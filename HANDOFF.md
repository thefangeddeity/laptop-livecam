# HANDOFF — read first, then re-measure. Do not trust this over live state.

Updated 2026-11-10 (after a compaction). Start a FRESH session per node.

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

- (done 11-10: code already matches the template; see "alert messages" below.)

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

## 2026-11-10 — after Ron's reboot (NOT yet resolved; was only in chat)
- 192.168.18.5 came up as **tanzania**: root = sdb3 (Toshiba, tanzania's drive),
  sda (Spitsbergen's USB Seagate) unmounted, so its 19 ext4 errors are NOT fsck'd.
  machine-id e74cf9dbf6ab4adf9f0cc89472967943.
- Measured there: laptop-livecam 7.2.0-1 (AUR, none of the 11-10 fixes),
  broadcast-api + mediamtx active, HLS playlist ok, 0 kernel I/O errors this boot,
  presence-pause=true, privacy-mask=true, feed-mode=show. Load ~7 at 12 min:
  python3 (broadcast-api) 75% CPU + three ffmpeg 42-61% -- not yet explained.
- Which machine's hardware this is was NOT measured (no DMI read). Chat claimed
  "tanzania's hardware"; that was an inference. Check /sys/class/dmi/id/product_name.
- Host key differs (different OS install). Probe with
  `-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=ERROR`;
  ~/.ssh/known_hosts deliberately left untouched.
- WAITING ON RON: keep tanzania booted, or put the Seagate first / unplug the
  Toshiba so Spitsbergen boots and fsck runs. Then: copy
  hosts/tanzania/var/lib/hls-livecam/* only if Ron wants tanzania's switches there
  (default is OFF by decision), and verify the recorder writes new segments.

## Release 7.2.1 (owed; nothing deployed to nodes yet)
main 7a5dee2 (serve guard json->_json), 1c9be10 + macos be394cd (alert logs),
ad9efba + macos b7dbbb0 (clip segment selection), 653f9aa (packaging/arch,
device.env template). Steps: tag v7.2.1 + mac-v7.2.1 together (annotated, -a);
regenerate sha256sums + .SRCINFO in packaging/arch; push AUR; rebuild deb
(tina unreachable 11-09); DMG on ariana; deploy to nodes and measure.

## Tooling (scratchpad, lost on reboot of this Mac)
- pyflakes: $S/venv/bin/pyflakes (python -m via xargs failed).
- python with cv2: ~/Projects/mac-hls-livecam/.venv/bin/python.
- main clone: $S/llc-main (S = /private/tmp/claude-501/-Users-ron-Projects/<session>/scratchpad).
- ssh probe that can't hang: `( ssh -n -o ConnectTimeout=5 -o BatchMode=yes ... & P=$!; sleep N; kill $P )`.

## Open questions for Ron (not yet asked again)
boot choice above; keep /etc/sudoers.d/99-ron NOPASSWD and ariana's key on
Spitsbergen?; delete stale local branches (main-art, main-mesh-card,
main-serve-guard, windows-art)?

## 2026-11-10 midday — tanzania study + installers (main 6568396, 4869178; pushed)
- Reference copies (read these before trusting memory of the design):
  osiris:repos/backups/llc-live/tanzania-llc-live-20261110-114057.tgz (live LLC
  files, units, nginx, sudoers, udev, manifests: pacman -Qe, versions) and
  ariana-llc-live-20261110.tgz (state/ config, LaunchAgents, versions). Both
  sha256-verified. Excluded: rec/, gallery/, images, wav, notify.urls (token).
- The machine is "HP Laptop 15-dw1xxx" with an HP TrueVision camera; it booted
  tanzania's Toshiba because Ron left it plugged in.
- Tanzania findings: package-owned code == 7.2.0 + index.html hand edit (50bb713,
  already in main). Hand-placed: livecam-tools (== macos tools/), capability
  units, mediamtx.yml (= setup's + `cam: record: no`), udev write-through rule
  (node-specific serial), snd-aloop (unused: AUDIO_SINGLE_SESSION=0).
  device.env: 3 stray `lili` lines; managed comments duplicated x4 (setup
  merge was not idempotent); CV_SCENE_ENABLED=1 with model retired.
- Installer fixes (7.2.1, both distros): shared `llc-configure` (device-env
  merge idempotent, audio detection, notify.urls stub, `verify`); template =
  tanzania values (CONF 0.50, recorder/clip keys, SCENE 0); home.html copied
  (fresh installs served 404 at /); capability probe packaged at
  /usr/share/hls-livecam-server/livecam-tools (NOT /usr/local/lib: pacman
  refused to overwrite tanzania's hand copies); setup retires shadowing
  /etc/systemd/system capability units; Debian pyfakewebcam check used no
  vendor path -> always pip-installed; alsa-utils dep; stale share/ camdash,
  camstack and dangling livecam-sync.timer removed; packaging/deb/build-deb.sh.
- MEASURED on tanzania (Arch): fresh install (state moved aside to
  /root/llc-fresh-test-20261110-115606, restored after) -> setup rc 0, 8 ok +
  WARN no destination; second run byte-identical (sha256 of every file setup
  writes + unit links). Upgrade over tanzania's real config -> 9/9 ok,
  identical on rerun, presence-pause=true, feed=show, 1 destination kept.
  CV on fresh install: detector loads packaged model, no tracebacks.
- Tanzania is now on a locally built 7.2.1-1 (pacman -Qkk 0 altered).
  /usr/local/etc/mediamtx.yml.tanzania = its pre-test copy.
- Found, not fixed: CV enhancement pipeline flaps (drops at ~100ms render, back
  on at 1.4ms, every few seconds) -- needs hysteresis. Load ~7 in show mode.
- Deb MEASURED (main fb97caf) in a rootful Ubuntu 24.04 systemd container on
  tanzania, real kernel + camera (host video/audio GIDs mapped in-container):
  apt install ok, setup rc 0, run2 byte-identical; frames, HLS, viewer, API ok.
  Also fixed from that run: gawk-only awk in the port check (mawk syntax error),
  pyfakewebcam pip fallback. BLOCKER: Ubuntu 24.04 / bookworm OpenCV 4.6 cannot
  run YOLOv8 (shape assertion; an opset-12 re-export from official weights is
  numerically equal on OpenCV 5.0 but fails identically on 4.6). Setup now
  FAILs with that reason. Decision for Ron: how Deb gets OpenCV >= 4.7.
- Test leftovers on tanzania: ~/llc-build (logs, snaps, scripts, built pkgs);
  /root/llc-fresh-test-20261110-115606 (tanzania originals, already restored)
  and -115745 (fresh-test config); /etc/hls-livecam.fresh-test,
  /var/lib/hls-livecam.fresh-test.
- Still to do: tag v7.2.1 + mac-v7.2.1; release_arch.sh (sha256/.SRCINFO, AUR
  push); gh release assets; macOS installer not re-tested this session.

## 2026-11-10 afternoon — CV boxes regression (main 0a3f642, deployed to tanzania)
- Cause: 5200d20 (Nov 3) split CV into a display instance (detection OFF) and
  a detecting instance; draw_hud drew the display tracker, always empty. Boxes
  gone since Nov 3, alerts unaffected. Fix: display draws detector's tracks
  (stale >5s skipped), re-pointed on CV reset; cv-state banner from display.
  MEASURED on tanzania: banner "DETECTING 1 TARGET", published frame shows a
  labelled box (HUMAN 0.92). Frame deleted after viewing.
- Alert study: today's 13 "Tanzania: Cat detected, no clip due to person
  present" = a REAL cat by the chair + a phantom "person" (clothes hung over a
  chair at the ROI's left edge, 0.34-0.64 in 116/120 ROI-crop frames).
  on_promotion stamps _human_seen before the motion gate, so a static phantom
  holds presence all day. Ron: "It's fine" -- no presence-rule change asked.
- Deb private OpenCV (Ron chose it): wheels opencv-python-headless 4.10.0.84,
  4.11.0.86, 4.12.0.88 all run yolov8n on Ubuntu 24.04 with system numpy 1.26
  (--no-deps --target, ~136-145 MB). NOT YET WIRED into setup/broadcast-api.

## 2026-11-10 evening — RELEASED 7.2.1 (Arch + macOS); Deb pending as 7.2.2
- Tags: v7.2.1 -> 0a3f642 (main), mac-v7.2.1 -> 11f5f10 (macos), annotated, pushed.
- GitHub release v7.2.1: laptop-livecam-7.2.1-1-any.pkg.tar.zst (sha256 6201290c...,
  built by release_arch.sh from the GH tag tarball; all its checks OK on tanzania)
  and HLS-Livecam-mac-v7.2.1-20261110T234916Z-11f5f10.dmg (f04406f2...).
- AUR: 69222bf "laptop-livecam 7.2.1" pushed from tanzania ~/Projects/aur-laptop-livecam
  (also osiris origin). AUR cgit .SRCINFO = 7.2.1; RPC lagged at 7.2.0 for a while.
- main 3a4ccf0 (after the tag): Deb private OpenCV (opencv-python-headless 4.10.0.84
  --no-deps into /usr/share/hls-livecam-server/opencv, only when distro cv2 < 4.7;
  python3-pip Depends; prerm removes). UNTESTED as a whole -> bump to 7.2.2, test in
  an Ubuntu 24.04 systemd container (see scratchpad build/debrun.sh: rootful, host
  video/audio GIDs mapped), then release deb + Arch 7.2.2.
- Next: Spitsbergen (Seagate) reboot -> fsck health -> upgrade test + fresh test of
  the Arch 7.2.1 installer (package staged on ariana: scratchpad spb/).

## 2026-11-10 19:00 — Spitsbergen back on its Seagate; Arch 7.2.1 installer MEASURED there
- Boot fsck ran 19:00:37: sda3 "clean", rw, write test ok, no EXT4/I/O errors this boot.
- Backup before testing: /root/spitsbergen-llc-pre-7.2.1-20261110-190335.tgz (on Spitsbergen).
- Upgrade 7.2.0 -> 7.2.1 (release package 6201290c): no conflicts, Qkk 0 altered,
  setup rc 0 twice, byte-identical, 9 ok + WARN (no destination).
- Nov 9 disk fault left ZERO-BYTE files written at 21:32: notify.urls, notches.json,
  audio.json, feed_mode, device.env.pre-clone-*. Restored: notify.urls from ariana's
  (same bot, 0640 root:http, not printed), notches.json + audio.json from
  hosts/tanzania. feed_mode left empty (= Hide) for Ron to choose. device.env is
  setup's (template + detected PCH audio); the Nov 7 backup held no URL.
- Fresh install (state moved to /root/llc-fresh-test-20261110-190805, restored after):
  setup rc 0, 9 ok + WARN, second run identical, / 200. After restore: 10/10 ok,
  identical on rerun.
- main d172524 (after 3a4ccf0): install hook uses hostnamectl (no hostname(1) there).

## 2026-11-11 ~01:20 — RELEASED 7.2.2 (deb + Arch + DMG); AUR still on 7.2.1
- Tags: v7.2.2 -> 9f445f5 (main), mac-v7.2.2 -> ee03e74 (macos). Release assets:
  laptop-livecam_7.2.2_amd64.deb (f3fd6566, built on tina from 9f445f5),
  laptop-livecam-7.2.2-1-any.pkg.tar.zst (08b7972d, release_arch.sh on Spitsbergen
  from the GH tag tarball, all OK), HLS-Livecam-mac-v7.2.2-...-ee03e74.dmg (0f733915).
- MEASURED: Ubuntu 24.04 container (rootful podman on Spitsbergen, host GIDs mapped):
  private OpenCV 4.10 installed, the running service maps opencv/cv2/cv2.abi3.so,
  setup rc 0 twice, identical. tina (Ubuntu 26.04, distro OpenCV 4.10): upgrade
  7.2.0->7.2.2, 9 ok + WARN (tina has no alert destination), identical, its own
  nginx TLS file kept (conffile). Spitsbergen on 7.2.2: setup 10/10.
- Bugs found and fixed on the way: deb overwrote tina's nginx file (now conffile /
  Arch backup=); include ele-messenger* matched old+new snippet -> duplicate /elem/;
  verify followed a redirect to an unresolvable tailnet name; journal check counted
  the pre-restart process; pyfakewebcam imports cv2 before the private path was set.
- AUR NOT updated to 7.2.2: the AUR key lives only on tanzania (~/.ssh/aur). When
  tanzania is up: copy main packaging/arch/{PKGBUILD,laptop-livecam.install,
  release_arch.sh} into ~/Projects/aur-laptop-livecam, makepkg --printsrcinfo >
  .SRCINFO, commit "laptop-livecam 7.2.2", push aur + origin.
- Node notes: tina's Tailscale is LOGGED OUT (Ron must sign in); tina and the
  fresh Spitsbergen have no alert destination / Spitsbergen has ariana's.
  Spitsbergen: podman + pacman-contrib installed after `pacman -Sy` (partial
  upgrade) -- a full `pacman -Syu` is advisable. Spitsbergen feed_mode is empty
  (= Hide) since the Nov 9 fault; left for Ron.

## 2026-11-11 — AUR at 7.2.2, pushed from ariana
- Ron registered ariana's id_ed25519.pub with the AUR account; ariana pushes now
  (no ~/.ssh/config entry needed). AUR host keys added to ariana known_hosts after
  matching the fingerprints published on aur.archlinux.org.
- AUR checkout on ariana: ~/Projects/aur-laptop-livecam-ariana (remotes: origin =
  AUR, osiris = osiris:repos/aur-laptop-livecam.git). 07eb87a "laptop-livecam 7.2.2"
  pushed to both; tag tarball and install sums re-verified before the push.
  .SRCINFO came from the Spitsbergen release build (no makepkg on macOS).
- tanzania's ~/Projects/aur-laptop-livecam is now BEHIND (at 7.2.1): `git pull` there.

## 2026-11-11 afternoon — ELE Mesh on Spitsbergen; Spitsbergen fully upgraded
- `pacman -Syu` (127 pkgs, OpenSSL 3.6 -> 4.1, linux-lts 6.18.62) fixed the partial
  upgrade Claude caused with `-Sy`. v4l2loopback built for 6.18.62-lts; GRUB boots lts.
- ele-messenger 1.5.7 from AUR (replaced retired ele-messenger-client 1.3.5);
  linger on, `elemesh` user service active; /elem/ 200; ping joined:false --
  **Ron must enter the mesh passphrase** in the app on Spitsbergen.
- After reboot: livecam verify 10/10 (frames, HLS, detector on OpenCV 5.0, 1 alert
  destination), 0 EXT4/I/O/reset lines this boot. Spitsbergen tailnet 100.100.17.2.
