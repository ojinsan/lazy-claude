"""L5 intraday fire — CLI entrypoint.

Usage:
    python -m tools.trader.l5_run --ticker ADMR

Called by L4 Mode B via Popen when BUY-NOW detected.
Pure Python — no AI, no playbook.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md §4.2.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import sys

WIB = _dt.timezone(_dt.timedelta(hours=7))


def _is_market_hours(now: _dt.datetime) -> bool:
    t = now.time()
    return _dt.time(9, 0) <= t <= _dt.time(15, 30)


def run(ticker: str, *, dry_run: bool = False) -> int:
    """Place intraday entry for ticker. Returns exit code (0=ok, 1=skip/abort)."""
    from tools._lib import current_trade as ct_mod
    from tools.trader.l5_healthcheck import check as hc_check
    from tools.trader.l5_dim_gather import gather_cash_balance, gather_orders
    from tools.trader.l5_synth import (
        validate_plan_for_execute, check_price_drift,
        check_cash_sufficient, check_holdings_sufficient,
        fmt_place_event, fmt_error_event, fmt_circuit_breaker_event,
    )
    from tools.trader.l5_executor import place_entry
    try:
        from tools.trader.telegram_client import send_message as _tg
    except Exception:
        _tg = None

    def tg(msg: str) -> None:
        if _tg and not dry_run:
            try:
                _tg(msg)
            except Exception:
                pass
        else:
            print(msg)

    now = _dt.datetime.now(WIB)
    if not _is_market_hours(now):
        print(f"[l5_run] outside market hours ({now.strftime('%H:%M')}) — exit 0")
        return 0

    ct = ct_mod.load()

    hc = hc_check(ct, "intraday", ticker=ticker, now=now)
    if not hc["ok"]:
        print(f"[l5_run] healthcheck abort: {hc['reason']}")
        ct_mod.save(ct, "l5", "skipped", note=hc["reason"])
        return 1

    # Find item
    item = None
    for lst in (ct.lists.superlist, ct.lists.exitlist):
        for it in lst:
            if it.ticker == ticker:
                item = it
                break
        if item:
            break

    if item is None or item.plan is None:
        print(f"[l5_run] {ticker} not found or no plan")
        return 1

    # Idempotency guard
    ex = item.execution
    if ex is not None and ex.status in ("placed", "partial", "filled"):
        print(f"[l5_run] {ticker} already {ex.status} — skip (idempotent)")
        return 0

    plan = item.plan
    side = "sell" if (item.current_plan and item.current_plan.mode == "sell_at_price") else "buy"

    # Validate plan
    err = validate_plan_for_execute(plan, side)
    if err:
        msg = fmt_error_event(ticker, err)
        tg(msg)
        ct_mod.save(ct, "l5", "error", note=err)
        return 1

    # Cash / holdings gate
    if side == "buy":
        cash = gather_cash_balance()
        if cash is None or not check_cash_sufficient(cash, plan.lots, plan.entry):
            notional = plan.lots * 100 * plan.entry
            msg = fmt_error_event(ticker, "insufficient_funds",
                                  cash=cash or 0, notional=notional)
            tg(msg)
            ct_mod.save(ct, "l5", "skipped", note="cash_insufficient")
            return 1
    else:
        holdings_lot = 0
        for h in ct.trader_status.holdings:
            if h.ticker == ticker:
                holdings_lot = h.lot
                break
        if not check_holdings_sufficient(holdings_lot, plan.lots):
            msg = fmt_error_event(ticker, f"sell_blockade: hold {holdings_lot}lot < plan {plan.lots}lot")
            tg(msg)
            ct_mod.save(ct, "l5", "skipped", note="sell_blockade")
            return 1

    # Use plan.entry for intraday (best_offer fetch deferred to live integration)
    entry_price = plan.entry

    if dry_run:
        print(f"[l5_run DRY-RUN] would place {side} {plan.lots}lot {ticker} @ {entry_price}")
        return 0

    resp = place_entry(ticker, side, plan.lots * 100, entry_price)
    if resp.get("error"):
        msg = fmt_error_event(ticker, resp["error"])
        tg(msg)
        ct_mod.save(ct, "l5", "error", note=resp["error"])
        return 1

    order_id = resp.get("order_id", "unknown")
    now_iso = now.replace(microsecond=0).isoformat()
    from tools._lib.current_trade import ExecutionState
    item.execution = ExecutionState(
        status="placed",
        path="intraday",
        entry_order_id=order_id,
        last_check=now_iso,
    )
    tg(fmt_place_event(ticker, side, plan.lots, entry_price, order_id))
    ct_mod.save(ct, "l5", "ok", note=f"intraday:{ticker}:{order_id}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="L5 intraday fire")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.exit(run(args.ticker, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
