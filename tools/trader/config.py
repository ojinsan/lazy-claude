from __future__ import annotations
import os, json
from pathlib import Path

WORKSPACE = Path('/home/lazywork/workspace')
RUNTIME = WORKSPACE / 'runtime'
LOG_DIR = RUNTIME / 'logs'
MONITORING_DIR = RUNTIME / 'monitoring'
WATCHLIST_DIR = RUNTIME / 'watchlists'
ORDERBOOK_STATE_DIR = MONITORING_DIR / 'orderbook_state'
LOCAL_NOTES_DIR = MONITORING_DIR / 'notes'
TOKEN_CACHE_DIR = RUNTIME / 'tokens'
ENV_PATH = WORKSPACE / '.env.local'
WATCHLIST_FILE = WATCHLIST_DIR / 'active.json'

for p in [LOG_DIR, MONITORING_DIR, WATCHLIST_DIR, ORDERBOOK_STATE_DIR, LOCAL_NOTES_DIR, TOKEN_CACHE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k, v)

def backend_url() -> str:
    load_env()
    return os.environ.get('BACKEND_URL', 'https://api-magibook.lazywork.dev').rstrip('/')

def backend_token() -> str:
    load_env()
    return os.environ.get('API_TOKEN', '')

def stockbit_token_cache() -> Path:
    return TOKEN_CACHE_DIR / 'stockbit_token.json'

def ensure_watchlist_file():
    if not WATCHLIST_FILE.exists():
        WATCHLIST_FILE.write_text(json.dumps({}, indent=2))
    return WATCHLIST_FILE
