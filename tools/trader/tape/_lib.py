"""
Shared helpers for tape reading modules.
Composes: api.get_stockbit_orderbook, api.get_stockbit_running_trade, api.get_orderbook_delta.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import tools.trader.api as api

# Thresholds
BANDAR_LOT_MIN = 20_000        # lots at one price level to qualify as bandar-sized
BANDAR_FREQ_MAX = 10           # max freq accounts at level for bandar classification
SPAM_WINDOW_SEC = 60           # seconds window for spam detection
SPAM_HAKA_MIN = 5              # min HAKA trades to flag spam
CROSSING_LOT_MIN = 100_000     # min lot for cross-trade flag
WALL_LOT_THRESHOLD = 50_000    # minimum lots to treat a level as a "wall"


def load_orderbook(ticker: str) -> dict:
    ob = api.get_stockbit_orderbook(ticker.upper())
    return ob if ob and "error" not in ob else {}


def load_trade_book(ticker: str, lookback_sec: int = 300) -> list[dict]:
    data = api.get_stockbit_running_trade(ticker.upper(), limit=200)
    if not isinstance(data, dict):
        return []
    trades = data.get("running_trade", data.get("rows", []))
    return trades


def load_running(ticker: str, limit: int = 100) -> list[dict]:
    return api.get_running_trades(ticker.upper(), limit=limit)


def load_orderbook_delta(ticker: str) -> dict:
    return api.get_orderbook_delta(ticker.upper())
