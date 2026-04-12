import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from trader.api import *  # noqa
from trader import api as _m
# expose module-level attrs so 'from skills import api; api.fn()' works
globals().update({k: v for k, v in vars(_m).items() if not k.startswith('__')})
