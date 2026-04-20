"""L0 mechanical data reshaping helpers.

Pure functions — no AI, no I/O, no side effects. Inputs are plain dicts from
MCP `carina_portfolio` + rows from `journal.load_previous_orders`. Output is
spec #1 dataclasses. The playbook orchestrates calls and feeds the assembled
TraderStatus draft to Opus for aggressiveness tier + per-holding details.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md.
"""
from __future__ import annotations

import datetime as _dt

from tools._lib.current_trade import Balance, Holding, PnL, TraderStatus


def balance_from_portfolio(carina_portfolio: dict) -> Balance:
    """Parse Carina `portfolio` response into Balance.

    Uses `summary.cash` for both cash and buying_power (IDX cash accounts have
    no margin — broker API does not expose a distinct buying_power field).
    """
    summary = carina_portfolio.get("summary", {})
    cash = float(summary.get("cash") or 0.0)
    return Balance(cash=cash, buying_power=cash)


def holdings_from_portfolio(carina_portfolio: dict) -> list[Holding]:
    """Parse Carina `portfolio.positions` into list[Holding].

    Position shape (from api.get_portfolio):
      {symbol, lots, shares, avg_price, latest_price, market_value, pl, gain_pct}

    `details` always starts empty; playbook fills via Opus.
    """
    out: list[Holding] = []
    for p in carina_portfolio.get("positions", []):
        out.append(
            Holding(
                ticker=str(p["symbol"]),
                lot=int(p["lots"]),
                avg_price=float(p["avg_price"]),
                current_price=float(p["latest_price"]),
                pnl_pct=float(p["gain_pct"]),
                details="",
            )
        )
    return out


def pnl_rollup_from_orders(
    journal_rows: list[dict],
    prior_pnl: PnL,
    today: _dt.date,
) -> PnL:
    """Compute realized MtD/YtD from local journal rows via FIFO pairing.

    Row shape (from `journal.load_previous_orders`):
      {ts, action ('BUY'|'SELL'), ticker, shares, price, order_id, ...}

    For each ticker we sort rows chronologically and maintain a FIFO queue of
    unmatched BUY lots. Each SELL consumes from the queue head to compute
    `realized = (sell_price - buy_price) * matched_shares`. Realized is
    attributed to MtD/YtD based on the SELL timestamp.

    If no SELL rows fall inside the month/year window, the corresponding field
    falls back to `prior_pnl.mtd` / `prior_pnl.ytd` verbatim (spec §8.4 — keeps
    prior value instead of zeroing). `realized_today` always returns 0 because
    L0 runs pre-market (today's fills come from L5 intraday).

    Limitation: BUYs that happened before the journal window are not in the
    queue, so SELLs matching those historical lots produce 0 realized for the
    unmatched portion. This self-corrects as the journal accumulates history.
    """
    mtd = 0.0
    ytd = 0.0
    mtd_had_row = False
    ytd_had_row = False

    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    by_ticker: dict[str, list[dict]] = {}
    for r in journal_rows:
        action = str(r.get("action", "")).upper()
        if action not in ("BUY", "SELL"):
            continue
        by_ticker.setdefault(str(r["ticker"]), []).append(r)

    for _ticker, rows in by_ticker.items():
        rows.sort(key=lambda r: str(r["ts"]))
        queue: list[list] = []  # list of [shares_remaining, buy_price]
        for r in rows:
            action = str(r.get("action", "")).upper()
            if action not in ("BUY", "SELL"):
                continue
            shares = int(r["shares"])
            price = float(r["price"])
            if action == "BUY":
                queue.append([shares, price])
                continue
            realized = 0.0
            remaining = shares
            while remaining > 0 and queue:
                lot_shares, lot_price = queue[0]
                matched = min(remaining, lot_shares)
                realized += (price - lot_price) * matched
                lot_shares -= matched
                remaining -= matched
                if lot_shares == 0:
                    queue.pop(0)
                else:
                    queue[0][0] = lot_shares
            sell_date = _dt.date.fromisoformat(str(r["ts"])[:10])
            if sell_date >= year_start:
                ytd += realized
                ytd_had_row = True
                if sell_date >= month_start:
                    mtd += realized
                    mtd_had_row = True

    return PnL(
        realized=0.0,
        unrealized=prior_pnl.unrealized,
        mtd=mtd if mtd_had_row else prior_pnl.mtd,
        ytd=ytd if ytd_had_row else prior_pnl.ytd,
    )


def _unrealized_from_portfolio(carina_portfolio: dict) -> float:
    """Read broker's own unrealized total from `summary.unrealised_pl`."""
    return float(carina_portfolio.get("summary", {}).get("unrealised_pl") or 0.0)


def assemble_trader_status_draft(
    carina_portfolio: dict,
    journal_rows: list[dict],
    prior_status: TraderStatus,
    today: _dt.date,
) -> TraderStatus:
    """Build a TraderStatus with mechanical fields filled (balance, pnl, holdings).

    Judgment fields (aggressiveness, holding.details) are left at spec-#1
    defaults for the Claude playbook to synthesize via Opus. L1-owned fields
    (regime, sectors, narratives) are carried from `prior_status` unchanged.
    """
    balance = balance_from_portfolio(carina_portfolio)
    holdings = holdings_from_portfolio(carina_portfolio)

    pnl = pnl_rollup_from_orders(journal_rows, prior_pnl=prior_status.pnl, today=today)
    pnl.unrealized = _unrealized_from_portfolio(carina_portfolio)

    return TraderStatus(
        regime=prior_status.regime,
        aggressiveness="",
        sectors=list(prior_status.sectors),
        narratives=list(prior_status.narratives),
        balance=balance,
        pnl=pnl,
        holdings=holdings,
    )
