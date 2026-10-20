#!/usr/bin/env bash
# Deploy the current committed .deb to tina. Takes its version from
# pkg/DEBIAN/control, builds from HEAD, and refuses to run if pkg/ is dirty.
#
# Written for the 6.0.7 -> 7.0.5 package RENAME (hls-livecam-server ->
# laptop-livecam), which is not an ordinary upgrade, and kept general
# afterwards because the parts that make it safe are not rename-specific:
# capture before, re-assert after, verify independently. Read
# pkg/DEBIAN/prerm's comment block for the rename story. Its short version
# is that dpkg removes the old package rather than upgrading it, so the OLD
# prerm runs its full teardown and three things do not come back on their
# own. On a same-name upgrade (7.0.5 onward) only the second of these
# applies, and the restore steps below are no-ops rather than wrong:
#
#   1. mediamtx and broadcast-api are stopped AND disabled.
#   2. /etc/nginx/conf.d/hls-livecam.conf is payload with no conffiles
#      declaration, so dpkg overwrites it with no prompt and no .dpkg-old.
#      On tina that file is the ONLY one carrying TLS -- the 301 to
#      https://tina.humboldt-polaris.ts.net and the listen 8443 ssl block.
#      The repo's copy is `listen 8080;` and nothing else.
#   3. The sudoers drop-ins hls-livecam-dark, hls-livecam-services and
#      camdash-smart are deleted. The package has never shipped them, so
#      nothing in the payload restores them.
#
# 7.0.5's preinst/postinst recover (1) by themselves. This script handles
# (2) and (3), and re-asserts (1) against MEASURED prior state rather than
# trusting the recovery, because the recovery cannot know what was enabled.
#
# tina is the live family camera. Every step is failure-gated and every
# claim below is checked rather than announced.
set -euo pipefail

HOST=tina
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VER="$(sed -n 's/^Version: //p' "$REPO/pkg/DEBIAN/control")"
PKGNAME="$(sed -n 's/^Package: //p' "$REPO/pkg/DEBIAN/control")"
DEB="$PKGNAME"_"$VER"_amd64.deb
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# Set before any die() can fire: rollback_hint names it, and a preflight
# failure happens before the capture step has one to name.
BACKUP="(no backup taken -- failed before the capture step)"

say() { printf '\n== %s ==\n' "$*"; }
die() { printf '\nFAILED: %s\n' "$*" >&2; rollback_hint; exit 1; }

rollback_hint() {
    cat >&2 <<HINT

ROLLBACK, if you need it. Two steps, not one -- the 6.0.7 deb carries the
nginx config too, so reinstalling it clobbers TLS a second time:

  ssh $HOST 'sudo dpkg -i ~/tina-backups/hls-livecam-server_6.0.7_amd64.deb'
  ssh $HOST "sudo cp -p $BACKUP/hls-livecam.conf /etc/nginx/conf.d/hls-livecam.conf \\
             && sudo nginx -t && sudo systemctl reload nginx"
  ssh $HOST 'sudo systemctl enable --now mediamtx broadcast-api'
HINT
}

# --- 0. Preflight, before anything is built or copied -----------------
say "Preflight"
[ -n "$VER" ] && [ -n "$PKGNAME" ] \
    || die "could not read Package/Version out of pkg/DEBIAN/control"
git -C "$REPO" diff --quiet HEAD -- pkg/ \
    || die "pkg/ has uncommitted changes -- commit first so the .deb matches a commit"

# Refuse to reinstall the version already there. Not a safety rule -- dpkg
# would do it happily -- but a deploy that silently does nothing new is how
# you end up believing a fix is live when the build never got rebuilt.
INSTALLED="$(ssh "$HOST" "dpkg-query -W -f='\${Version}' $PKGNAME 2>/dev/null" || true)"
if [ "$INSTALLED" = "$VER" ]; then
    die "$HOST already has $PKGNAME $VER -- bump the version or uninstall first"
fi
echo "$HOST has ${INSTALLED:-no $PKGNAME}; deploying $VER"
# Build from the TAG, not from HEAD. This repo is a shared working tree --
# other sessions commit into it -- and during the 7.0.8 deploy HEAD moved
# between the clean-tree assert and `git archive`, so the .deb that shipped
# was built from a commit that had not existed when the run started. It was
# harmless that time: the extra commit touched only the clip path, which the
# target node has disabled. The version number was the casualty -- two
# different trees both declaring 7.0.8, one on each node.
#
# A tag cannot move under us, and requiring one also forces the version in
# control to correspond to something named. If v$VER does not exist, that is
# the error, not a reason to fall back to HEAD.
REF="v$VER"
git -C "$REPO" rev-parse -q --verify "refs/tags/$REF" >/dev/null \
    || die "no tag $REF -- tag the release before deploying it"
COMMIT="$(git -C "$REPO" rev-parse --short "$REF")"
git -C "$REPO" diff --quiet "$REF" -- pkg/ \
    || die "pkg/ differs from $REF -- the working tree is not what the tag says"
