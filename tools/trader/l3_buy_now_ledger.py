"""Daily idempotency ledger for L3 BUY-NOW events.

Prevents double-invoking /trade:tradeplan for the same ticker within one day.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
LEDGER_DIR = str(WORKSPACE / "runtime" / "monitoring")


def _path_for(d: _dt.date) -> str:
    return os.path.join(LEDGER_DIR, f"buy_now_fired_{d.isoformat()}.json")


def _today_wib() -> _dt.date:
    tz = _dt.timezone(_dt.timedelta(hours=7))
    return _dt.datetime.now(tz).date()


def load(d: _dt.date | None = None) -> set[str]:
    d = d or _today_wib()
    path = _path_for(d)
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def record(ticker: str, d: _dt.date | None = None) -> None:
    d = d or _today_wib()
    os.makedirs(LEDGER_DIR, exist_ok=True)
    fired = load(d)
    fired.add(ticker)
    with open(_path_for(d), "w") as f:
        json.dump(sorted(fired), f)
