"""L5 Carina data gatherers: cash, orders, position detail.

All functions graceful-degrade — exceptions captured, None or empty returned.
Callers decide whether missing data is fatal.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md.
"""
from __future__ import annotations

from typing import Callable, Optional


def gather_cash_balance(
    *,
    cash_balance_fn: Optional[Callable] = None,
) -> Optional[float]:
    """Return buying power as float IDR, or None on failure."""
    if cash_balance_fn is None:
        try:
            from tools.trader.api import get_cash_balance as cash_balance_fn  # type: ignore
        except Exception:
            return None
    try:
        result = cash_balance_fn()
        if isinstance(result, dict):
            return float(result.get("buying_power") or result.get("cash_balance") or 0)
        return float(result)
    except Exception:
        return None


def gather_orders(
    ticker: str,
    *,
    orders_fn: Optional[Callable] = None,
) -> list[dict]:
    """Return open orders for ticker, empty list on failure."""
    if orders_fn is None:
        try:
            from tools.trader.api import get_orders as orders_fn  # type: ignore
        except Exception:
            return []
    try:
        result = orders_fn(stock_code=ticker)
        if isinstance(result, list):
            return result
        return []
    except Exception:
        return []


def gather_position_detail(
    ticker: str,
    *,
    position_fn: Optional[Callable] = None,
) -> Optional[dict]:
    """Return position dict for ticker, None if not held or on failure."""
    if position_fn is None:
        try:
            from tools.trader.api import get_position_detail as position_fn  # type: ignore
        except Exception:
            return None
    try:
        result = position_fn(ticker)
        if isinstance(result, dict) and result:
            return result
        return None
    except Exception:
        return None
