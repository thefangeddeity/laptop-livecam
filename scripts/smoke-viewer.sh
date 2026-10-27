#!/usr/bin/env bash
# Load the viewer in a real browser and assert the page renders at all.
#
# SCOPE, stated honestly because two attempts to widen it failed:
#
#   It proves  : the URL serves, Firefox parses it, a frame is painted.
#   It does NOT: catch a runtime JavaScript error (headless Firefox does not
#                surface console output to stdout or stderr, even with
#                devtools.console.stdout.content), and it does NOT catch a
#                page that printed its own source as text -- that renders
#                perfectly well, and on a dark theme it even has the same
#                dark-pixel profile as the real viewer. Both of those were
#                tried and both gave false passes against the exact break
#                that shipped.
#
# check-viewer.py is the gate for that break and catches it reliably. This
# is a second, weaker gate for "the page does not load at all", which that
# static check cannot see.
#
# Detecting more needs DOM access -- Marionette or a devtools client -- which
# is not worth a dependency on these nodes.
set -uo pipefail

URL="${1:-http://127.0.0.1:8080/llc}"
FF="${FIREFOX:-/Applications/Firefox.app/Contents/MacOS/firefox}"
[ -x "$FF" ] || FF="$(command -v firefox || true)"

if [ -z "$FF" ] || [ ! -x "$FF" ]; then
  echo "skip: no Firefox on this host -- smoke test not run" >&2
  exit 0
fi

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
mkdir -p "$work/profile"
shot="$work/shot.png"

"$FF" --headless --profile "$work/profile" --screenshot "$shot" \
      --window-size=1280,900 "$URL" >/dev/null 2>"$work/err" &
pid=$!
for _ in $(seq 1 40); do [ -s "$shot" ] && break; sleep 1; done
sleep 2; kill $pid 2>/dev/null; wait $pid 2>/dev/null

if [ ! -s "$shot" ]; then
  echo "FAIL: $URL never rendered" >&2
  sed -n '1,8p' "$work/err" >&2
  exit 1
fi

echo "ok   smoke: $URL rendered ($(wc -c <"$shot" | tr -d ' ') byte frame)"
