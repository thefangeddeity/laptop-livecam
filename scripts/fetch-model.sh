#!/usr/bin/env bash
# Fetch the detector model. It is a release asset, not repo content.
set -euo pipefail

REPO="${REPO:-thefangeddeity/laptop-livecam}"
TAG="${MODEL_TAG:-models-v1}"
NAME="${MODEL_NAME:-yolov8n.onnx}"
# The same hash the PKGBUILD pins. A size check only proves the download was
# not an error page; this proves it is the model the fleet is tested against.
SHA="${MODEL_SHA256:-b2bc52f40e8e1c532427d5bde3575a5d5b571b739fab2c6df443733ed1589cbd}"
DEST="${1:-/usr/share/hls-livecam-server/models/candidates}"

mkdir -p "$DEST"
tmp="$DEST/$NAME.part"
echo "fetching $NAME from $REPO@$TAG"
curl -fsSL -o "$tmp" "https://github.com/$REPO/releases/download/$TAG/$NAME"

got="$(sha256sum "$tmp" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$tmp" | cut -d' ' -f1)"
if [ "$got" != "$SHA" ]; then
  rm -f "$tmp"
  echo "ERROR: checksum mismatch for $NAME" >&2
  echo "  expected $SHA" >&2
  echo "  got      $got" >&2
  exit 1
fi

mv "$tmp" "$DEST/$NAME"
chmod 0644 "$DEST/$NAME"
echo "ok: $DEST/$NAME"
