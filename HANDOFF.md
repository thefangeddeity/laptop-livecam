# HANDOFF — read first, then re-measure. Do not trust this over live state.

Updated 2026-11-09. Session ran out of budget; start a FRESH session per node.

## Verified (named measurement)
- Spitsbergen streams: after deploying main 59426bd, /dev/video10 G_FMT 1280x720,
  13 segments in the :8888 variant, rtsp=ok, 0 writer-loop errors in journal.
- Ariana: Tailscale was stopped (fixed Nov 7, `tailscale up --accept-routes`).
  Published frame YAVG=103 (not black). privacy-mask region is full-frame.
- Ariana "Never film people" = /api/presence-pause. API round-trips. The NOTIFIER
  never read it (NOTIFY_PRESENCE_FILE absent from config.env -> /dev/null).
  Fixed a9c9864: notifier derives flag paths from DETECT_ROI_FILE's dir.
  Verified ONLY as path resolution, NOT behaviour.

## NOT verified — do these with a behavioural test
- Ariana pictures/video "blocked whatever users select". notify_shots=false since
  Oct 20, notify_video=true. Paths match and are re-read per alert, so not the
  presence bug. Test: set each toggle, trigger a detection, confirm Telegram gets /
  doesn't get photo+clip. Check NOTIFY_APPRISE_URLS_FILE exists and is readable.
- Spitsbergen: CV (mode is show, cv=None), detection (OpenCV 5.0 "setPreferableTarget
  not supported by new graph engine"; model path models/candidates/yolov8n.onnx),
  Telegram, recorder/clips, scene model, audio, :8080/llc in a browser.
  device.env carried from old install: check Telegram/ROI/NOTIFY_* keys.
- Installers on Linux: does setup set notify flag paths / detect camera into a
  preserved device.env?
- tina: unreachable over ssh Nov 9 (timeout). main 59426bd NOT deployed there.

## Repo changes
- macos a9c9864: cv_notify flag-path derivation.
- main 59426bd: vendored pyfakewebcam first (numpy 2), _writer_loop logs first
  exception + rate-limited repeats, ffmpeg-cam.service reads VIDEO_DEVICE/SIZE.
  Port cv_notify derivation to main? Linux defaults already /var/lib/hls-livecam.

## Node changes to review with Ron
- Spitsbergen: /etc/sudoers.d/99-ron NOPASSWD (ask keep?), ariana key in
  ~/.ssh/authorized_keys (ask keep?), sed tostring->tobytes in distro
  pyfakewebcam (now unnecessary; reverts on update), leftovers in
  /root/llc-preinstall-20261107. No pacman hook exists.
- Spitsbergen + tina(not yet): /usr/local/bin/broadcast-api and ffmpeg-cam unit
  hand-installed from main; a package rebuild should match them.
- NEVER enable Tailscale SSH. Don't change network settings.

## Still open from the brief
publisher stderr visible / backoff; setup+camdash check G_FMT on /dev/video10;
full sweep of bare `except: continue`, removed numpy/OpenCV APIs; release 7.2.1.

## 2026-11-09 late — Spitsbergen cloned from hosts/tanzania, then WEDGED
- device.env had 12 keys vs tanzania's 34 (no CV_*, NOTIFY_ENABLED, notify.urls,
  night, echo duck, mixer). Installed hosts/tanzania/{device.env,notches.json,
  audio.json,feed_mode} + ariana's notify.urls (same bot). Backup:
  /etc/hls-livecam/device.env.pre-clone-<ts>.
- Verified after clone: "notify: enabled, 1 destination, classes=[cat]",
  recording=True, 35 notches/9 enabled, audio 60/14000/0dB. Scene model missing
  (lived on tanzania's drive; CV_SCENE logs FileNotFoundError every pass).
- CORRECTED 11-10: NOT load (load 0.58). At 21:38 Nov 9 USB port 2-4 reset 3x,
  I/O errors on sda (Spitsbergen's USB Seagate root), ext4 journal aborted:
  root read-only in practice (state 'clean with errors', 19 errors) though
  findmnt says rw. Both disks SMART-clean; tanzania drive sdb fsck clean.
  Fix: move Seagate off port 2-4 / swap cable, reboot (fsck runs). Optane
  nvme RAID = Hera's Windows, leave alone.
- (old, wrong) Then POST feed-mode=cv -> within ~1 min ssh sessions stall (TCP 22 open, ping
  17ms, `uptime` never returns). Suspect load/memory under CV + cloned options
  (CV_FOVEAL, NIGHT_STACK, scene retries). Needs console look or power cycle.
  If it recurs: set feed_mode back to show, then enable options one at a time.
- Installer finding: setup writes a 12-key device.env and no notify.urls; a
  fresh or migrated node gets no CV config, no notifier. Fix in repo: setup
  should write the full template (hosts/tanzania is the reference).

- TODO after root writable: standardize detection messages to the documented format.
