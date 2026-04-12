# Shim: exposes trader/ modules as the 'skills' Python package.
# Allows screener.py's 'from skills import api' to resolve correctly
# while preserving relative imports inside trader/*.py.
