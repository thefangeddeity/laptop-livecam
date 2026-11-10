# Tanzania: the live livecam install, captured 2026-10-05 21:43 -05

What is actually running on Tanzania (Arch), so it can be rebuilt exactly.
The installed Arch package is `hls-livecam-server 6.0.7-1` (its VERSION
file still says 6.0.7), but the files below were deployed over it
with `deploy-local.sh`, so the package version does not describe what runs.

## Code: live file = this commit

| Live path | Repo path | Commit |
|---|---|---|
| /var/www/hls-livecam/index.html | pkg/usr/share/hls-livecam-server/index.html | 034829c, plus the Video panel moved above Audio (2026-10-05, also on main); (2026-09-11, index.html: flag NATIVE fallback in the HLS status text) |
| /usr/local/bin/broadcast-api | pkg/usr/local/bin/broadcast-api | 50b06ad (2026-09-10, Tanzania: cascaded low-pass stages, and document the not-live-reloadable trap) |
| /etc/nginx/conf.d/hls-livecam.conf | pkg/etc/nginx/conf.d/hls-livecam.conf | b413989 (2026-09-07, Tanzania: port Ariana's audio/UI parity — true two-way (RTC), split graph, global reset) |
| /usr/local/bin/camdash | pkg/usr/local/bin/camdash | e7ec59c (2026-08-25, Scene registration leaves the livecam panel; camdash reports room audio) |
| /usr/local/bin/hls-livecam-setup | pkg/usr/share/hls-livecam-server/hls-livecam-setup-arch | 296d46e (2026-08-26, Packaging: one copy of the viewer, and everything the viewer needs) |
| /usr/share/hls-livecam-server/cv_detect.py | pkg/usr/share/hls-livecam-server/cv_detect.py | 42fa740 (2026-09-11, cv_detect: stop burning HUD banner/capability text into the picture) |
| /usr/share/hls-livecam-server/vendor/hls.min.js | pkg/usr/share/hls-livecam-server/vendor/hls.min.js | f43411d (2026-09-03, Tanzania: the iOS baseline, four faults that compound into a blank page) |

## Configuration: not in the package, copied here

- `etc/hls-livecam/device.env`: devices and plumbing (admin tier).
- `etc/hls-livecam/notches.json`: the notch list. The ones marked "from Ariana" are on;
  Tanzania's own earlier list is kept, switched off.
- `var/lib/hls-livecam/audio.json`: the Settings panel's audio values (high-pass 60 Hz,
  low-pass 14000 Hz, inbound and outbound gain 0 dB, speaker not muted), copied from Ariana's.
- `var/lib/hls-livecam/feed_mode`: the video mode.
- `var/lib/hls-livecam/{notify_presence_pause,privacy_mask,mask_style,detect_roi,
  notify_shots,notify_video,notify_classes,detect_always,blur_mode,msg_lock}`: the
  privacy and alert switches, read from tanzania's own drive on 2026-11-10.
  "Never film people" is on, the mask is on (black), the region is the right-hand
  part of the room. Setup does not write these; with presence_pause absent a fresh install films
  people and never sends "<Node>: Cat detected, no <media> due to person present."
  -- which is what Spitsbergen did after its install.
- `usr/local/etc/mediamtx.yml`: MediaMTX. Equal to what setup writes, plus `cam: record: no`
  (mediamtx's own recording is off; the evidence recorder in broadcast-api records instead).
- `etc/udev/rules.d/61-usb-root-write-through.rules`: NODE-SPECIFIC. Turns the write cache off
  on tanzania's USB system drive (Toshiba enclosure, no FUA), after a clean shutdown left
  half-written inode blocks on 2026-09-25. Matches by serial, so it is inert anywhere else;
  a node booting from a USB disk needs its own copy with its own serial.
- `etc/udev/rules.d/69-hdparm.rules`: APM 254 on the rotational sda (no spin-down).
- `etc/modprobe.d`, `etc/modules-load.d`: v4l2loopback (setup writes the same) and snd-aloop
  (setup does NOT; only needed with AUDIO_SINGLE_SESSION=1, which is 0 here).
- `etc/sudoers.d/hls-livecam-studio`: as setup writes it.
- Refreshed from the live system on 2026-11-10 (booted from this drive by accident; full
  snapshot on osiris: repos/backups/llc-live/tanzania-llc-live-20261110-114057.tgz).
  device.env carries three stray `lili` lines (since Aug 26); setup from 7.2.1 drops them.
  It also still has CV_SCENE_ENABLED=1 with the scene model retired on Sep 8.
- `systemd/`: the units. mediamtx and broadcast-api are enabled at boot; nginx too.

## Boot

Boots to the graphical target (LightDM, then Cinnamon). The livecam starts at boot. The
organism (cambrian-perception) does not: its autostart is off and its target is disabled.

## Restore

Check out each file at the commit above into the live path (or `deploy-local.sh` from a
checkout at that commit), copy the configuration back, then
`systemctl restart broadcast-api mediamtx && systemctl reload nginx`.
