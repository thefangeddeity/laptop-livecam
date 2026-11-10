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

## 2026-11-10 — installer stock-take (verified)
- Release assets v7.2.0: bytes match GitHub sha256 digests; archives list. Not
  corrupt files -- they install broken systems.
- main 6xx (see git log): PKGBUILD now in packaging/arch/ (was only AUR +
  tanzania; osiris aur-laptop-livecam.git == AUR 419512c). Installs whole
  vendor/, drops python-pyfakewebcam dep. New pkg/.../device.env.template;
  both setups merge missing defaults. Tested: 11->30 keys, rerun 0 added.
- Still to do: setup/camdash frame check on /dev/video10 + HLS segments;
  publish PKGBUILD to AUR from packaging/arch (needs a 7.2.1 tag + sha256);
  rebuild deb on tina (unreachable 11-09); notify.urls stub in setup.
- Spitsbergen root FS read-only since USB reset on port 2-4 (Nov 9); needs
  cable/port change + reboot before anything can be deployed there.

## 2026-11-10 — full-history stock-take (main 444, macos 316, windows 182 commits)
Method: read every subject; pyflakes over both lineages; symbol parity checks;
diffed v7.2.0 deb vs Arch payloads. Ranked:
1. FIXED main 7a5dee2: Linux HTTPS guard NameError (json vs _json) -> sudo
   `tailscale serve --bg 8080` every 5 min, serve map never saved, /elem never
   restored. Spitsbergen journal: 25 "restored" in 2h. Needs deploy (7.2.1).
2. windows: viewer compiled in has privacy mask / Never film people / ROI /
   gallery / alert switches; Rust server has NO routes for them. Controls inert.
   windows is parked at 7.0.45.
3. macos: evidence recorder writes even when low power is on or the CPU gate
   parked detection (main fixed this in 7e528a9; bin/broadcast-api:1502).
4. main lacks macOS 35fcc3f stale-frame guard (_SLOT_MAX_AGE_S): a stalled
   capture can keep scoring/alerting off a frozen frame on Linux.
5. Arch pkg installs TWO camdash: /usr/local/bin (current) and a stale share/
   copy (no room-audio panel); also legacy camstack x2. Nothing references the
   share copies. ffmpeg-cam.service also has two copies (setup uses share/).
6. deb ships no GUI (gui/ + camdash-gui live outside pkg/); Arch does.
7. Notifier lineages diverged 850 lines. Linux manual Snapshot schedules a clip,
   macOS doesn't (`not manual`). Documented alert text (CHANGELOG 7.0.47):
   "<Node>: Cat detected[, no photo due to person present.]" -- code on both
   matches; "all over the place" likely = nodes on different versions/repos
   (amira separate repo). Need a sample of the bad messages to go further.
8. Linux API hardcodes NOTIFY_*_FILE while notifier honours device.env: latent
   split if anyone sets them (nobody does today).
9. Silent handlers (except -> pass/continue): mac broadcast-api 24, Linux 32,
   cv_notify 7/6. The json bug above hid in one. Sweep still owed.
10. Stale local branches main-art/main-mesh-card/main-serve-guard/windows-art are
   pre-rewrite copies; content is on origin. Safe to delete (ask).
11. Release state: v7.2.0 has deb+Arch+DMG; mac-v7.2.0 tag has no GH release;
   main is 5 commits past v7.2.0, macos 8+ past mac-v7.2.0.
Recurring classes in history (why this keeps happening): half-ports between
lineages (7.0.13, 7.0.14, 1732dcf, a9c9864, 6acac62, this json bug); NameErrors
shipped (4c768f3, a540c37, 95b424f, 175b3de, 1f2fa6a); installers destroying
config (5254dd9, 4a412fd, 6043569, 7e48e43); blind regex edits (05b9c63,
a6f7115). Cheapest guard: pyflakes undefined-name check in the build/deploy.

## 2026-11-10 — alert messages (corrects my earlier "read-only root broke clips")
- Template (user): "<HOSTNAME>: Cat detected, no <MEDIATYPE> due to person present."
  Code matches it (Ariana 07:40 is correct).
- Spitsbergen never used it: its "Never film people" is OFF because the
  INSTALLER never writes /var/lib/hls-livecam switches, and absent presence_pause
  means off (cv_notify/_presence_pause_on). Absent privacy_mask means ON (7.0.26),
  so the mask is fine. Ron installed with our installer; nothing was cloned into
  /var/lib. tanzania's own values (sdb3, ro) are now in hosts/tanzania (4b16928).
- DECIDED 11-10 (Ron): "Never film people" stays OFF by default; setup does not ask.
  Users find it in Settings. Spitsbergen sending bare "Cat detected" is by design.
- AFTER the disk fix + reboot, copy hosts/tanzania/var/lib/hls-livecam/* to
  Spitsbergen (http-owned), restart broadcast-api, verify /api/presence-pause=true,
  then a person + cat in frame should give the template text.
- Clips: cut works by hand (rc 0, 465 KB to /tmp). Real bug: newest segment treated
  as open-ended -> every alert cut the 36-byte segment from 21:37 Nov 9 when the
  recorder stopped. Fixed main ad9efba / macos b7dbbb0. Scene model: tanzania
  retired its own on Sep 8, so "missing" is not a regression.
