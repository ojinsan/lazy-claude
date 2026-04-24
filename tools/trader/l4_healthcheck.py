"""L4 pre-run gates.

Mode A batch: iterate superlist+exitlist with {buy,sell}_at_price and plan=None.
Mode A single or Mode B: specific ticker, wait_bid_offer skipped, dup guard by mode+date.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md §8.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from tools._lib.current_trade import CurrentTrade, ListItem

TICKER_RE = re.compile(r"^[A-Z]{1,6}$")
WIB = timezone(timedelta(hours=7))


def _find(ct: CurrentTrade, ticker: str) -> Optional[ListItem]:
    for lst in (ct.lists.superlist, ct.lists.exitlist):
        for it in lst:
            if it.ticker == ticker:
                return it
    return None


def _is_today_wib(iso: str, now: datetime) -> bool:
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(iso)
    except Exception:
        return False
    return dt.astimezone(WIB).date() == now.astimezone(WIB).date()


def _side_for(item: ListItem) -> str:
    if item.current_plan and item.current_plan.mode == "sell_at_price":
        return "sell"
    return "buy"


def check(
    ct: CurrentTrade,
    mode: str,
    ticker: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict:
    """Returns:
        {"ok": True, "ticker": t}            # single-ticker path
        {"ok": True, "queue": [t, ...]}      # Mode A batch
        {"ok": False, "reason": str}         # aborted
    """
    ts = ct.trader_status
    if (ts.aggressiveness or "").lower() == "off":
        return {"ok": False, "reason": "aggressiveness=off (kill-switch)"}
    if now is None:
        now = datetime.now(WIB)

    if ticker is not None:
        if not TICKER_RE.match(ticker):
            return {"ok": False, "reason": f"invalid ticker {ticker!r}"}
        item = _find(ct, ticker)
        if not item:
            return {"ok": False, "reason": f"{ticker} not in superlist/exitlist"}
        cp_mode = item.current_plan.mode if item.current_plan else ""
        if cp_mode == "wait_bid_offer":
            return {"ok": False, "reason": f"{ticker} wait_bid_offer — not ready"}
        if cp_mode not in ("buy_at_price", "sell_at_price"):
            return {"ok": False, "reason": f"{ticker} current_plan.mode={cp_mode!r} — not actionable"}
        if item.plan and _is_today_wib(item.plan.updated_at, now) and item.plan.mode == mode:
            return {"ok": False, "reason": f"{ticker} duplicate plan today (mode={mode})"}
        if cp_mode == "buy_at_price" and ts.balance.buying_power <= 0:
            return {"ok": False, "reason": "buying_power<=0"}
        return {"ok": True, "ticker": ticker}

    # Mode A batch
    queue: list[str] = []
    has_buy_side = False
    for lst in (ct.lists.superlist, ct.lists.exitlist):
        for it in lst:
            if not it.current_plan:
                continue
            if it.current_plan.mode not in ("buy_at_price", "sell_at_price"):
                continue
            if it.plan and _is_today_wib(it.plan.updated_at, now) and it.plan.mode == "A":
                continue
            queue.append(it.ticker)
            if it.current_plan.mode == "buy_at_price":
                has_buy_side = True
    if not queue:
        return {"ok": False, "reason": "empty queue"}
    if has_buy_side and ts.balance.buying_power <= 0:
        return {"ok": False, "reason": "buying_power<=0 (batch has buy-side)"}
    return {"ok": True, "queue": queue}
