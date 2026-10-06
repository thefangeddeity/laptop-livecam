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
- `usr/local/etc/mediamtx.yml`: MediaMTX.
- `systemd/`: the units. mediamtx and broadcast-api are enabled at boot; nginx too.

## Boot

Boots to the graphical target (LightDM, then Cinnamon). The livecam starts at boot. The
organism (cambrian-perception) does not: its autostart is off and its target is disabled.

## Restore

Check out each file at the commit above into the live path (or `deploy-local.sh` from a
checkout at that commit), copy the configuration back, then
`systemctl restart broadcast-api mediamtx && systemctl reload nginx`.
