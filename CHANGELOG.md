# Changelog

Newest first. Entries for 7.0.2 through 7.0.11 were reconstructed from the
release tags on 2026-10-20, having been skipped as they shipped; the older
5.x/2.x section below is not consistently ordered and has been left as it was.

## 7.0.12

- The Debian package stops installing software at install time. `postinst`
  used to `pip install pyfakewebcam` as root, with `--break-system-packages`
  and a trailing `|| true`, then rewrite the installed library source in
  place to swap numpy's removed `tostring()` for `tobytes()`. It needed the
  network to finish a package install, hid its own failure so a broken
  install still reported success, wrote into
  `/usr/local/lib/python3*/dist-packages` where no package manager would ever
  clean it up, and the patch had become a no-op because upstream already
  uses `tobytes()`. pyfakewebcam is now vendored in the payload under
  `/usr/share/hls-livecam-server/vendor`, byte-identical to the Arch
  `python-pyfakewebcam 0.1.0-1` copy that drives tanzania's camera.
  `broadcast-api` prefers a distro-packaged pyfakewebcam and falls back to
  the vendored one, so Arch behaviour is unchanged and only Debian moves.
  Arch was never affected: its PKGBUILD always declared the dependency.
- The import had to move. `import pyfakewebcam` sat one line *above* the
  `sys.path` insert it would need to find a vendored copy.
- README's install instructions were three versions and one package rename
  out of date: they named `hls-livecam-server_2.7.3_amd64.deb` for a package
  now called `laptop-livecam`, and the accompanying `apt install` line was
  missing four hard dependencies (`python3-flask`, `python3-pil`,
  `python3-numpy`, `python3-opencv`), so following them produced a package
  that could not start. Now documents both the Debian and Arch routes, and
  uses `apt install ./<file>.deb` rather than `dpkg -i`, which does not
  resolve `Depends` at all.
- `hosts/tina/MANIFEST.md` claimed tina ran the 6.0.7 .deb; it runs 7.0.11.
- 7.0.6 shipped as a commit but was never tagged, so the version named no
  findable tree. Tagged retroactively at the commit that declares it.

## 7.0.11

- A detection region: crop the camera so motion is only detected inside a
  chosen rectangle, with snapshots and clips cropped to match. Edit/Set
  buttons on the viewer panel, a separate toggle to apply or lift it, and a
  reset. Fractions are taken against the picture rectangle rather than the
  video element, which is letterboxed by `object-fit: contain`.
- Two silent failures surfaced while porting it to Linux: `/var/lib/hls-livecam`
  was root-owned so the service could not write the region file, which also
  revealed that `notify_shots` had not persisted since 7.0.10 because its
  writer swallowed exceptions; and the Linux `broadcast-api` imports
  `json as _json`, so a ported block using the bare name raised NameError
  and returned 400.

## 7.0.10

- Photos in alerts get the same switch video has, so snapshots can be turned
  off independently of clips.

## 7.0.9

- One version number, one tree: release from a tag, and refuse to build a
  version that is not tagged. Cut after two trees had both declared 7.0.8.

## 7.0.8

- The evidence recorder gets a switch, so clip recording can be turned off
  without turning off detection.

## 7.0.7

- Alert clips work on Linux, and record the room rather than the mode. A
  third ffmpeg leg fed from the pre-render frame writes segments straight to
  disk, so a clip is not blacked out by Hide mode and is not served over HLS
  the way a mediamtx path would be.

## 7.0.6

- Review findings from the 7.0.5 deploy. Shipped as a commit; see 7.0.12 for
  the tag it was missing.

## 7.0.5

- A deploy script for tina, failure-gated throughout, with final checks that
  do not trust what the install printed about itself. It captures tina's live
  state before installing and re-asserts unit enablement from that capture,
  because the old `prerm` destroys that information before any script of ours
  runs. It also restores `/etc/nginx/conf.d/hls-livecam.conf` afterwards:
  that file is payload with no `conffiles` declaration, so dpkg replaces it
  with no prompt and no `.dpkg-old`, and tina's copy is the only one carrying
  the TLS listener and redirect.

## 7.0.4

