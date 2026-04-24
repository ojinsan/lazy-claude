"""L5 pre-run gates.

Aborts: telegram warn + layer_runs['l5'].status='skipped'.

Paths:
  pre_open  — 08:00–08:45 WIB window
  intraday  — any market hour, ticker must be in lists with plan
  reconcile — 09:00–15:15 WIB window

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md §7.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

from tools._lib.current_trade import CurrentTrade, ListItem

TICKER_RE = re.compile(r"^[A-Z]{1,6}$")
WIB = _dt.timezone(_dt.timedelta(hours=7))

# Carina token max age (seconds). Token considered expired if older.
TOKEN_MAX_AGE_SEC = 3600


def _find(ct: CurrentTrade, ticker: str) -> Optional[ListItem]:
    for lst in (ct.lists.superlist, ct.lists.exitlist):
        for it in lst:
            if it.ticker == ticker:
                return it
    return None


def _wib_now(now: Optional[_dt.datetime] = None) -> _dt.datetime:
    if now is None:
        return _dt.datetime.now(WIB)
    if now.tzinfo is None:
        return now.replace(tzinfo=WIB)
    return now.astimezone(WIB)


def _in_window(now: _dt.datetime, start_h: int, start_m: int,
               end_h: int, end_m: int) -> bool:
    t = now.time()
    lo = _dt.time(start_h, start_m)
    hi = _dt.time(end_h, end_m)
    return lo <= t <= hi


def _plan_age_hours(plan_updated_at: str,
                    now: _dt.datetime) -> Optional[float]:
    if not plan_updated_at:
        return None
    try:
        dt = _dt.datetime.fromisoformat(plan_updated_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=WIB)
        return (now - dt).total_seconds() / 3600
    except Exception:
        return None


def check(
    ct: CurrentTrade,
    path: str,
    ticker: Optional[str] = None,
    now: Optional[_dt.datetime] = None,
    token_age_sec: Optional[float] = None,
) -> dict:
    """Return {"ok": True} or {"ok": False, "reason": str}.

    path ∈ {pre_open, intraday, reconcile}
    """
    ts = ct.trader_status
    if (ts.aggressiveness or "").lower() == "off":
        return {"ok": False, "reason": "aggressiveness=off (kill-switch)"}

    now_wib = _wib_now(now)

    # Token check (optional — pass None to skip)
    if token_age_sec is not None and token_age_sec > TOKEN_MAX_AGE_SEC:
        return {"ok": False, "reason": f"Carina token expired (age {token_age_sec:.0f}s)"}

    if path == "pre_open":
        if not _in_window(now_wib, 8, 0, 8, 45):
            return {"ok": False, "reason": f"pre_open outside 08:00–08:45 WIB ({now_wib.strftime('%H:%M')})"}
        return {"ok": True}

    if path == "reconcile":
        if not _in_window(now_wib, 9, 0, 15, 15):
            return {"ok": False, "reason": f"reconcile outside 09:00–15:15 WIB ({now_wib.strftime('%H:%M')})"}
        return {"ok": True}

    if path == "intraday":
        if ticker is None:
            return {"ok": False, "reason": "intraday path requires --ticker"}
        if not TICKER_RE.match(ticker):
            return {"ok": False, "reason": f"invalid ticker {ticker!r}"}
        item = _find(ct, ticker)
        if item is None:
            return {"ok": False, "reason": f"{ticker} not in superlist/exitlist"}
        if item.plan is None:
            return {"ok": False, "reason": f"{ticker} has no plan (L4 not run yet)"}
        age = _plan_age_hours(item.plan.updated_at, now_wib)
        if age is not None and age > 24:
            return {"ok": False, "reason": f"{ticker} plan stale ({age:.1f}h > 24h)"}
        return {"ok": True}

    return {"ok": False, "reason": f"unknown path: {path!r}"}
