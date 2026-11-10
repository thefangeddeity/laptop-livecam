#!/usr/bin/env bash
# Build the .deb release asset from a commit -- the build half of
# scripts/deploy_tina.sh, without the deploy, so a release does not need tina.
#
# Usage: packaging/deb/build-deb.sh [ref]   (default HEAD) -> ./laptop-livecam_<ver>_amd64.deb
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REF="${1:-HEAD}"
VER="$(git -C "$REPO" show "$REF:pkg/DEBIAN/control" | sed -n 's/^Version: //p')"
NAME="$(git -C "$REPO" show "$REF:pkg/DEBIAN/control" | sed -n 's/^Package: //p')"
DECLARED="$(git -C "$REPO" show "$REF:pkg/usr/share/hls-livecam-server/VERSION" | tr -d '[:space:]')"
[ "$VER" = "$DECLARED" ] || { echo "control says $VER, VERSION says $DECLARED" >&2; exit 1; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
git -C "$REPO" archive "$REF" pkg | tar -x -C "$WORK"
mv "$WORK/pkg" "$WORK/$NAME"
find "$WORK/$NAME" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$WORK/$NAME" -type d -exec chmod 755 {} +
chmod 755 "$WORK/$NAME/DEBIAN/"{preinst,postinst,prerm}
for s in preinst postinst prerm; do bash -n "$WORK/$NAME/DEBIAN/$s"; done
python3 "$REPO/scripts/check-viewer.py" "$WORK/$NAME/usr/share/hls-livecam-server/index.html"
OUT="$PWD/${NAME}_${VER}_amd64.deb"
fakeroot dpkg-deb --build "$WORK/$NAME" "$OUT" >/dev/null
echo "$OUT"
