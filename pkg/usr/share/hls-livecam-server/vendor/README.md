# Vendored third-party code

Not ours. Do not edit these files to fix our bugs; fix them upstream or
replace the vendored copy wholesale.

## pyfakewebcam 0.1.0

- Upstream: https://github.com/jremmons/pyfakewebcam
- License: GPL-3.0 (compatible with this project, GPL-3.0-or-later)
- Taken from: Arch package `python-pyfakewebcam 0.1.0-1`, which ships the
  `tobytes()` form already. Do not re-introduce the `tostring()` patch.

### Why this is vendored

Debian and Ubuntu do not package pyfakewebcam (checked on Ubuntu 26.04:
`apt-cache policy python3-pyfakewebcam` finds nothing). Until 7.0.12 the
Debian `postinst` therefore ran, as root, at install time:

    python3 -m pip install pyfakewebcam --break-system-packages ... || true

and then rewrote the installed library source in place to swap the
numpy-removed `tostring()` for `tobytes()`.

Three things were wrong with that:

1. It needed the network to complete a package install, and `|| true`
   meant a failed install still reported success. The breakage surfaced
   later, as a camera that would not start.
2. It wrote into `/usr/local/lib/python3*/dist-packages`, which no package
   manager owns, so the files were never removed on uninstall.
3. The patch had become a no-op: upstream pyfakewebcam already uses
   `tobytes()`, so it was rewriting a file that did not need rewriting.

Arch was never affected -- the PKGBUILD declares `python-pyfakewebcam` as a
normal dependency. `broadcast-api` still prefers a system-installed
pyfakewebcam and falls back to this copy, so Arch behaviour is unchanged.
