#!/usr/bin/env python3
"""buzz_tone.py -- BUZZ, out loud, on the server's own speakers.

BUZZ already shook every viewer's browser. This is the other half: a tone on
the machine the camera is attached to, for reaching somebody in that room.

Through the sound card, never the PC speaker. pcspkr exists on these nodes
(tanzania has the module loaded and a /dev/input device) but it is a one-bit
beeper on a motherboard pin -- there is no volume control on it and nothing
to shape. The requirement was "whatever is louder", and this was measured
rather than assumed; see below.

WHAT WAS MEASURED, AND HOW
Tones were played on tanzania's own speaker and recorded through its own
microphone -- not a model of a laptop speaker, the actual one. The mic is
held by the RTSP pipeline, so the recording was taken from the stream that
pipeline already publishes, which is the same microphone. Every candidate
was rendered at one peak amplitude, and played at 25% so the stream's
limiter (alimiter limit=0.95) never engaged and the comparison stayed
linear; the recordings peaked at 0.19-0.25, well clear. Scores are
A-weighted, i.e. weighted for what an ear actually hears.

A swept sine, 400-4500 Hz, gave the response of speaker + room + mic:

    ~950 Hz, ~1400 Hz and ~2600 Hz are peaks; 1550 Hz is a deep null;
    everything above ~3200 Hz is more than 20 dB down.

Three things follow, and all three shaped the tone:

1. SINE, NOT SQUARE. A square at 1400 Hz spends much of its energy on
   harmonics at 4200 and 7000 Hz, which this speaker cannot reproduce. In
   the first round the square-wave candidates lost to plain sines, which is
   the opposite of what equal-peak RMS predicts, and this is why.

2. NOTHING ABOVE 3 kHz, even though the ear is most sensitive at 3-4 kHz.
   A 3800 Hz sine measured 22.9 dB below a 2000 Hz one. Ear sensitivity is
   worth nothing if the speaker cannot move that fast.

3. TWO TONES, NOT ONE. The response is spiky because of room nulls, so a
   single pure tone can be loud at the laptop and quiet three steps away.
   Alternating 1400/2100 Hz measured only 1.1 dB below the best single tone
   -- at or under the ~1 dB a listener can notice -- and cannot be cancelled
   at both frequencies by one null. The alternation also defeats the ear's
   habit of filtering out a steady tone, which is why alarms warble.

    A-weighted, relative, on tanzania:
        sine 1400 ............  0.0 dB
        sine 2000 ............ -0.2
        ALT 1400/2100 ........ -1.1   <- chosen
        alt 950/1400/2100 .... -2.7
        AM square 2300 ....... -2.7
        sweep 1500-3500 ...... -3.4
        pager square ......... -4.7
        sine 2950 ............ -7.3
        sine 3800 ........... -22.9

VOLUME. None of the above is the biggest lever. tanzania's master sat at
-23.25 dB, and raising it for the duration of the tone is worth more than
every tone choice combined. So the player does that and puts it back. The
restore runs in a finally, because the failure that matters is leaving
somebody's speakers at maximum.
"""

import math
import os
import struct
import subprocess
import sys
import threading
import time
import wave

SR          = 48000
TONE_A      = 1400.0     # measured peak of the speaker/room response
TONE_B      = 2100.0     # far enough that one null cannot take both
SEG         = 0.110      # per-tone, seconds -- urgent without being a trill
BURST       = 0.66       # one group of alternations
GAP         = 0.16       # silence between groups
GROUPS      = 3
PEAK        = 0.9
FADE        = 0.005      # anti-click, seconds

MIN_INTERVAL = 3.0       # seconds between audible buzzes
_last_played = 0.0
_lock        = threading.Lock()


def _render():
    """The tone, as signed 16-bit stereo frames."""
    frames = bytearray()
    seg_n  = int(SR * SEG)
    fade_n = max(1, int(SR * FADE))
    per_group = max(1, int(round(BURST / SEG)))
    for g in range(GROUPS):
        for i in range(per_group):
            f = TONE_A if i % 2 == 0 else TONE_B
            for n in range(seg_n):
                v = math.sin(2.0 * math.pi * f * n / SR)
                if n < fade_n:                 v *= n / fade_n
                elif n > seg_n - fade_n:       v *= (seg_n - n) / fade_n
                s = int(max(-1.0, min(1.0, v * PEAK)) * 32767)
                frames += struct.pack('<hh', s, s)
        if g != GROUPS - 1:
            frames += b'\x00\x00\x00\x00' * int(SR * GAP)
    return bytes(frames)