echo "building $DEB from $REF ($COMMIT)"

ssh "$HOST" 'test -f ~/tina-backups/hls-livecam-server_6.0.7_amd64.deb' \
    || die "no rollback artifact on $HOST:~/tina-backups/ -- build it from tag v6.0.7 first"
echo "rollback artifact present on $HOST"

# --- 1. Capture what is true now --------------------------------------
# Taken BEFORE the install, from the live node, because the recovery path
# in postinst explicitly cannot know it.
say "Capturing current state from $HOST"
BACKUP="$(ssh "$HOST" 'B=~/tina-preupgrade-$(date +%Y%m%d-%H%M%S); mkdir -p "$B"; echo "$B"')"
ssh "$HOST" "set -e
    sudo cp -p /etc/nginx/conf.d/hls-livecam.conf '$BACKUP/'
    for f in hls-livecam-dark hls-livecam-services camdash-smart hls-livecam-studio; do
        [ -f /etc/sudoers.d/\$f ] && sudo cp -p /etc/sudoers.d/\$f '$BACKUP/' || true
    done
    sudo cp -rp /etc/hls-livecam '$BACKUP/etc-hls-livecam'
    sudo cp -p /var/www/hls-livecam/index.html '$BACKUP/index.html.www'
    for u in mediamtx broadcast-api ffmpeg-cam nginx; do
        echo \"\$u enabled=\$(systemctl is-enabled \$u 2>&1) active=\$(systemctl is-active \$u 2>&1)\"
    done | sudo tee '$BACKUP/unit-state.txt' >/dev/null
    sudo chown -R ron:ron '$BACKUP'"
echo "backup: $HOST:$BACKUP"
ssh "$HOST" "cat '$BACKUP/unit-state.txt'"

NGINX_MD5_BEFORE="$(ssh "$HOST" 'md5sum /etc/nginx/conf.d/hls-livecam.conf | cut -d" " -f1')"
VIEWER_MD5_REPO="$(md5sum "$REPO/pkg/usr/share/hls-livecam-server/index.html" | cut -d' ' -f1)"

# --- 2. Build the .deb from a clean export of the commit --------------
# git archive, not a copy of the working tree: no __pycache__, no stray
# .bak files, and what ships is exactly what is committed.
say "Building $DEB from a clean export"
mkdir -p "$WORK/build"
git -C "$REPO" archive "$REF" pkg | tar -x -C "$WORK/build"
mv "$WORK/build/pkg" "$WORK/build/$PKGNAME"
find "$WORK/build/$PKGNAME" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$WORK/build/$PKGNAME" -type d -exec chmod 755 {} +
chmod 755 "$WORK/build/$PKGNAME/DEBIAN/"{preinst,postinst,prerm}
for s in preinst postinst prerm; do
    bash -n "$WORK/build/$PKGNAME/DEBIAN/$s" || die "DEBIAN/$s is not valid bash"
done
fakeroot dpkg-deb --build "$WORK/build/$PKGNAME" "$WORK/$DEB" >/dev/null
dpkg-deb -I "$WORK/$DEB" | grep -q "Version: $VER" || die "built .deb does not declare $VER"
echo "built $(du -h "$WORK/$DEB" | cut -f1) -- $(md5sum "$WORK/$DEB" | cut -d' ' -f1)"

# --- 3. Dry run, then install ----------------------------------------
say "Dry run on $HOST"
scp -q "$WORK/$DEB" "$HOST:/tmp/$DEB"
ssh "$HOST" "sudo dpkg --simulate -i /tmp/$DEB" || die "dpkg --simulate refused the package"

say "Installing on $HOST (the camera goes dark from here until step 4)"
ssh "$HOST" "sudo dpkg -i /tmp/$DEB" || die "dpkg -i failed -- node is mid-install, roll back"

# --- 4. Re-assert what the rename destroyed ---------------------------
# The order here matters more than it looks. Validating AFTER writing, and
# dying on failure, would leave an invalid config on disk while nginx keeps
# serving the one it already has loaded -- so every check below would pass
# and the node would look healthy. The breakage would surface at the next
# reload, logrotate, package action or reboot, detached from this script by
# hours, on the one node whose viewer is https-only. So: stash what dpkg
# installed, write ours, and put dpkg's back if ours does not validate.
# Being left on the package config is visibly broken and fixable in a
# minute; being left on an invalid file is invisible until it is not.
say "Restoring the nginx TLS config"
ssh "$HOST" "set -e
    sudo cp -p /etc/nginx/conf.d/hls-livecam.conf /tmp/hls-livecam.conf.frompkg
    sudo cp -p '$BACKUP/hls-livecam.conf' /etc/nginx/conf.d/hls-livecam.conf
    if ! sudo nginx -t; then
        echo 'restored config failed nginx -t; putting the package copy back' >&2
        sudo cp -p /tmp/hls-livecam.conf.frompkg /etc/nginx/conf.d/hls-livecam.conf
        exit 1
    fi
    sudo rm -f /tmp/hls-livecam.conf.frompkg" \
    || die "restored nginx config does not pass nginx -t (package copy left in place, TLS is DOWN)"
