# Laptop LiveCam

Turns an old laptop into a camera appliance: live video in a browser, room
audio, cat/person detection, and Telegram alerts when something walks past.

![camdash TUI monitor](screenshots/camstack.jpg)

## Install

Grab an installer from **[Releases](https://github.com/thefangeddeity/laptop-livecam/releases/latest)**.

| Platform | File | Then |
|---|---|---|
| macOS | `...-macOS.dmg` | Drag to Applications, run once to set up |
| Debian / Ubuntu | `...-amd64.deb` | `sudo apt install ./<file>` then `sudo hls-livecam-setup` |
| Arch | `...-Arch.pkg.tar.zst` | `sudo pacman -U <file>` — or `yay -S laptop-livecam` |

Use `apt install ./file.deb`, not `dpkg -i`: apt pulls the dependencies.

Then open `http://<the-machine>:8080/llc`.

## What it does

- **Video** — HLS stream from a USB or built-in camera, viewable in any browser.
- **Audio** — the room, over the same page. Optional.
- **Detection** — YOLO spots people, cats, dogs, birds; Telegram gets a photo or a clip.
- **Privacy** — draw a box and everything outside it is hidden before encoding, so
  clips and snapshots inherit it. "Never film people" detects them without recording them.
- **Who's who** — name the animals it sees and browse their pictures.
- **camdash** — a terminal monitor for the whole pipeline.

## Commands

```
hls-livecam-setup     # configure the node (run once, as root)
camdash               # terminal monitor
livecam start|stop|restart|status
```

## Layout

```
pkg/        what gets installed on a node, mirroring the filesystem
scripts/    build, deploy and release helpers
gui/        the desktop monitor
hosts/      per-node unit files and manifests
docs/       notes
```

Branches: `main` is Linux (Debian + Arch), `macos` is the Mac build, `windows`
is an in-progress Rust port.

## Requirements

ffmpeg, nginx, python3 with flask / numpy / opencv / pillow / psutil,
v4l-utils. The installers pull these for you.

The detector model is not in this repo — it is a release asset, and both
installers fetch it. To place it by hand: `scripts/fetch-model.sh`.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

More detail in [CHANGELOG.md](CHANGELOG.md) and [PENDING.md](PENDING.md).
