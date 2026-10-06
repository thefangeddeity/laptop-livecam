#!/usr/bin/env python3
"""
cv_notify.py -- notifications on track promotion, off the frame path.

Fires when the run-14 evidence accumulator promotes a track, never per
frame. A promotion is a real event: evidence has accumulated across
multiple detections past a threshold. A raw single-frame hit at 0.05 is
not, and notifying on one would mean an email every time a shadow moved.

Nothing here runs on the writer thread. The pipeline calls on_promotion(),
which snapshots the frame and enqueues; a worker thread does the encode and
the send. That ordering is deliberate and is the run-11 lesson: an SMTP
server that takes thirty seconds to answer must cost the feed nothing. The
queue is bounded and drops rather than blocks, because a backlog of stale
notifications is worth less than a live stream.

Apprise rather than smtplib: the backend is a URL. mailto:// today, and a
push service or webhook later is a config change with no code change. That
is the whole reason for the dependency, so nothing in here may assume the
destination is email.
"""

import json
import os
import queue
import socket
import threading
import time
import urllib.error
import urllib.request
import uuid

try:
    import apprise as _apprise
except Exception:      # optional dependency; absence disables notification
    _apprise = None

import cv2

# What the message says, per detector class.
_LABELS = {'human': 'Person', 'person': 'Person'}


def _label(cls):
    return _LABELS.get(cls, cls.capitalize())


def _sharpness(frame, box):
    """Variance of the Laplacian over the detection's box: the standard
    focus/blur measure. A cat mid-leap smears into a low number; a cat
    holding still for a frame scores high."""
    x, y, w, h = (int(v) for v in box)
    fh, fw = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(fw, x + w), min(fh, y + h)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return 0.0
    gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _telegram_targets(url):
    """tgram://<token>/<chat>[/<chat>...][?...] -> (token, [chats]), else None."""
    if not url.lower().startswith('tgram://'):
        return None
    path = url[len('tgram://'):].split('?', 1)[0].strip('/')
    parts = [p for p in path.split('/') if p]
    if len(parts) < 2:
        return None
    token = parts[0][3:] if parts[0].startswith('bot') else parts[0]
    return token, parts[1:]


def _multipart(fields, files):
    """multipart/form-data body for Telegram's upload endpoints."""
    boundary = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                   f'name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (name, data) in files.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                   f'name="{k}"; filename="{name}"\r\n'
                   f'Content-Type: image/jpeg\r\n\r\n'.encode() + data + b'\r\n')
    out.append(f'--{boundary}--\r\n'.encode())
    return b''.join(out), f'multipart/form-data; boundary={boundary}'