- Capability detection. A node measures whether it can render CV mode and
  hides the key when it cannot, while detection and alerting carry on
  regardless, running off the much cheaper `observe()`. Measured rather than
  inferred, because core count and CPU model go stale and lie on a throttled
  box. Three states, and `unknown` deliberately does not hide the key: a
  probe that failed to run is not evidence a machine is slow.
- The Debian package takes the `laptop-livecam` name, matching the Arch
  package and the repo.
- CV and Night had rendered nothing since 7.0.2, a consequence of splitting
  `observe()` out of `process()`.

## 7.0.3

- A motion gate, so furniture stops being reported as animals. This lineage
  carried no motion evidence at all, so every promoted track alerted. Tracks
  now carry `fg_consistency`, absorbed with decay — `max(det.fg, tr.fg*0.93)`
  rather than a lifetime high-water mark — and the notifier skips a track
  whose evidence has gone stale. The decay is the point: a monotonic peak
  lets one frame where a motionless object overlapped moving foreground vouch
  for it for the life of the track, which is how a black shoe under a sofa
  became a recurring cat.

## 7.0.2

- Give `CVProcessor` the three methods `broadcast-api` was calling. Detection
  had been dead since 7.0.1, logging `AttributeError: 'CVProcessor' object has
  no attribute 'set_motion_alerts'` once a second: a merge paired a
  `broadcast-api` from one lineage with a `cv_processor` from another and
  nothing checked that the calls still landed. Found by diffing what the
  caller calls against what the class defines, which showed three missing
  methods rather than the one being hit — including `observe()`, without
  which alerting is tied to whatever a viewer happened to select.

## 7.0.1

- Camera lamp reads the device, not the mode. The writer loop runs in every
  mode and only changes what it renders, so the camera goes on being read in
  Hide; reporting "off" was a privacy indicator under-reporting live capture.
- "All living beings" now means it: COCO's full animate set, person plus ten
  animals, behind one "Other" row, instead of four species.
- A "plant" class, off by default and deliberately outside "All living
  beings", so a houseplant can be named correctly and silenced rather than
  reported as a cat.
- COCO_LIVING derives from COCO_LABELS instead of restating it.
- main and cambrian-actor merged into one lineage.

## [5.5.1] - 2026-08-15
### Fixed
- **Feed-mode and message-lock persistence were silently no-ops.**
  `/var/lib/hls-livecam/` was `root:root 0755`; `broadcast-api` runs as
  `http` and could not write `feed_mode` or `msg_lock` into it. The write
  was wrapped in a bare `except: pass`, so every POST appeared to succeed
  while never reaching disk. On restart, `feed_mode` always fell back to
  `SAFE_FEED_MODE` regardless of what the operator last chose -- a
  deliberate `hide` did not survive a restart, silently replaced by `cv`.
  Found live, verified by setting `hide`, restarting, and observing the
  fallback. `feed_mode` and `msg_lock` are now included in the same
  `CAMDASH_STATE_FILES` chown/chmod loop `camdash-feed.state` and
  `cell_aspect` already used (root:www-data/http 0664), in both setup
  scripts. A live system already on 5.5.0 needs `hls-livecam-setup`
  re-run (or the two files manually chowned) to pick this up -- the
  package payload alone does not fix already-broken permissions on an
  existing install.

## [5.5.0] - 2026-08-15
### Added
- **CV Mode pivot, Phase 1.** Show/Blur/Hide + a separate B&W control is
  replaced by Show/CV Mode/Hide across the web viewer, camdash, and the
  Linux operator GUI. `/api/feed-mode` accepts `cloak` as a permanent input
  alias for the canonical `cv`; `/api/bw-mode` stays routable but is now a
  no-op. New `cv_processor.py`: a stateful temporal processor (bounded
  3-frame history, optical-flow-gated motion mask, temporal denoise, CLAHE
  tone correction, damped unsharp sharpening), wired into `broadcast-api`
  in place of the old PNG/PIL cloak render. Profiled at ~31ms/frame
  steady-state against a ~40ms budget on real captured frames. Detection
  and recording are not part of this phase.

