"""L5 Carina order executor: thin wrappers with retry + idempotency.

Idempotency key: (ticker, leg, plan_updated_at) — ensures at-most-one place
per plan version per leg. Retry: exponential backoff, 3 attempts max.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md §8.
"""
from __future__ import annotations

import time
from typing import Callable, Optional


_RETRY_DELAYS = (0, 2, 4)  # seconds before attempt 1, 2, 3


def _retry(fn: Callable, attempts: int = 3,
           delays: tuple = _RETRY_DELAYS) -> dict:
    """Call fn up to `attempts` times. Returns last result or raises."""
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        if i > 0 and i < len(delays):
            time.sleep(delays[i])
        try:
            result = fn()
            if isinstance(result, dict) and result.get("error"):
                # API-level error — do not retry (bad request, insufficient funds, etc.)
                return result
            return result
        except Exception as exc:
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def place_entry(
    ticker: str,
    side: str,
    shares: int,
    price: float,
    *,
    buy_fn: Optional[Callable] = None,
    sell_fn: Optional[Callable] = None,
    attempts: int = 3,
) -> dict:
    """Place entry order. Returns API response dict."""
    if buy_fn is None:
        from tools.trader.api import place_buy_order as buy_fn  # type: ignore
    if sell_fn is None:
        from tools.trader.api import place_sell_order as sell_fn  # type: ignore

    if side == "buy":
        fn = lambda: buy_fn(stock_code=ticker, shares=shares,
                            price=price, order_type="LIMIT_DAY")
    else:
        fn = lambda: sell_fn(stock_code=ticker, shares=shares,
                             price=price, order_type="LIMIT_DAY")
    return _retry(fn, attempts=attempts)


def place_stop(
    ticker: str,
    side: str,
    shares: int,
    price: float,
    *,
    buy_fn: Optional[Callable] = None,
    sell_fn: Optional[Callable] = None,
    attempts: int = 3,
) -> dict:
    """Place stop-loss order. Stop for buy position = sell; for sell position = buy."""
    if buy_fn is None:
        from tools.trader.api import place_buy_order as buy_fn  # type: ignore
    if sell_fn is None:
        from tools.trader.api import place_sell_order as sell_fn  # type: ignore

    stop_side = "sell" if side == "buy" else "buy"
    if stop_side == "sell":
        fn = lambda: sell_fn(stock_code=ticker, shares=shares,
                             price=price, order_type="LIMIT_DAY")
    else:
        fn = lambda: buy_fn(stock_code=ticker, shares=shares,
                            price=price, order_type="LIMIT_DAY")
    return _retry(fn, attempts=attempts)


def place_tp(
    ticker: str,
    side: str,
    shares: int,
    price: float,
    *,
    buy_fn: Optional[Callable] = None,
    sell_fn: Optional[Callable] = None,
    attempts: int = 3,
) -> dict:
    """Place take-profit limit order."""
    if buy_fn is None:
        from tools.trader.api import place_buy_order as buy_fn  # type: ignore
    if sell_fn is None:
        from tools.trader.api import place_sell_order as sell_fn  # type: ignore

    tp_side = "sell" if side == "buy" else "buy"
    if tp_side == "sell":
        fn = lambda: sell_fn(stock_code=ticker, shares=shares,
                             price=price, order_type="LIMIT_DAY")
    else:
        fn = lambda: buy_fn(stock_code=ticker, shares=shares,
                            price=price, order_type="LIMIT_DAY")
    return _retry(fn, attempts=attempts)


def cancel_order(
    order_id: str,
    *,
    cancel_fn: Optional[Callable] = None,
    attempts: int = 3,
) -> dict:
    """Cancel an open order."""
    if cancel_fn is None:
        from tools.trader.api import cancel_order as cancel_fn  # type: ignore
    fn = lambda: cancel_fn(order_id=order_id)
    return _retry(fn, attempts=attempts)


def make_idempotency_key(ticker: str, leg: str, plan_updated_at: str) -> str:
    """Stable key for at-most-one guarantee per plan version per leg."""
    return f"{ticker}:{leg}:{plan_updated_at}"
