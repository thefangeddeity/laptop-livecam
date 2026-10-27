#!/usr/bin/env bash
# Fetch the detector model. It is NOT in the repo.
#
# A 12.3 MiB ONNX was tracked here and nothing installed it: neither the
# PKGBUILD nor deploy_tina.sh referenced it, and the file the nodes actually
# load sits at models/candidates/ and is owned by no package -- hand-placed,
# and therefore tracked nowhere. So the repo carried the weight of the model
# in every clone while the running fleet used a copy it did not describe.
#
# The model already had a proper home: the models-v1 release. This is the
# missing half -- the step that puts it on a node reproducibly instead of
# whoever-downloaded-it-last.
set -euo pipefail

REPO="${REPO:-thefangeddeity/laptop-livecam}"
TAG="${MODEL_TAG:-models-v1}"
NAME="${MODEL_NAME:-yolov8n.onnx}"
DEST="${1:-/usr/share/hls-livecam-server/models/candidates}"

echo "fetching $NAME from $REPO@$TAG -> $DEST"
mkdir -p "$DEST"

if command -v gh >/dev/null 2>&1; then
  gh release download "$TAG" --repo "$REPO" --pattern "$NAME" --dir "$DEST" --clobber
else
  curl -fsSL -o "$DEST/$NAME" \
    "https://github.com/$REPO/releases/download/$TAG/$NAME"
fi

# A truncated download is worse than a missing one: it fails at the first
# detection instead of at install time.
sz=$(stat -c%s "$DEST/$NAME" 2>/dev/null || stat -f%z "$DEST/$NAME")
if [ "$sz" -lt 1000000 ]; then
  echo "ERROR: $DEST/$NAME is only $sz bytes -- download failed" >&2
  exit 1
fi
echo "ok: $DEST/$NAME ($sz bytes)"