## [5.4.0] - 2026-08-14
### Fixed
- **Feed mode persists across restarts, and defaults to `cloak`.** A restart
  previously reset the feed to `show`, exposing the clear camera after the
  operator had deliberately chosen cloak. `show` is now never reached by
  fallback -- only by explicit choice.
- **GOP regression.** Run-1's 1s keyframe interval was lost when a package
  install overwrote a live-only fix. Now sourced from `device.env` as
  `GOP_SECONDS` (default 1) and committed in `pkg/`.
- **broadcast-api now stops cleanly.** Its supervisor loops respawned the
  children that SIGTERM had just killed, so the replacement ffmpeg outlived
  the process, systemd waited out its full stop timeout, and an orphaned
  ffmpeg kept the camera device open. 90s-and-failed is now 47ms and clean.
- **Stalled streams are detected.** `hls_worker` only checked the master
  playlist for HTTP 200 -- a static file that answers 200 while the pipeline
  behind it is stopped. It now watches `EXT-X-MEDIA-SEQUENCE` and reports
  STALE, with the threshold derived from the stream's own TARGETDURATION so
  slow hardware is not misreported as broken.
- **Hide no longer derives from the camera image.** It row-shuffled and
  rolled the live frame; it now publishes black, matching the Windows node.
- Header no longer reads DEGRADED for a deliberately stopped server, or for
  a healthy one whose HLS state has not been polled yet.

### Changed
- Feed switches are covered by VHS static instead of a 16s countdown, and
  the cover is now shown to **every** viewer -- previously only the browser
  that clicked saw it.
- Hide shows viewers "No signal / The camera is switched off" rather than an
  unexplained black frame.

## [5.3.0] - 2026-08-13
### Added
- camdash-gui: PySide6 operator dashboard for Linux, ported from the macOS build.
  Installed alongside camdash — the curses monitor is unchanged and still the
  headless/SSH surface; the GUI is the desktop one.
- camdash: additive GUI-support layer (API_BASE/RTSP_PORT/HLS_PORT/API_PORT,
  `camera_present_cached()`, `_cpu_temp()` via x86_pkg_temp, and a `_livecam()`
  dispatcher over the existing run_* service functions). The curses UI does not
  reference any of it.
