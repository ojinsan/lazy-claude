# Layer 0 — Portfolio (Hedge-Fund View)

Run BEFORE Layer 1 every morning. Start with portfolio health, concentration, and thesis quality before screening any new name.

## Inputs

- `tools/trader/api.py` → `get_portfolio()` for live positions and summary
- `tools/trader/api.py` → `get_cash_info()` for cash / trade balance / buying power
- Airtable `Superlist` where Status = `Hold` for current hold list and notes
- `vault/thesis/<TICKER>.md` for each active hold, if the thesis note already exists
- `vault/data/transactions.json` for recent closed-trade review, if available
- `vault/data/portfolio-state.json` for prior equity snapshots and high-water mark
- `runtime/orders/<prev-trading-day>.jsonl` for yesterday's execution log
- Latest EOD note or review from yesterday, if available

## Step 0 — Stale Thesis + Kill Switch Pre-Check

Before anything else:

1. `python tools/trader/journal.py stale` — any ticker returned MUST have a drift-check this session even if otherwise intact. Add to Step 4 forced list.
2. `python tools/trader/journal.py kill-switch` — if `active: true`, stop here. No new entries today. Write the reason to `vault/daily/<date>.md` and send Telegram `layer0` with kill-switch flag.

## Step 1 — Portfolio Growth & Health

Run `portfolio_health.py compute_portfolio_state()` → equity, MTD, drawdown, utilization, position count.

Apply DD posture rules from `skills/trader/portfolio-management.md`.

## Step 1.5 — Yesterday's Execution Review

Call `journal.load_previous_orders(days_back=1)` and read the result.

For each order row:
- **BUY filled**: is the position open in current portfolio? Does it match a current-day hold in Superlist?
- **SELL / CUT**: was this a planned exit (check yesterday's L4 plan) or a forced stop? Note whether the stop level held.
- **SYSTEM / BLOCKED**: what blocked execution? Is the blocker still present (e.g. auth expired)?

Write a 2–3 line summary into Step 6 self-review. Flag any mismatch between yesterday's order intent and today's Superlist state.

## Step 2 — Weighting & Concentration

Run `portfolio_health.py compute_concentration_flags()`. Apply per-position / per-sector / total-deployed limits from `portfolio-management.md`.

## Step 3 — Sector Exposure

Run `portfolio_health.py compute_exposure_breakdown()` → bucket map. Apply sector rules from `skills/trader/sector-exposure.md`. Flag orphan holds (no active L1 theme).

## Step 4 — Thesis Drift Per Hold

First: load forced list from Step 0 (stale tickers). Those must be checked even if price hasn't moved.

For each hold: invoke `skills/trader/thesis-drift-check.md` against `vault/thesis/<TICKER>.md`. Mark `intact | watch | reduce | exit-candidate | needs refresh`.

After marking: call `journal.set_thesis_action(ticker, action)` for every hold. This writes to `vault/data/thesis-actions.json` which L2 and L4 read to prevent same-day adds on exit-candidates.

## Step 5 — Aggregate Probability & Money Flow

Aggregate book-level (not per-name) view via `skills/trader/probability-measurement.md` + `skills/trader/money-flow-analysis.md`. Sizing implication: up / flat / down.

## Step 6 — Self-Evaluation

Compare yesterday's L0–L4 calls vs actual outcomes via `skills/trader/portfolio-self-review.md`. Write to `vault/journal/YYYY-MM-DD-review.md`. Log lessons via `tools/trader/journal.py`.

## Tools

| Tool | How |
|------|-----|
| Portfolio health | `tools/trader/portfolio_health.py` — equity, drawdown, concentration, sector exposure |
| Carina portfolio | `tools/trader/api.py` → `get_portfolio()`, `get_cash_info()`, `get_position_detail()` |
| Sector lookup | `tools/trader/api.py` → `get_emitten_info()` |
| Airtable hold list | `tools/trader/airtable_client.py` |
| Journal review | `tools/trader/journal.py` |

## Output (Required)

1. **Kill-switch status** — state first; if active, halt and document.
2. **Yesterday orders review** — from Step 1.5: mismatch flags, blocked-execution notes.
3. **Portfolio health card** — total equity, MTD, drawdown, cash utilization, top exposure.
4. **Action list** — rebalance / reduce / add-to / exit-candidate per hold (also written to `vault/data/thesis-actions.json` via `journal.set_thesis_action`).
5. **Sector exposure snapshot**.
6. **Self-review note** — `vault/journal/YYYY-MM-DD-review.md`.
7. **Portfolio state update** — `vault/data/portfolio-state.json`.
8. **PortfolioLog sync candidate** — prepare a clean summary for Airtable once that table exists.
9. **Daily-note append** — `journal.append_daily_layer_section('0', summary)` with equity + DD + kill-switch status + top action.

## Telegram Notify

Send `layer0` via `skills/trader/telegram-notify.md`.

Triggers: scheduled 04:30 run; urgent if DD > 5% from HWM or any hold flagged `exit-candidate`.

## Skills To Load

- `skills/trader/portfolio-management.md`
- `skills/trader/sector-exposure.md`
- `skills/trader/probability-measurement.md`
- `skills/trader/money-flow-analysis.md`
- `skills/trader/portfolio-self-review.md`
- `skills/trader/thesis-drift-check.md`
- `skills/trader/journal-review.md`
