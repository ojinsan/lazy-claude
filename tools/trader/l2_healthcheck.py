"""Pre-run gate for L2 screening (spec #4 §6 step 2).

Aborts L2 if any of the following holds:
- Both watchlist and holdings are empty (nothing to judge).
- L1 layer_run is missing, not `ok`, or older than 6 hours (stale upstream).
- Both yesterday broker-flow caches are missing (no dim-2 signal available).
"""
from __future__ import annotations

import datetime as _dt
import os

from tools._lib.current_trade import CurrentTrade

L1_MAX_AGE_HOURS = 6


def _parse_ts(ts: str | None) -> _dt.datetime | None:
    if not ts:
        return None
    s = ts.replace("Z", "+00:00")
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def check(ct: CurrentTrade, hapcu_path: str, retail_path: str) -> dict:
    if not ct.lists.watchlist and not ct.trader_status.holdings:
        return {"ok": False, "reason": "watchlist and holdings both empty"}

    l1 = ct.layer_runs.get("l1")
    l1_ts = _parse_ts(getattr(l1, "last_run", None)) if l1 else None
    if l1_ts is None:
        return {"ok": False, "reason": "L1 layer_run missing or unparseable last_run"}
    age = _dt.datetime.now(_dt.timezone.utc) - l1_ts
    if age > _dt.timedelta(hours=L1_MAX_AGE_HOURS):
        return {"ok": False, "reason": f"L1 stale {int(age.total_seconds() / 60)}min (>{L1_MAX_AGE_HOURS}h)"}

    if not os.path.exists(hapcu_path) and not os.path.exists(retail_path):
        return {"ok": False, "reason": "both broker-flow caches missing"}

    return {"ok": True, "reason": "ok"}