class Notifier:
    """Queue-and-forget notifier keyed on track promotion.

    A promotion opens a short WINDOW for that track. on_promotion() is called
    for every promoted track on every detection cycle, so each call during
    the window offers the current frame as a candidate snapshot; the best
    one per sub-slot is kept. When the window closes, the best SHOTS frames
    at least SPACING apart are sent together with one line of text.

    Why several and why apart (the defaults are starting points to measure
    against, not findings): if one snapshot is usable with probability p,
    N independent ones give 1-(1-p)^N -- at p=0.5, three give 88% -- but
    only if they ARE independent, and frames a few hundred ms apart are the
    same pose and the same blur. Choosing by score rather than by clock
    raises p itself. Each sent frame's score is logged so the numbers can
    be tuned from real sightings.

    Construct once and keep. Nothing here blocks the frame path for longer
    than a frame copy; encoding and sending run on the worker thread.
    """

    def __init__(self, urls=None, classes=('human',), cooldown_sec=300,
                 enabled=False, snapshot_dir=None, queue_size=8,
                 log=None, shots=3, window_sec=6.0, spacing_sec=1.5,
                 name=None):
        self.enabled = bool(enabled) and bool(urls) and (
            _apprise is not None or all(_telegram_targets(u) for u in urls))
        self.urls = [u.strip() for u in (urls or []) if u.strip()]
        self.classes = {c.strip().lower() for c in classes if c.strip()}
        self.cooldown_sec = float(cooldown_sec)
        self.shots = max(1, int(shots))
        self.window_sec = max(0.0, float(window_sec))
        self.spacing_sec = max(0.0, float(spacing_sec))
        # Candidate slots a third of the spacing wide: the best frame per
        # slot is all that is kept, so memory is bounded by window/slot
        # frames, and the greedy pick below still has choices near every
        # spacing boundary.
        self._slot_sec = max(0.1, self.spacing_sec / 3.0)
        self.snapshot_dir = snapshot_dir or '/tmp'
        # Which node saw it, first in the message: with several livecams on
        # one chat, "Cat detected" alone does not say where.
        self.name = (name or socket.gethostname().split('.')[0].capitalize()).strip()
        self._log = log or (lambda msg: None)

        self._q = queue.Queue(maxsize=int(queue_size))
        self._lock = threading.Lock()
        self._last_sent = {}        # class -> monotonic timestamp
        self._notified_tracks = set()
        self._collecting = {}       # track_id -> open window
        self._chat_moves = {}       # telegram chat id -> the id it moved to
        self._thread = None
        self._stopping = threading.Event()

        if self.enabled:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
            self._log(f"notify: enabled, {len(self.urls)} destination(s), "
                      f"classes={sorted(self.classes)}, "
                      f"{self.shots} shot(s) from {self.window_sec:g}s, "
                      f">= {self.spacing_sec:g}s apart, "
                      f"cooldown={self.cooldown_sec:.0f}s")
        elif enabled and urls and not self.enabled:
            self._log("notify: apprise not installed; notifications disabled")

    # ── called from the detection thread; must stay cheap ───────────────
    def on_promotion(self, track, frame):
        """A promoted track, this detection cycle. Returns True if this call
        opened a new notification window."""
        if not self.enabled:
            return False
        cls = (track.cls or '').lower()
        if cls not in self.classes:
            return False
        now = time.monotonic()
        with self._lock:
            win = self._collecting.get(track.track_id)
            if win is not None:
                self._offer(win, track, frame, now)
                self._close_expired(now)
                return False
            self._close_expired(now)
            # One notification per track, ever: a track that decays and
            # re-promotes is the same animal on the same visit.
            if track.track_id in self._notified_tracks:
                return False
            last = self._last_sent.get(cls)
            if last is not None and (now - last) < self.cooldown_sec:
                # Per class: a cat that settles in and keeps re-promoting
                # does not send forty messages.
                self._notified_tracks.add(track.track_id)
                return False
            self._last_sent[cls] = now
            self._notified_tracks.add(track.track_id)
            win = {'cls': cls, 'track_id': track.track_id, 'start': now,
                   'wall': time.time(), 'slots': {}}
            self._collecting[track.track_id] = win
            self._offer(win, track, frame, now)
            if self.window_sec == 0:
                self._close_expired(now + 1.0)
            return True

    def _offer(self, win, track, frame, now):
        t = now - win['start']
        if t > self.window_sec:
            return
        conf = float(track.confidence)
        sharp = _sharpness(frame, track.box)
        score = conf * sharp
        slot = int(t / self._slot_sec)
        best = win['slots'].get(slot)
        if best is None or score > best['score']:
            win['slots'][slot] = {'score': score, 't': t, 'conf': conf,
                                  'sharp': sharp, 'frame': frame.copy()}

    def _close_expired(self, now):
        """Caller holds the lock. Closes every window past its end."""
        for tid in [tid for tid, w in self._collecting.items()
                    if now - w['start'] > self.window_sec]:
            win = self._collecting.pop(tid)
            cands = sorted(win['slots'].values(), key=lambda c: -c['score'])
            picks = []
            for c in cands:
                if all(abs(c['t'] - p['t']) >= self.spacing_sec for p in picks):
                    picks.append(c)
                    if len(picks) == self.shots:
                        break
            picks.sort(key=lambda c: c['t'])
            if not picks:
                continue
            try:
                self._q.put_nowait({'cls': win['cls'], 'track_id': tid,
                                    'when': win['wall'], 'picks': picks})
            except queue.Full:
                self._log("notify: queue full, dropped a notification")

    def forget_track(self, track_id):
        with self._lock:
            self._notified_tracks.discard(track_id)

    def close(self):
        self._stopping.set()

    # ── worker thread ───────────────────────────────────────────────────
    def _worker(self):
        while not self._stopping.is_set():
            try:
                item = self._q.get(timeout=1.0)
            except queue.Empty:
                # A window whose track stopped being promoted gets no more
                # calls; close it from here.
                with self._lock:
                    self._close_expired(time.monotonic())
                continue
            try:
                self._send(item)
            except Exception as exc:
                # Never propagate: a failed send is a log line, not an
                # outage. The stream does not depend on this succeeding.
                self._log(f"notify: send failed: {exc}")
            finally:
                self._q.task_done()

    def _send(self, item):
        text = f"{self.name}: {_label(item['cls'])} detected"
        paths, jpegs = [], []
        try:
            for i, p in enumerate(item['picks']):
                # The snapshot is the original feed, not the sharpie or CV
                # render: evidence for a person to look at.
                bgr = cv2.cvtColor(p['frame'], cv2.COLOR_RGB2BGR)
                ok, buf = cv2.imencode('.jpg', bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if not ok:
                    continue
                jpegs.append(buf.tobytes())
                path = os.path.join(
                    self.snapshot_dir,
                    f"livecam-{item['cls']}-{int(item['when'])}-{item['track_id']}-{i}.jpg")
                with open(path, 'wb') as f:
                    f.write(jpegs[-1])
                paths.append(path)

            results = []
            other = []
            for u in self.urls:
                tg = _telegram_targets(u)
                if tg:
                    for chat in tg[1]:
                        results.append(self._send_telegram(tg[0], chat, text, jpegs))
                else:
                    other.append(u)
            if other and _apprise is not None:
                ap = _apprise.Apprise()
                for u in other:
                    ap.add(u)
                stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(item['when']))
                results.append(ap.notify(title=text, body=f"{text} at {stamp}",
                                         attach=paths or None))
            scores = ', '.join(f"t+{p['t']:.1f}s conf {p['conf']:.2f} sharp {p['sharp']:.0f}"
                               for p in item['picks'])
            self._log(f"notify: {item['cls']} track {item['track_id']}, "
                      f"{len(jpegs)} shot(s) [{scores}] "
                      f"{'sent' if results and all(results) else 'FAILED'}")
        finally:
            # Snapshots are transient by design -- recording is a separate
            # concern with its own retention budget.
            for path in paths:
                try:
                    os.unlink(path)
                except Exception:
                    pass

    def _send_telegram(self, token, chat, text, jpegs, _retry=True):
        """One message: the text as the caption of a photo, or of the first
        photo of an album (sendMediaGroup) when there are several."""
        chat = self._chat_moves.get(chat, chat)
        if not jpegs:
            body = json.dumps({'chat_id': chat, 'text': text}).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendMessage', data=body,
                headers={'Content-Type': 'application/json'})
        elif len(jpegs) == 1:
            body, ctype = _multipart({'chat_id': chat, 'caption': text},
                                     {'photo': ('snapshot.jpg', jpegs[0])})
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendPhoto', data=body,
                headers={'Content-Type': ctype})
        else:
            media = [dict({'type': 'photo', 'media': f'attach://p{i}'},
                          **({'caption': text} if i == 0 else {}))
                     for i in range(len(jpegs))]
            body, ctype = _multipart(
                {'chat_id': chat, 'media': json.dumps(media)},
                {f'p{i}': (f'p{i}.jpg', j) for i, j in enumerate(jpegs)})
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendMediaGroup', data=body,
                headers={'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return bool(json.loads(r.read().decode()).get('ok'))
        except urllib.error.HTTPError as exc:
            # The URL holds the token: report Telegram's own reason (error
            # code and description, which never echo it), never the request.
            try:
                err = json.loads(exc.read().decode())
            except Exception:
                err = {}
            why = err.get('description', '')
            # A group that becomes a supergroup gets a new id, and Telegram
            # says which: follow it now, and say what to put in the URL file.
            moved = (err.get('parameters') or {}).get('migrate_to_chat_id')
            if moved and _retry:
                self._chat_moves[chat] = str(moved)
                self._log(f"notify: telegram chat {chat} moved to {moved} "
                          f"(supergroup) -- sending there; update notify.urls")
                return self._send_telegram(token, str(moved), text, jpegs, _retry=False)
            self._log(f"notify: telegram send failed: HTTP {exc.code} {why}".rstrip())
            return False
        except Exception as exc:
            self._log(f"notify: telegram send failed: {type(exc).__name__}")
            return False


def make_notifier(denv, log=None):
    """Build from device.env, or a disabled Notifier if not configured."""
    denv = denv or {}

    def _get(key, default):
        v = denv.get(key)
        return default if v is None or str(v).strip() == '' else str(v).strip()

    enabled = _get('NOTIFY_ENABLED', '0') not in ('0', 'false', 'no', 'off')
    urls = [u for u in _get('NOTIFY_APPRISE_URLS', '').split(',') if u.strip()]
    # The URLs carry the service's token (tgram://<token>/<chat>), so they may
    # live in their own file instead -- root:http 640, one URL per line, '#'
    # comments -- keeping the secret out of device.env, which is copied into
    # the repo's host captures.
    url_file = _get('NOTIFY_APPRISE_URLS_FILE', '')
    if url_file:
        try:
            with open(url_file) as f:
                urls += [ln.strip() for ln in f
                         if ln.strip() and not ln.lstrip().startswith('#')]
        except OSError as exc:
            if log:
                log(f"notify: cannot read {url_file}: {exc}")
    classes = [c for c in _get('NOTIFY_CLASSES', 'human').split(',') if c.strip()]
    try:
        cooldown = float(_get('NOTIFY_COOLDOWN_SEC', '300'))
    except ValueError:
        cooldown = 300.0

    def _num(key, default):
        try:
            return float(_get(key, str(default)))
        except ValueError:
            return float(default)

    return Notifier(urls=urls, classes=classes, cooldown_sec=cooldown,
                    enabled=enabled, log=log, name=_get('NOTIFY_NAME', '') or None,
                    shots=int(_num('NOTIFY_SHOTS', 3)),
                    window_sec=_num('NOTIFY_WINDOW_SEC', 6.0),
                    spacing_sec=_num('NOTIFY_SPACING_SEC', 1.5))
