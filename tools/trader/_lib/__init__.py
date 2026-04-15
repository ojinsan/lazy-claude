# Shim: makes trader/ modules importable as _lib.<module>
import sys
from pathlib import Path
_trader = str(Path(__file__).parent.parent)
if _trader not in sys.path:
    sys.path.insert(0, _trader)
