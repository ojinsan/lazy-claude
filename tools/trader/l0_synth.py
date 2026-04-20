"""L0 mechanical data reshaping helpers.

Pure functions — no AI, no I/O, no side effects. Carina MCP responses
(plain dicts from tool calls) → spec #1 dataclasses. The playbook
orchestrates calls and feeds assembled TraderStatus draft to Opus for
aggressiveness tier + per-holding details synth.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md.
"""
from __future__ import annotations

import datetime as _dt

from tools._lib.current_trade import Balance, Holding, PnL


def balance_from_cash(carina_cash: dict) -> Balance:
    """Parse Carina cash_balance response into Balance dataclass.

    Expected keys: `cash` (float, IDR), `buying_power` (float, IDR).
    """
    return Balance(
        cash=float(carina_cash["cash"]),
        buying_power=float(carina_cash["buying_power"]),
    )


def holdings_from_positions(carina_positions: dict) -> list[Holding]:
    """Parse Carina position_detail response into list[Holding].

    Expected shape: `{"positions": [{ticker, lot, avg_price, current_price, pnl_pct, ...}, ...]}`.
    `details` always starts empty; playbook fills via Opus.
    """
    out: list[Holding] = []
    for p in carina_positions.get("positions", []):
        out.append(
            Holding(
                ticker=str(p["ticker"]),
                lot=int(p["lot"]),
                avg_price=float(p["avg_price"]),
                current_price=float(p["current_price"]),
                pnl_pct=float(p["pnl_pct"]),
                details="",
            )
        )
    return out


def pnl_rollup_from_orders(
    carina_orders: dict,
    prior_pnl: PnL,
    today: _dt.date,
) -> PnL:
    """Sum realized PnL across filled sell orders within month/year window.

    If the window is empty (Carina did not return orders spanning the period),
    fall back to `prior_pnl.mtd` / `prior_pnl.ytd` verbatim. `realized_today`
    is left at 0 (L0 runs pre-market; L5 fills during the day).

    Only filled orders with a truthy `filled_at` timestamp contribute. Cancelled
    or unfilled orders are ignored.
    """
    mtd = 0.0
    ytd = 0.0
    mtd_had_row = False
    ytd_had_row = False

    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    for o in carina_orders.get("orders", []):
        if o.get("status") != "filled":
            continue
        filled_at = o.get("filled_at")
        if not filled_at:
            continue
        # ISO8601 with offset — take the date portion only.
        filled_date = _dt.date.fromisoformat(filled_at[:10])
        realized = float(o.get("realized_pnl") or 0.0)

        if filled_date >= year_start:
            ytd += realized
            ytd_had_row = True
            if filled_date >= month_start:
                mtd += realized
                mtd_had_row = True

    return PnL(
        realized=0.0,
        unrealized=prior_pnl.unrealized,  # unrealized is set by holdings merge elsewhere
        mtd=mtd if mtd_had_row else prior_pnl.mtd,
        ytd=ytd if ytd_had_row else prior_pnl.ytd,
    )
