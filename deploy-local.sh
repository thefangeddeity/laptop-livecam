#!/usr/bin/env bash
# Deploy the repo's staged pkg/ files to Tanzania's live system paths, with a
# timestamped backup of what's replaced, then reload/restart. Run with sudo:
#     sudo bash deploy-local.sh
set -euo pipefail

# Derived, not hardcoded: this runs under sudo, so $HOME would be root's,
# and a hardcoded /home/<user> both breaks on any other machine and puts a
# real username in a public repo.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BK="$(dirname "$REPO")/_backups/LIVE-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BK"

# NOTE: the live docroot is nginx `root /var/www/hls-livecam` -- NOT
# /usr/share/hls-livecam-server (a stale leftover the server does not read).
declare -A MAP=(
  ["$REPO/pkg/usr/share/hls-livecam-server/index.html"]="/var/www/hls-livecam/index.html"
  ["$REPO/pkg/usr/local/bin/broadcast-api"]="/usr/local/bin/broadcast-api"
  ["$REPO/pkg/etc/nginx/conf.d/hls-livecam.conf"]="/etc/nginx/conf.d/hls-livecam.conf"
  # The capability prober and its publisher. These were hand-copied to
  # /usr/local/lib once, which is exactly the untracked-artifact failure
  # this script exists to end: a file running the node that no tree owns
  # and nothing can diff against.
  ["$REPO/pkg/usr/local/lib/livecam-tools/node-capabilities"]="/usr/local/lib/livecam-tools/node-capabilities"
  ["$REPO/pkg/usr/local/lib/livecam-tools/publish-capabilities"]="/usr/local/lib/livecam-tools/publish-capabilities"
)
# /etc/hls-livecam/notches.json is deliberately NOT in MAP or the payload:
# it's curated, per-room tuning data (the live 12-entry list is nothing like
# the repo's old seed), and it was never installed over here anyway -- only
# backed up. The .deb payload used to ship a stale seed copy under this same
# path with no conffiles guard, so every package upgrade would have silently
# clobbered a live-tuned list; that seed file is now removed from the
# package entirely (same fix already applied to cams.json once before).
# Live backups of whatever's on disk still happen below, unconditionally.
BK_NOTCHES="/etc/hls-livecam/notches.json"

echo "== backing up live files to $BK =="
for src in "${!MAP[@]}"; do
  dst="${MAP[$src]}"
  [ -f "$dst" ] && cp -a "$dst" "$BK/$(basename "$dst")" && echo "  backed up $dst"
done
[ -f "$BK_NOTCHES" ] && cp -a "$BK_NOTCHES" "$BK/notches.json" && echo "  backed up $BK_NOTCHES"
# vendored player dir (new: the live node is 404 on /vendor/hls.min.js)
[ -f /usr/share/hls-livecam-server/vendor/hls.min.js ] && \
  cp -a /usr/share/hls-livecam-server/vendor/hls.min.js "$BK/hls.min.js.live" || true

echo "== installing =="
install -D -m0644 "$REPO/pkg/usr/share/hls-livecam-server/vendor/hls.min.js" \
        /usr/share/hls-livecam-server/vendor/hls.min.js
echo "  installed /usr/share/hls-livecam-server/vendor/hls.min.js"
install -m0644 "$REPO/pkg/usr/share/hls-livecam-server/index.html" /var/www/hls-livecam/index.html
echo "  installed index.html"
install -m0755 "$REPO/pkg/usr/local/bin/broadcast-api" /usr/local/bin/broadcast-api
echo "  installed broadcast-api"
install -m0644 "$REPO/pkg/etc/nginx/conf.d/hls-livecam.conf" /etc/nginx/conf.d/hls-livecam.conf
echo "  installed nginx conf"
# -D so a fresh node gets /usr/local/lib/livecam-tools/ created rather than
# failing on a missing parent. These were hand-placed once; a file running a
# node that no tree owns is the failure this script exists to end.
install -D -m0755 "$REPO/pkg/usr/local/lib/livecam-tools/node-capabilities" \
        /usr/local/lib/livecam-tools/node-capabilities
install -D -m0755 "$REPO/pkg/usr/local/lib/livecam-tools/publish-capabilities" \
        /usr/local/lib/livecam-tools/publish-capabilities
echo "  installed capability tools"
/usr/local/lib/livecam-tools/publish-capabilities >/dev/null 2>&1 \
  && echo "  capabilities.json republished" \
  || echo "  WARNING: capability probe failed; capabilities.json left stale"

echo "== python syntax check on installed broadcast-api =="
python3 -m py_compile /usr/local/bin/broadcast-api && echo "  broadcast-api: py OK"

echo "== nginx config test + reload =="
nginx -t && systemctl reload nginx && echo "  nginx reloaded"

echo "== restart broadcast-api =="
systemctl restart broadcast-api && echo "  broadcast-api restarted"

echo "== done. verifying =="
sleep 2
curl -s -m8 -o /dev/null -w "  home   :8080/    -> %{http_code}\n" http://127.0.0.1:8080/
curl -s -m8 -o /dev/null -w "  viewer :8080/llc -> %{http_code}\n" http://127.0.0.1:8080/llc
curl -s -m8 -o /dev/null -w "  /vendor/hls.min.js -> %{http_code}\n" http://127.0.0.1:8080/vendor/hls.min.js

# The viewer is at /llc, not /. Since 496108f ("Home at /, camera at /llc")
# / serves home.html, which has no player tag in it at all -- so this check
# was grepping a 9KB page that could never match, grep -o returned 1, and
# under this script's `set -euo pipefail` the whole deploy ABORTED here,
# after the files were already installed and the services already restarted.
# A verification step that kills the run it is verifying, at the last line,
# having done its job silently wrong for a month.
#
# Captured first and matched against the string, rather than piped into
# `grep -o ... | head -1`: with pipefail, head exits at the first line and
# the producer takes SIGPIPE, which is a second way for this line to fail on
# a page that is perfectly fine. And `|| true`, because what this prints is
# a diagnostic -- it is not the deploy's verdict and must not be able to
# decide it.
VIEWER_HTML="$(curl -s -m8 http://127.0.0.1:8080/llc || true)"
case "$VIEWER_HTML" in
    *"/vendor/hls.min.js"*) echo "  viewer player src: /vendor/hls.min.js (same-origin)" ;;
    *cdnjs*)                echo "  viewer player src: cdnjs -- EXPECTED same-origin" ;;
    "")                     echo "  viewer player src: could not fetch /llc" ;;
    *)                      echo "  viewer player src: no player tag found" ;;
esac
echo "  backup of replaced files: $BK"
