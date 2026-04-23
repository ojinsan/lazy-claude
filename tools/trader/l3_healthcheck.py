"""Pre-run gate for L3 monitoring (spec #5 §6 step 2).

Aborts if:
- Current WIB time outside 09:00-15:30.
- Universe empty (all three lists: superlist, exitlist, holdings).
- Orderbook state dir missing.
"""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path

from tools._lib.current_trade import CurrentTrade

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_OB_DIR = str(WORKSPACE / "runtime" / "monitoring" / "orderbook_state")

MARKET_OPEN  = _dt.time(9, 0)
MARKET_CLOSE = _dt.time(15, 30)
WIB = _dt.timezone(_dt.timedelta(hours=7))


def check(ct: CurrentTrade, now_wib: _dt.datetime | None = None, orderbook_state_dir: str | None = None) -> dict:
    now_wib = now_wib or _dt.datetime.now(WIB)
    t = now_wib.timetz().replace(tzinfo=None)
    if not (MARKET_OPEN <= t <= MARKET_CLOSE):
        return {"ok": False, "reason": f"market closed ({t.strftime('%H:%M')} outside 09:00-15:30 WIB)"}

    if not ct.lists.superlist and not ct.lists.exitlist and not ct.trader_status.holdings:
        return {"ok": False, "reason": "empty universe"}

    ob_dir = orderbook_state_dir or DEFAULT_OB_DIR
    if not os.path.isdir(ob_dir):
        return {"ok": False, "reason": f"no tape source at {ob_dir}"}

    return {"ok": True, "reason": "ok"}
