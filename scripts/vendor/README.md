# vendor/

`esprima` — pure-Python JavaScript parser, BSD licensed.

Vendored rather than installed because the check that uses it must run in
every build environment, and it did not: the Debian build calls system
`python3`, which has no esprima, so `check-viewer.py` printed `ok` having
parsed no JavaScript at all. An indicator that cannot fail is decoration.

Arch has no `python-esprima` package and PEP 668 blocks `pip install` on
these nodes, so vendoring is what makes the check unconditional.
