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

import glob
import math
import json
import subprocess
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
                 min_fg=0.0, classes_file='/dev/null',
                 video_flag_file='/dev/null',
                 shots_flag_file='/dev/null',
                 rec_dir=None, clip_pre=None, clip_post=None, clip_max=None,
                 roi_file=None,
                 presence_file=None, presence_hold_sec=None,
                 name=None):
        self.enabled = bool(enabled) and bool(urls) and (
            _apprise is not None or all(_telegram_targets(u) for u in urls))
        self.urls = [u.strip() for u in (urls or []) if u.strip()]
        self.classes = {c.strip().lower() for c in classes if c.strip()}
        # Which classes raise an alert is a SETTING, not a deploy. The panel
        # writes this file and the notifier re-reads it per event, so turning
        # 'dog' on does not need a restart -- same live-toggle shape as the
        # video switch. Absent file means "use what config.env said".
        self.classes_file = classes_file
        # Don't record while somebody is home. Presence is tracked whether or
        # not 'human' is an alerting class: not wanting to be TOLD about
        # yourself is the ordinary setup, and is a different question from not
        # wanting to be RECORDED.
        self.presence_file = presence_file or '/dev/null'
        self.presence_hold_sec = (60.0 if presence_hold_sec is None
                                  else float(presence_hold_sec))
        self._human_seen = None
        # Was a hardcoded Linux path, so on macOS it never existed and the
        # switch silently read as "on" no matter what the panel said.
        self.video_flag_file = video_flag_file
        self.shots_flag_file = shots_flag_file
        # The detection region, re-read per event like the switches: changing
        # it must not need a restart, and an alert should be cropped the way
        # the region was when the alert happened.
        self.roi_file = roi_file or '/dev/null'
        # Instance attribute shadows the class default, so a node whose
        # recording lives somewhere else says so once, at construction.
        if rec_dir:
            self.REC_DIR = rec_dir
        # How much of the room either side of the detection goes in the clip.
        # Both come from config; the numbers here are only what a node that
        # says nothing gets. The post-roll is the one that matters and it is
        # why the clip used to stop too soon -- see _send.
        self.clip_pre = 5.0 if clip_pre is None else float(clip_pre)
        self.clip_post = 20.0 if clip_post is None else float(clip_post)
        # The ceiling on a clip that keeps extending. A cat that settles in
        # and sleeps in frame must not produce an unbounded file on a disk
        # that also holds six hours of rolling recording.
        self.clip_max = 120.0 if clip_max is None else float(clip_max)
        # track_id -> wall time it was last seen. The clip's END follows this,
        # not the moment of first detection.
        self._track_seen = {}
        self.cooldown_sec = float(cooldown_sec)
        # Motion gate. A detection that has never once overlapped moving
        # foreground is furniture: tanzania spent an hour reporting a crumpled
        # bag as a cat every five minutes at fg=0.00 on every single frame,
        # while a real arrival necessarily disturbs the background model.
        # Compared against the track's PEAK fg, so a cat that settles after
        # walking in still counts. 0 disables it, and Detection defaults fg to
        # 1.0, so a node running without MOG2 is never silenced by this.
        self.min_fg = float(min_fg)
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
        # Escalating backoff per class.
        #
        # The flat cooldown is a FLOOR, not a cap: one object that the tracker
        # keeps dropping and re-acquiring becomes a new track_id every ~20s,
        # every new id is a fresh candidate, and per-track dedupe cannot see
        # that they are the same thing. The result is a notification exactly
        # every cooldown_sec, forever -- observed on tanzania as ten alerts in
        # 47 minutes for a single static detection scraping the confidence
        # floor. A thing that has already been reported and has not gone away
        # is not news, so each repeat for the same class waits longer: 1x, 3x,
        # 6x, 12x the cooldown, capped. One quiet gap at the top of the ladder
        # means the subject actually left, and the next arrival is news again,
        # so the ladder resets.
        self._backoff_step = {}     # class -> rung
        self._backoff_mult = (1, 3, 6, 12)
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
        now = time.monotonic()
        # BEFORE the class filter, deliberately -- see presence_file above.
        if cls == 'human':
            self._human_seen = now
        if cls not in self._classes_wanted():
            return False
        # Stamped on EVERY cycle this track is still promoted, not only the
        # first -- the early returns below (cooldown, already-notified) are
        # exactly the path a subject that stays takes, so stamping after them
        # would record one sighting and never update.
        self._track_seen[track.track_id] = time.time()
        with self._lock:
            win = self._collecting.get(track.track_id)
            if win is not None:
                self._offer(win, track, frame, now)
                self._close_expired(now)
                return False
            self._close_expired(now)
            # One notification per track, ever: a track that decays and
            # re-promotes is the same animal on the same visit.
            if self.min_fg > 0:
                fg = float(getattr(track, 'fg_consistency', 1.0))
                if fg < self.min_fg:
                    # Seen and deliberately not reported: it has not moved.
                    # Marked notified so it is not reconsidered every frame.
                    self._notified_tracks.add(track.track_id)
                    return False
            if track.track_id in self._notified_tracks:
                return False
            last = self._last_sent.get(cls)
            step = self._backoff_step.get(cls, 0)
            wait = self.cooldown_sec * self._backoff_mult[
                min(step, len(self._backoff_mult) - 1)]
            # Quiet for a full top-rung interval => the subject left. Reset, so
            # the next genuine arrival is treated as the news it is.
            if last is not None and (now - last) > self.cooldown_sec * self._backoff_mult[-1]:
                step = 0
                self._backoff_step[cls] = 0
                wait = self.cooldown_sec
            if last is not None and (now - last) < wait:
                # Per class: a cat that settles in and keeps re-promoting
                # does not send forty messages.
                self._notified_tracks.add(track.track_id)
                return False
            self._last_sent[cls] = now
            self._backoff_step[cls] = min(step + 1, len(self._backoff_mult) - 1)
            if step:
                self._log("notify: %s repeat #%d -- next no sooner than %.0fs"
                          % (cls, step, self.cooldown_sec * self._backoff_mult[
                              min(step + 1, len(self._backoff_mult) - 1)]))
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
        # conf * sqrt(sharp), not conf * sharp.
        #
        # Sharpness is a VARIANCE (of the Laplacian), so its spread dwarfs a
        # probability's: measured here, confidence runs 0.35-0.91 while
        # sharpness runs 19-825. Multiplied raw, the score is sharpness with a
        # rounding error attached -- conf 0.35/sharp 800 (280) beat conf
        # 0.91/sharp 200 (182), so the marginal detection won for being crisp.
        # That was survivable across three shots; as the ONE picture sent it
        # is not, because low confidence usually means the subject is
        # half-occluded or leaving frame, which is the worst single picture to
        # pick. The square root puts sharpness on a standard-deviation scale,
        # comparable to a probability, so both terms actually count.
        score = conf * math.sqrt(max(0.0, sharp))
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
            # Score picks the sharpest, most confident frames -- which is
            # exactly why it drops the one that says what happened. A subject
            # is blurriest at the moment it is first seen, because that is when
            # it is moving, so the arrival frame loses on score almost every
            # time: sends were starting at t+1.0s with the entry already over.
            # Take the earliest candidate first, unconditionally, then fill the
            # rest by score. Best-of-six still, with the first shot in it.
            # The arrival frame is reserved only when there is room for more
            # than one shot. At shots=1 "best of six" has to mean the best
            # one, or the setting is lying: the arrival frame is reliably the
            # blurriest in the window (it is the moment the subject was
            # moving), so forcing it here would hand over the worst picture
            # available and call it the best.
            earliest = (min(win['slots'].values(), key=lambda c: c['t'])
                        if self.shots > 1 else None)
            if earliest is not None:
                picks.append(earliest)
            for c in cands:
                if earliest is not None and c is earliest:
                    continue
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

    def snapshot(self, frame):
        """On demand (the panel's SNAPSHOT key): this frame, now, with no
        cooldown -- a person asked for it."""
        if not self.enabled:
            return False
        try:
            self._q.put_nowait({'cls': 'snapshot', 'track_id': 'snapshot',
                                'when': time.time(), 'text': f"{self.name}: Snapshot",
                                'picks': [{'frame': frame, 't': 0.0, 'conf': 0.0, 'sharp': 0.0}]})
            return True
        except queue.Full:
            return False

    def _classes_wanted(self):
        """Classes that currently raise an alert, re-read per event.

        The file is the panel's checkboxes; config.env is the fallback for a
        node whose operator has never touched them.
        """
        try:
            with open(self.classes_file) as f:
                picked = {c.strip().lower()
                          for c in f.read().replace('\n', ',').split(',')
                          if c.strip()}
            # An empty file is a CHOICE (every box unticked), not an absence,
            # so it must silence the notifier rather than fall through to the
            # configured default. Only an unreadable/missing file falls back.
            return picked
        except Exception:
            pass
        return self.classes

    def _presence_pause_on(self):
        """Absent means off. The opposite default from the shots/video
        switches, which are on unless turned off: this one withholds
        evidence, and a setting nobody chose should not stop the camera
        recording."""
        try:
            with open(self.presence_file) as f:
                return f.read().strip() == 'true'
        except Exception:
            return False

    def _presence_blocks(self):
        """True when somebody is home and the operator asked not to record it.

        The hold is what makes it usable rather than flickering: a person who
        steps out of frame for a moment has not left the room.
        """
        if self._human_seen is None or not self._presence_pause_on():
            return False
        return (time.monotonic() - self._human_seen) <= self.presence_hold_sec

    def forget_track(self, track_id):
        self._track_seen.pop(track_id, None)
        with self._lock:
            self._notified_tracks.discard(track_id)

    # -- Short clip from the rolling recording -------------------------
    #
    # A still taken at promotion shows a cat already sitting there. It cannot
    # show the cat walking in, because that already happened by the time the
    # detector was sure. mediamtx is told to keep a short rolling recording of
    # the camera path (see mediamtx.yml, path 'cam'), so the clip is CUT from
    # video that already exists -- `-c copy`, no re-encode, no second encoder
    # competing with the live publisher -- and it can start BEFORE the
    # detection. That pre-roll is the whole reason to prefer a clip.
    #
    # Live-toggled through a state file, like feed mode and blur: the panel
    # writes it, this reads it per event. Absent file means on.

    # The rolling recording's `cam` path -- a DEFAULT, overridden per node,
    # the same way snapshot_dir and video_flag_file are. It used to be this
    # constant and nothing else, which is where the Linux nodes keep it and
    # which does not exist on macOS: _cut_clip globbed an empty directory and
    # returned None on every alert, forever. The cutter was correct the whole
    # time; it was reading a path no platform-aware code had ever written to,
    # and the function's own "None is never an error worth failing over"
    # turned a missing feature into a silence nobody could see.
    REC_DIR         = '/var/lib/hls-livecam/rec/cam'

    def _roi(self):
        """The operator's detection region as (x, y, w, h) fractions, or None.

        Absent file, empty file or unparseable content all mean "whole
        frame". A region is an optional narrowing, so every failure mode here
        has to widen rather than narrow -- a corrupt file that silently
        cropped every alert to a corner would be worse than one that is
        ignored.
        """
        try:
            with open(self.roi_file) as f:
                raw = f.read().strip()
            if not raw:
                return None
            d = json.loads(raw)
            # Switched off means the whole frame, the same as never set. The
            # box stays in the file so it can be switched back on without
            # being drawn again; it just stops applying.
            if not bool(d.get('on', True)):
                return None
            box = (float(d['x']), float(d['y']), float(d['w']), float(d['h']))
            if box[2] <= 0 or box[3] <= 0:
                return None
            return box
        except Exception:
            return None

    def _crop_to_roi(self, frame):
        """Crop a full frame to the region. Returns the frame unchanged when
        there is no region, so callers need no branch."""
        box = self._roi()
        if box is None:
            return frame
        h, w = frame.shape[:2]
        fx, fy, fw, fh = box
        x = max(0, min(w - 1, int(round(fx * w))))
        y = max(0, min(h - 1, int(round(fy * h))))
        bw = max(1, min(w - x, int(round(fw * w))))
        bh = max(1, min(h - y, int(round(fh * h))))
        return frame[y:y + bh, x:x + bw]

    def _shots_wanted(self):
        """Whether an alert carries its stills. Same switch shape as video:
        read per event, absent file means on.

        Both can be off at once and that is a legitimate setting, not a
        misconfiguration -- the alert still arrives, it just says what was
        seen instead of showing it. Somebody on a metered connection, or who
        only wants to know the cat came in, is served by exactly that.
        """
        try:
            with open(self.shots_flag_file) as f:
                return f.read().strip() != 'false'
        except Exception:
            return True

    def _video_wanted(self):
        try:
            with open(self.video_flag_file) as f:
                return f.read().strip() != 'false'
        except Exception:
            return True

    def _seg_start(self, path):
        """Wall-clock start of a mediamtx segment, from its own filename."""
        base = os.path.basename(path).rsplit('.', 1)[0]
        try:
            d, t = base.split('_')
            hh, mm, rest = t.split('-', 2)
            ss, us = (rest.split('-') + ['0'])[:2]
            import datetime
            return datetime.datetime.strptime(
                f"{d} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S").timestamp() + int(us) / 1e6
        except Exception:
            return None

    def _cut_clip(self, when, pre=None, post=None):
        """Cut [when-pre, when+post] out of the rolling recording.

        Returns a path, or None -- and None is never an error worth failing a
        notification over: the stills still go. Everything here is best-effort
        precisely because the alert matters more than the clip.
        """
        pre = self.clip_pre if pre is None else float(pre)
        post = self.clip_post if post is None else float(post)
        try:
            segs = []
            for p in glob.glob(os.path.join(self.REC_DIR, '*.mp4')):
                st = self._seg_start(p)
                if st is not None:
                    segs.append((st, p))
            if not segs:
                return None
            segs.sort()
            start, end = when - pre, when + post

            # A segment covers [its start, the next segment's start). The last
            # one is still being written, so treat it as open-ended.
            chosen = []
            for i, (st, p) in enumerate(segs):
                nxt = segs[i + 1][0] if i + 1 < len(segs) else float('inf')
                if nxt > start and st < end:
                    chosen.append((st, p))
            if not chosen:
                return None

            out = os.path.join(self.snapshot_dir,
                               'livecam-clip-%d.mp4' % int(when))
            lst = out + '.txt'
            with open(lst, 'w') as f:
                for _, p in chosen:
                    f.write("file '%s'\n" % p.replace("'", "'\\''"))
            # -ss AFTER -i on a concat input: accurate, and still stream-copy.
            # A region means the clip has to be CROPPED, and cropping means
            # re-encoding: `-c copy` hands the stream through untouched,
            # which is why a clip normally costs no CPU at all. That property
            # is worth keeping when there is no region, so the two cases are
            # genuinely different commands rather than one with a filter that
            # is sometimes a no-op.
            roi = self._roi()
            if roi is None:
                tail = ['-c', 'copy', '-movflags', '+faststart']
            else:
                fx, fy, fw, fh = roi
                # ffmpeg's crop takes expressions, so the fractions are
                # resolved against iw/ih at encode time -- no need to know the
                # recording's resolution here, and it stays correct if the
                # capture size changes under us. Rounded to even numbers
                # because yuv420p cannot represent odd dimensions.
                crop = ('crop=floor(iw*%.6f/2)*2:floor(ih*%.6f/2)*2:'
                        'floor(iw*%.6f/2)*2:floor(ih*%.6f/2)*2'
                        % (fw, fh, fx, fy))
                tail = ['-vf', crop,
                        '-c:v', 'libx264', '-preset', 'veryfast',
                        '-pix_fmt', 'yuv420p', '-an',
                        '-movflags', '+faststart']
            cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                   '-f', 'concat', '-safe', '0', '-i', lst,
                   '-ss', '%.2f' % max(0.0, start - chosen[0][0]),
                   '-t', '%.2f' % (end - start)] + tail + [out]
            r = subprocess.run(cmd, capture_output=True, timeout=45)
            try:
                os.unlink(lst)
            except Exception:
                pass
            if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) < 1024:
                self._log('notify: clip cut failed (stills still sent)')
                try:
                    os.unlink(out)
                except Exception:
                    pass
                return None
            return out
        except Exception as exc:
            self._log('notify: clip error %s (stills still sent)'
                      % type(exc).__name__)
            return None

    def _schedule_clip(self, item, text):
        """Cut and send the clip once post-roll seconds of room exist.

        A timer rather than a sleep in the worker: the worker drains a queue,
        and blocking it for the length of a post-roll would hold up every
        other alert behind it. One timer per alert, and the cooldown bounds
        how many can ever be in flight.
        """
        when = item['when']
        tid = item.get('track_id')

        def _visit_over():
            # Gone = not seen for a whole post-roll. The cap is the other way
            # out, so a subject that never leaves still produces a clip.
            last = self._track_seen.get(tid, when)
            return (time.time() >= last + self.clip_post
                    or time.time() >= when + self.clip_max)

        def _cut_and_send():
            last = self._track_seen.get(tid, when)
            # End at the last sighting plus the tail, capped. Never shorter
            # than the old fixed window, so this can only lengthen a clip.
            post = min(max(self.clip_post, (last - when) + self.clip_post),
                       self.clip_max)
            clip = self._cut_clip(when, post=post)
            if not clip:
                return
            try:
                other = []
                for u in self.urls:
                    tg = _telegram_targets(u)
                    if not tg:
                        other.append(u)
                        continue
                    for chat in tg[1]:
                        self._send_telegram_video(tg[0], chat, text, clip)
                # Non-Telegram destinations used to get the clip as an
                # attachment on the stills notification. That has already gone
                # by the time this runs, so they get their own -- dropping them
                # silently would be a capability removed by accident while
                # fixing something else.
                if other and _apprise is not None:
                    ap = _apprise.Apprise()
                    for u in other:
                        ap.add(u)
                    ap.notify(title=text, body=text, attach=[clip])
            finally:
                # This path owns the file: the stills cleanup ran long ago.
                try:
                    os.unlink(clip)
                except Exception:
                    pass

        def _tick():
            if not _visit_over():
                nt = threading.Timer(1.0, _tick)
                nt.daemon = True
                nt.start()
                return
            _cut_and_send()

        # One second, not the full post-roll: the wait has to be re-evaluated
        # while the subject is still in frame. Still a timer rather than a
        # sleep in the worker, which drains a queue and must not be held.
        t = threading.Timer(min(1.0, self.clip_post), _tick)
        t.daemon = True
        t.start()

    def _send_telegram_video(self, token, chat, text, path, _retry=True):
        """sendVideo, separate from the photo album: Telegram will mix the two
        in one media group, but then a failed clip takes the stills down with
        it. They go independently so the evidence always arrives."""
        chat = self._chat_moves.get(chat, chat)
        try:
            with open(path, 'rb') as f:
                blob = f.read()
        except Exception:
            return False
        body, ctype = _multipart(
            {'chat_id': chat, 'caption': text, 'supports_streaming': 'true'},
            {'video': ('clip.mp4', blob)})
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendVideo', data=body,
            headers={'Content-Type': ctype})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return bool(json.loads(r.read().decode()).get('ok'))
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
            except Exception:
                err = {}
            moved = (err.get('parameters') or {}).get('migrate_to_chat_id')
            if moved and _retry:
                self._chat_moves[chat] = str(moved)
                return self._send_telegram_video(token, str(moved), text, path,
                                                 _retry=False)
            self._log('notify: telegram video failed: HTTP %d %s'
                      % (exc.code, err.get('description', '')))
            return False
        except Exception as exc:
            self._log('notify: telegram video failed: %s' % type(exc).__name__)
            return False

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

    @staticmethod
    def _stamp_frame(bgr, captured_at):
        """Burn the CAPTURE time into the picture.

        Deliberately the moment the frame was taken, not the moment it was
        sent -- those differ exactly when something has gone wrong, and a
        send-time stamp would paper over the one failure worth seeing.

        A real OFFSET DROP SHADOW, not a symmetric stroke. The first attempt
        ringed the glyphs with a fat dark outline and filled them with a
        hairline, so the stroke swallowed the letterforms and read as muddy
        grey mush at a distance. A shadow sits down-right of a solid white
        fill: the fill stays the brightest thing in the frame and keeps its
        shape, while the shadow only has to lift it off whatever is behind.

        Everything scales off frame width so a 640px clip and a 1280px still
        look like the same stamp.
        """
        try:
            txt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(captured_at))
            h, w = bgr.shape[:2]
            scale = max(0.5, min(1.15, w / 1280.0 * 0.78))
            # Fill weight carries the legibility, so it is the heavier of the
            # two -- the opposite of the first version.
            fill = max(2, int(round(scale * 2.6)))
            off = max(2, int(round(scale * 2.4)))
            font = cv2.FONT_HERSHEY_DUPLEX      # rounder, reads better small

            (tw, th), base = cv2.getTextSize(txt, font, scale, fill)
            x = int(14 * scale) + 2
            y = h - int(14 * scale) - base
            if x + tw > w - 4:                  # never run off a narrow frame
                x = max(2, w - 4 - tw)

            # Shadow first, offset down-right, a touch heavier so it reads as
            # depth rather than as a second copy of the text.
            cv2.putText(bgr, txt, (x + off, y + off), font, scale,
                        (0, 0, 0), fill + 1, cv2.LINE_AA)
            # Then the fill, solid and bright, at full weight.
            cv2.putText(bgr, txt, (x, y), font, scale,
                        (255, 255, 255), fill, cv2.LINE_AA)
        except Exception:
            pass          # a missing stamp must never cost the alert
        return bgr

    def _send(self, item):
        text = item.get('text') or f"{self.name}: {_label(item['cls'])} detected"
        paths, jpegs = [], []
        # Encoding the stills is the expensive half of an alert, so the switch
        # is read BEFORE the work rather than before the send. Off means the
        # frames are never JPEG-encoded at all, not encoded and discarded.
        #
        # A snapshot the operator asked for explicitly is not an alert's
        # stills and ignores this -- turning off automatic photos must not
        # silently break the button that takes one.
        # A snapshot the operator asked for is exempt: they are at the panel
        # asking for this picture and already know who is home.
        manual = item.get('cls') == 'snapshot'
        withhold = (not manual) and self._presence_blocks()
        if withhold:
            # Say so. An alert that silently arrives without its picture reads
            # as a broken camera.
            text += " -- no photo or clip, someone is home"
        want_shots = manual or (self._shots_wanted() and not withhold)
        try:
            for i, p in enumerate(item['picks'] if want_shots else []):
                # The snapshot is the original feed, not the sharpie or CV
                # render: evidence for a person to look at.
                # Cropped to the detection region, so the picture shows the
                # area that was actually being watched. A still of the whole
                # room, when only a corner of it is armed, invites the reader
                # to look for the cat in three quarters of a frame where no
                # detector was ever running.
                bgr = cv2.cvtColor(self._crop_to_roi(p['frame']),
                                   cv2.COLOR_RGB2BGR)
                # item['when'] is the window's wall clock; p['t'] is this
                # shot's offset inside it, so together they are when THIS
                # picture was taken.
                bgr = self._stamp_frame(
                    bgr, float(item.get('when') or time.time())
                         + float(p.get('t') or 0.0))
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

            # Cut once, reuse for every destination. Snapshots are never
            # held back waiting on it: if the cut fails, clip is None and the
            # stills go exactly as before.
            # THE CLIP IS CUT LATER, ON PURPOSE.
            #
            # Stills are collected over window_sec and sent when that window
            # closes, so at this instant only about window_sec of room has
            # happened since the detection. Cutting here could therefore only
            # ever reach a few seconds past it -- which is exactly why the clip
            # stopped while the animal was still walking. The old 4s post-roll
            # was not a judgement about what is interesting; it was the most
            # that existed yet.
            #
            # So the stills go now and the clip is cut once its tail has actually
            # been recorded. The two were already sent separately, for the
            # unrelated reason that a failed clip must not take the stills with
            # it; this only moves one of them later.
            if not manual and self._video_wanted() and not withhold:
                self._schedule_clip(item, text)

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
                    spacing_sec=_num('NOTIFY_SPACING_SEC', 1.5),
                    min_fg=_num('NOTIFY_MIN_FG', 0.05),
                    classes_file=_get('NOTIFY_CLASSES_FILE', '') or '/dev/null',
                    presence_file=_get('NOTIFY_PRESENCE_FILE', '') or '/dev/null',
                    presence_hold_sec=_num('NOTIFY_PRESENCE_HOLD_SEC', 60.0),
                    video_flag_file=_get('NOTIFY_VIDEO_FILE', '')
                        or '/var/lib/hls-livecam/notify_video',
                    shots_flag_file=_get('NOTIFY_SHOTS_FILE', '')
                        or '/var/lib/hls-livecam/notify_shots',
                    rec_dir=_get('NOTIFY_REC_DIR', '') or None,
                    clip_pre=_num('NOTIFY_CLIP_PRE', 5.0),
                    clip_post=_num('NOTIFY_CLIP_POST', 20.0),
                    clip_max=_num('NOTIFY_CLIP_MAX', 120.0),
                    roi_file=_get('DETECT_ROI_FILE', '') or None)