- setup (Arch): registers camdash-gui.desktop and prepares the per-user config
  directory the GUI persists window geometry into, chowned to the invoking user
  (root-owned would be silently unwritable from the user's session).

### Notes
- GUI is Arch-only. PySide6 has no Debian bookworm packages (the split pyside6
  packages start at trixie) and the Debian node is headless, so `gui/` lives at
  the repo root rather than under `pkg/`, and the .deb payload is unchanged.

## [3.0.3] - 2026-05-06
### Fixed
- camdash: VIDEO STACK shows N/A for MSSG API, DARK, FPS, REPAIR when server is off ([o] toggle)
- camdash: CAM shows FOUND (not LIVE) when server is off but camera is present
- camdash: CAM shows LIVE only when server is on and camera is present
- setup (Arch): mediamtx restarted after config write to avoid "path not configured" on fresh installs
- setup (Arch): sudoers entries use `disable --now` / `enable --now` to match camdash [o] toggle


## [2.8.7] - 2026-05-01
### Fixed
- camstack: `getdata()` → `tobytes()` (Pillow deprecation, Python 3.14)
- Arch setup: move nginx default server from port 80 to 8080 so conf.d config wins
- Arch setup: add `include conf.d/*.conf;` to nginx.conf if missing
- Arch setup: create `/var/log/nginx/` if missing

## [2.8.6] - 2026-04-26
### Fixed
- Arch setup: `User=www-data` → `User=http` in broadcast-api.service
- Arch setup: sudoers entry updated from www-data to http
- deb: version bumped, ffmpeg-cam.service synced to pkg

## [2.8.5] - 2026-04-25
### Fixed
- Arch setup: pkg copy of hls-livecam-setup-arch had stale `hostname -I` — now matches installed fix from v2.8.4

## [2.8.4] - 2026-04-25
### Fixed
- Arch setup: IP address empty in completion message — replaced `hostname -I` with `ip route get` fallback

## [2.8.3] - 2026-04-25
### Fixed
- Arch setup: `hostname` command not found — replaced with `hostnamectl hostname` with `/etc/hostname` fallback

## [2.8.2] - 2026-04-25
### Added
- Feed mode controls: Show / Cloak / Hide replacing single Hide Feed toggle
- Cloak mode: client-side halfblock pixelation canvas overlay (color, live)
- Cloak bridges to Hide: grayscale pixelation shown immediately on Hide to prevent flash of raw video while snapshot generates
- confirm() dialog on Clear message button

### Changed
- Forced dark theme (no longer follows system preference)
- Sidebar sections styled as cards
- Button state logic: Save and Cancel blue only when changes pending; Clear blue when message exists; all always visible
- block_art COLS reduced to 80 to match Cloak pixelation density
- dark.png cache-busted on Hide with timestamp query string

### Notes
- Cloak is client-side only — a determined user can bypass via dev tools.
  Future goal: server-side pixelated HLS stream via ffmpeg-cam-dark.service.

## [2.8.1] - 2026-04-24
### Added
- camstack SYSTEM panel: CPU temperature display (coretemp sensor, falls back to "?" if unavailable)
- snap_interval config: `/var/lib/hls-livecam/snap_interval` sets widget refresh (1/2/5s), falls back to 2s default

### Changed
- SMART box: colon spacing normalized, TEMP renamed to DISK TEMP
- SYSTEM panel bottom row: equidistant thirds layout for RAM / USB / CPU TEMP

## [2.8.0] - 2026-04-24
### Added
- camstack MESSAGE box: live pixelated webcam widget using halfblock ▀ rendering with oceanic/earth-tone palette (color when feed live, grayscale when hidden)
- camstack broadcast editor: multiline support with Enter for newline, Ctrl+D to save & deliver, left/right cursor navigation, mid-text insert/delete
- camstack footer: dynamic word wrap at • boundaries, two-row layout
- Mute Buzzes button: now permanently blue (primary) for visual consistency
- Blinking • bullet on LIVE status in camstack header

### Changed
- snap_worker refresh interval: 5s (tuned from 2s for CPU stability)
- Widget capture size increased to 80×26 for terminal resize support

## [2.7.9] - 2026-04-24
### Fixed
- Repair completion status "OK" overriding header sys_status, causing "OK | feed hidden" to display in red instead of falling back to base status (LIVE/CONNECTING/DOWN)
- Removed dead color branch in `header_attr()` handling "OK" — unreachable after above fix

## [2.7.8] - 2026-04-24
### Fixed
- Packaging and setup audit: corrected dependency declarations, sudoers, service paths, and postinst to reach clean installable state on Debian and Arch

## [2.8.8] - 2026-05-02
- index.html: hostname now dynamic in title and header (works on any host)
- index.html: feed mode buttons inverted logic fixed (active=gray, inactive=blue)
- index.html: cancel button no longer lit on page load
- ffmpeg-cam.service template: User=root (was mediamtx, cross-contamination fix)
- camstack: version string updated to 2.8.8

## [2.8.9] - 2026-05-02
- index.html: feed mode button logic fixed (active=gray, inactive=blue)
- index.html: cancel button no longer lit on page load
- index.html: renamed CAM-01 to HLS Livecam

## [2.8.10] - 2026-05-04
- setup-arch: fix nginx log dir, http user, conf.d handling (Arch-specific)
- broadcast-api.service: revert DynamicUser, use www-data (setup substitutes http on Arch)

## [2.8.11] - 2026-05-04
- broadcast-api.service: revert DynamicUser, use www-data (setup substitutes http on Arch)

## [2.8.12] - 2026-05-04
- setup: use template for ffmpeg-cam.service (wrong file — patched hls-livecam-setup instead of hls-livecam-setup-arch, no effect)

## [2.8.13] - 2026-05-04
- setup-arch: use @PLACEHOLDER@ template for ffmpeg-cam.service ExecStart, eliminating ${VAR} word-splitting bug

## [2.8.14] - 2026-05-04
- index.html: remove hardcoded primary class from showBtn
- index.html: rename Cloak to Blur
