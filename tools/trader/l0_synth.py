"""L0 mechanical data reshaping helpers.

Pure functions — no AI, no I/O, no side effects. Carina MCP responses
(plain dicts from tool calls) → spec #1 dataclasses. The playbook
orchestrates calls and feeds assembled TraderStatus draft to Opus for
aggressiveness tier + per-holding details synth.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md.
"""
from __future__ import annotations

from tools._lib.current_trade import Balance, Holding


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