ssh "$HOST" 'sudo systemctl reload nginx' || die "nginx reload failed"

say "Restoring the sudoers drop-ins"
ssh "$HOST" "set -e
    for f in hls-livecam-dark hls-livecam-services camdash-smart hls-livecam-studio; do
        if [ -f '$BACKUP/'\$f ] && [ ! -f /etc/sudoers.d/\$f ]; then
            sudo install -o root -g root -m 0440 '$BACKUP/'\$f /etc/sudoers.d/\$f
            echo \"  restored \$f\"
        fi
    done
    sudo visudo -c -q" || die "sudoers did not validate after restore"

# Unit state, re-asserted against the capture rather than the recovery's
# guess. ffmpeg-cam on tina is enabled and FAILED -- the legacy capture
# path, already broken before this upgrade. It is restored to enabled and
# left stopped: putting it back as found, not pretending it is well.
say "Re-asserting unit state from the capture"
ssh "$HOST" "set -e
    while read -r unit en ac; do
        u=\$unit; want_en=\${en#enabled=}; want_ac=\${ac#active=}
        [ \"\$u\" = nginx ] && continue
        case \"\$want_en\" in
            enabled) sudo systemctl enable \"\$u\" >/dev/null 2>&1 || true ;;
            disabled|masked) sudo systemctl disable \"\$u\" >/dev/null 2>&1 || true ;;
        esac
        if [ \"\$want_ac\" = active ]; then
            sudo systemctl start \"\$u\" 2>/dev/null \
                || echo \"  WARNING: \$u was active before and will not start\"
        fi
        echo \"  \$u -> enabled=\$(systemctl is-enabled \$u 2>&1) active=\$(systemctl is-active \$u 2>&1) (was \$want_en/\$want_ac)\"
    done < '$BACKUP/unit-state.txt'"

# --- 5. Verify, independently of what the install said ----------------
say "Verification"
FAIL=0
check() { # label, actual, expected
    if [ "$2" = "$3" ]; then printf '  OK   %-34s %s\n' "$1" "$2"
    else printf '  FAIL %-34s got %s, wanted %s\n' "$1" "$2" "$3"; FAIL=1; fi
}

check "package version" \
      "$(ssh "$HOST" "dpkg-query -W -f='\${Version}' $PKGNAME 2>/dev/null")" "$VER"
check "old package gone" \
      "$(ssh "$HOST" 'dpkg -l hls-livecam-server 2>/dev/null | grep -c "^ii" || true')" "0"
check "broadcast-api active" \
      "$(ssh "$HOST" 'systemctl is-active broadcast-api')" "active"
check "mediamtx active" \
      "$(ssh "$HOST" 'systemctl is-active mediamtx')" "active"
check "nginx active" \
      "$(ssh "$HOST" 'systemctl is-active nginx')" "active"
check "nginx conf unchanged by install" \
      "$(ssh "$HOST" 'md5sum /etc/nginx/conf.d/hls-livecam.conf | cut -d" " -f1')" "$NGINX_MD5_BEFORE"
check "served viewer matches repo" \
      "$(ssh "$HOST" 'md5sum /var/www/hls-livecam/index.html | cut -d" " -f1')" "$VIEWER_MD5_REPO"
check "packaged viewer matches repo" \
      "$(ssh "$HOST" 'md5sum /usr/share/hls-livecam-server/index.html | cut -d" " -f1')" "$VIEWER_MD5_REPO"
check "https viewer answers 200" \
      "$(ssh "$HOST" 'curl -sk -o /dev/null -w "%{http_code}" https://localhost/llc')" "200"
check "http 8080 still redirects" \
      "$(ssh "$HOST" 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/')" "301"
check "sudoers drop-ins present" \
      "$(ssh "$HOST" 'ls /etc/sudoers.d/hls-livecam-dark /etc/sudoers.d/hls-livecam-services /etc/sudoers.d/camdash-smart 2>/dev/null | wc -l')" "3"
check "rename flag cleaned up" \
      "$(ssh "$HOST" 'test -f /var/lib/hls-livecam/renamed-from-hls-livecam-server && echo left || echo gone')" "gone"
check "cams.json survived" \
      "$(ssh "$HOST" 'test -s /var/www/hls-livecam/cams/cams.json && echo yes || echo no')" "yes"

ssh "$HOST" "rm -f /tmp/$DEB"

if [ "$FAIL" -ne 0 ]; then
    die "verification failed -- see above. Backup is at $HOST:$BACKUP"
fi

say "Done"
echo "$PKGNAME $VER on $HOST, from $COMMIT. Backup at $HOST:$BACKUP"
echo "ffmpeg-cam is intentionally left as it was found -- see step 4."
