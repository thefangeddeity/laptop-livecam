
# NO BYTECODE NEXT TO THE SOURCE -- see bin/broadcast-api for the full
# reasoning. Short version: this package lives inside the .app, a .pyc
# written beside it breaks the bundle's seal, and TCC drops the camera grant
# when the seal is repaired. Set in code because not every process that
# imports this comes through the launcher that exports the variable.
import sys
sys.dont_write_bytecode = True