def ensure_wav(path):
    """Render once and cache. Returns the path, or None if it cannot."""
    try:
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            return path
        tmp = path + '.tmp'
        with wave.open(tmp, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(_render())
        os.replace(tmp, path)          # atomic: no reader sees a partial file
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass
        return path
    except Exception as e:
        print('buzz_tone: could not render %s: %s' % (path, e),
              file=sys.stderr, flush=True)
        return None


def duration():
    return GROUPS * BURST + (GROUPS - 1) * GAP


# ── Picking an output ────────────────────────────────────────────
# Not by card NUMBER: the real analogue card is 1 on tanzania and 0 on tina,
# because tanzania also has snd-aloop loaded and the virtual Loopback takes
# index 0. Both call the real one PCH, so it is addressed by NAME. plughw
# rather than hw so ALSA converts rate/format instead of refusing.
#
# The service user reaches ALSA directly and deliberately: PulseAudio here
# belongs to the desktop user's session (/run/user/1000/pulse/native) and
# http/www-data cannot see that socket. Both are in the `audio` group, which
# is what makes the direct path work; it was verified before this shipped.

def _linux_devices(explicit):
    if explicit:
        return [explicit]
    found = []
    try:
        out = subprocess.run(['aplay', '-l'], capture_output=True, text=True,
                             timeout=5).stdout
        for line in out.splitlines():
            if not line.startswith('card '):
                continue
            try:
                head, rest = line.split(':', 1)
                name = rest.split('[', 1)[0].strip()
                dev  = int(line.split('device ', 1)[1].split(':', 1)[0])
            except Exception:
                continue
            if 'loopback' in name.lower():
                continue          # virtual; nothing is listening to it
            if 'hdmi' in rest.lower():
                continue          # a monitor, not the machine in the room
            found.append('plughw:CARD=%s,DEV=%d' % (name, dev))
    except Exception:
        pass
    found.append('default')
    return found


_MIX_CONTROLS = ('Master', 'PCM', 'Speaker', 'Headphone')


def _amixer_card(device):
    if device and 'CARD=' in device:
        return device.split('CARD=', 1)[1].split(',', 1)[0]
    return None


def _vol_get(card):
    """(control, raw_value) for the first control that answers, else None."""
    for ctl in _MIX_CONTROLS:
        try:
            cmd = ['amixer']
            if card:
                cmd += ['-c', card]
            cmd += ['sget', ctl]
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=5)
            if out.returncode != 0:
                continue
            for line in out.stdout.splitlines():
                if 'Playback' in line and '[' in line and '%' in line:
                    raw = line.split('Playback', 1)[1].strip().split()[0]
                    if raw.isdigit():
                        return ctl, raw
        except Exception:
            continue
    return None


def _vol_set(card, ctl, value):
    try:
        cmd = ['amixer', '-q']
        if card:
            cmd += ['-c', card]
        cmd += ['sset', ctl, value]
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _play_linux(wav, device, boost):
    """Play once. Returns True if some player actually ran."""
    card = _amixer_card(device)
    saved = _vol_get(card) if boost else None
    try:
        if saved:
            _vol_set(card, saved[0], '100%')
        limit = duration() + 5
        for cmd in (['aplay', '-q', '-D', device, wav],
                    ['aplay', '-q', wav]):
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=limit)
                if r.returncode == 0:
                    return True
            except FileNotFoundError:
                break                      # no aplay at all; stop trying it
            except subprocess.TimeoutExpired:
                return True                # it ran; it just outlived us
            except Exception:
                continue
        return False
    finally:
        # The one failure that must not happen is leaving the speakers at
        # maximum, so this runs even if playback raised.
        if saved:
            _vol_set(card, saved[0], saved[1])


def _play_macos(wav, device, boost):
    saved = None
    try:
        if boost:
            try:
                out = subprocess.run(
                    ['osascript', '-e', 'output volume of (get volume settings)'],
                    capture_output=True, text=True, timeout=5)
                v = out.stdout.strip()
                if v.isdigit():
                    saved = v
                    subprocess.run(['osascript', '-e', 'set volume output volume 100'],
                                   capture_output=True, timeout=5)
            except Exception:
                saved = None
        try:
            subprocess.run(['afplay', wav], capture_output=True,
                           timeout=duration() + 5)
            return True
        except subprocess.TimeoutExpired:
            return True
        except Exception:
            return False
    finally:
        if saved is not None:
            try:
                subprocess.run(['osascript', '-e',
                                'set volume output volume ' + saved],
                               capture_output=True, timeout=5)
            except Exception:
                pass


def play(wav_path, device=None, boost=True, force=False):
    """Sound the buzz. Returns True if it played.

    Rate limited: holding the button down, or several viewers buzzing at
    once, must not stack tones on top of each other -- that is noise, not a
    signal, and it is also how you end up with a dozen aplay processes
    fighting over one device.
    """
    global _last_played
    now = time.monotonic()
    with _lock:
        if not force and (now - _last_played) < MIN_INTERVAL:
            return False
        _last_played = now
    wav = ensure_wav(wav_path)
    if not wav:
        return False
    try:
        if sys.platform == 'darwin':
            return _play_macos(wav, device, boost)
        devs = _linux_devices(device)
        for d in devs:
            if _play_linux(wav, d, boost):
                return True
        print('buzz_tone: no ALSA device would play (tried %s)' % ', '.join(devs),
              file=sys.stderr, flush=True)
        return False
    except Exception as e:
        print('buzz_tone: play failed: %s' % e, file=sys.stderr, flush=True)
        return False


def play_async(wav_path, device=None, boost=True):
    """Fire and forget -- the HTTP request must not wait on a 2.3s tone."""
    t = threading.Thread(target=play, args=(wav_path, device, boost),
                         daemon=True)
    t.start()
    return t


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/buzz_tone_test.wav'
    dev  = sys.argv[2] if len(sys.argv) > 2 else None
    boost = '--no-boost' not in sys.argv
    print('rendering %s (%.2fs, %d/%d Hz)' % (path, duration(), TONE_A, TONE_B))
    ok = play(path, dev, boost=boost, force=True)
    print('played:', ok)
