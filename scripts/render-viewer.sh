#!/usr/bin/env bash
# Render web/index.html from the template, then validate it.
#
# This exists because the version was hand-substituted during a long editing
# session and got pinned at 1.8.0 while the tag moved to 1.8.1 -- the viewer
# then reported a version that no longer matched the tree. Derive it, do not
# type it. Same source as the DMG build, so the two cannot disagree.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VERSION="$(git -C "$ROOT" describe --tags --always 2>/dev/null || echo unknown)"
LABEL="$VERSION"
HLS_PORT="$(sed -n 's/^HLS_PORT=//p' "$ROOT/config.env" 2>/dev/null | head -1)"
HLS_PORT="${HLS_PORT:-8888}"

sed -e "s|@VERSION@|${VERSION}|g" \
    -e "s|@BUILD_LABEL@|${LABEL}|g" \
    -e "s|@HLS_PORT@|${HLS_PORT}|g" \
  "$ROOT/web/index.template.html" > "$ROOT/web/index.html"

"$ROOT/scripts/check-viewer.py" "$ROOT/web/index.html"
echo "rendered at $VERSION"
