"""L5 pure helpers: validators, payload builders, reconcile decision tree, formatters.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from tools._lib.current_trade import ExecutionState, FillEvent, TradePlan


# ── Validators ─────────────────────────────────────────────────────────────

def validate_plan_for_execute(plan: TradePlan, side: str) -> Optional[str]:
    """Return error string if plan is not executable, else None."""
    if plan.lots <= 0:
        return f"invalid lots: {plan.lots}"
    if plan.entry <= 0:
        return f"invalid entry price: {plan.entry}"
    if plan.stop <= 0:
        return f"invalid stop price: {plan.stop}"
    if plan.tp1 <= 0:
        return f"invalid tp1 price: {plan.tp1}"
    if side == "buy" and plan.stop >= plan.entry:
        return f"buy stop {plan.stop} >= entry {plan.entry}"
    if side == "sell" and plan.stop <= plan.entry:
        return f"sell stop {plan.stop} <= entry {plan.entry}"
    return None


def check_price_drift(plan_price: float, live_price: float,
                      pct: float = 0.05) -> bool:
    """Return True if drift exceeds threshold (circuit breaker)."""
    if plan_price <= 0:
        return True
    drift = abs(live_price - plan_price) / plan_price
    return drift > pct


def check_cash_sufficient(cash: float, lots: int, entry: float,
                           fee_pct: float = 0.002) -> bool:
    """Return True if cash covers notional + fee buffer."""
    notional = lots * 100 * entry
    required = notional * (1 + fee_pct)
    return cash >= required


def check_holdings_sufficient(holdings_lot: int, plan_lots: int) -> bool:
    """Return True if enough lots held for sell."""
    return holdings_lot >= plan_lots


# ── Payload builders ───────────────────────────────────────────────────────

def build_entry_payload(ticker: str, plan: TradePlan,
                        side: str) -> dict:
    return {
        "stock_code": ticker,
        "shares": plan.lots * 100,
        "price": plan.entry,
        "order_type": "LIMIT_DAY",
        "side": side,
    }


def build_stop_payload(ticker: str, plan: TradePlan,
                       side: str) -> dict:
    stop_side = "sell" if side == "buy" else "buy"
    return {
        "stock_code": ticker,
        "shares": plan.lots * 100,
        "price": plan.stop,
        "order_type": "LIMIT_DAY",
        "side": stop_side,
    }


def build_tp_payload(ticker: str, plan: TradePlan,
                     side: str, tp_key: str = "tp1") -> dict:
    tp_price = plan.tp1 if tp_key == "tp1" else (plan.tp2 or plan.tp1)
    tp_side = "sell" if side == "buy" else "buy"
    return {
        "stock_code": ticker,
        "shares": plan.lots * 100,
        "price": tp_price,
        "order_type": "LIMIT_DAY",
        "side": tp_side,
    }


# ── Reconcile decision tree ────────────────────────────────────────────────

_FILLED_STATUSES = {"filled", "done", "complete"}
_PARTIAL_STATUSES = {"partial", "partial_fill"}
_CANCELLED_STATUSES = {"cancelled", "canceled", "expired"}
_REJECTED_STATUSES = {"rejected", "failed", "error"}


def classify_order_state(order: dict) -> str:
    """Map Carina order status → internal state.

    Returns: filled | partial | open | cancelled | failed
    """
    status = str(order.get("status", "")).lower()
    if status in _FILLED_STATUSES:
        return "filled"
    if status in _PARTIAL_STATUSES:
        return "partial"
    if status in _CANCELLED_STATUSES:
        return "cancelled"
    if status in _REJECTED_STATUSES:
        return "failed"
    return "open"


def is_order_stale(order: dict, stale_hours: float = 3.0,
                   now: Optional[_dt.datetime] = None) -> bool:
    """Return True if open order older than stale_hours."""
    state = classify_order_state(order)
    if state != "open":
        return False
    created_str = order.get("created_at", "")
    if not created_str:
        return False
    try:
        created = _dt.datetime.fromisoformat(created_str)
        if now is None:
            tz = _dt.timezone(_dt.timedelta(hours=7))
            now = _dt.datetime.now(tz)
        if created.tzinfo is None:
            tz = _dt.timezone(_dt.timedelta(hours=7))
            created = created.replace(tzinfo=tz)
        age_hours = (now - created).total_seconds() / 3600
        return age_hours > stale_hours
    except (ValueError, TypeError):
        return False


def append_fill(execution: ExecutionState, order: dict,
                leg: str) -> ExecutionState:
    """Append fill from order dict to execution.fills. Returns same object."""
    filled_shares = int(order.get("filled_shares", 0))
    if filled_shares <= 0:
        return execution
    lot = filled_shares // 100
    fill = FillEvent(
        ts=order.get("updated_at", ""),
        lot=lot,
        price=float(order.get("avg_fill_price", order.get("price", 0))),
        order_id=str(order.get("order_id", "")),
        leg=leg,
    )
    execution.fills.append(fill)
    return execution


# ── Telegram event formatters ──────────────────────────────────────────────

def fmt_place_event(ticker: str, side: str, lots: int, price: float,
                    order_id: str) -> str:
    return f"[L5 place] {ticker} {side} {lots}lot @ {price:.0f} (order {order_id})"


def fmt_fill_event(ticker: str, lots: int, price: float,
                   stop: float, tp1: float) -> str:
    return (f"[L5 fill]  {ticker} entry {lots}lot @ {price:.0f}"
            f" → placing stop@{stop:.0f} + TP1@{tp1:.0f}")


def fmt_error_event(ticker: str, reason: str,
                    cash: Optional[float] = None,
                    notional: Optional[float] = None) -> str:
    detail = f": {reason}"
    if cash is not None and notional is not None:
        detail += f" — BP {cash/1e6:.1f}M < notional {notional/1e6:.2f}M"
    return f"[L5 error] {ticker} place failed{detail}"


def fmt_stale_event(ticker: str, age_hours: float) -> str:
    h = int(age_hours)
    return f"[L5 stale] {ticker} entry open {h}h, no fill; cancel? (reconcile)"


def fmt_circuit_breaker_event(ticker: str, plan_price: float,
                               live_price: float) -> str:
    drift_pct = abs(live_price - plan_price) / plan_price * 100
    return (f"[L5 abort] {ticker} price drift {drift_pct:.1f}%"
            f" (plan {plan_price:.0f} vs live {live_price:.0f}) — skip")


# ── Daily note block ───────────────────────────────────────────────────────

def fmt_daily_note_block(date: str, events: list[str]) -> str:
    lines = [f"## L5 Execution — {date}"]
    if not events:
        lines.append("No L5 activity.")
    else:
        lines.extend(events)
    return "\n".join(lines)
