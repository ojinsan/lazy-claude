# Layer 0 — Portfolio (Hedge-Fund View)

Run BEFORE Layer 1 every morning. Start with portfolio health, concentration, and thesis quality before screening any new name.

## Inputs

- `tools/trader/api.py` → `get_portfolio()` for live positions and summary
- `tools/trader/api.py` → `get_cash_info()` for cash / trade balance / buying power
- Airtable `Superlist` where Status = `Hold` for current hold list and notes
- `vault/thesis/<TICKER>.md` for each active hold, if the thesis note already exists
- `vault/data/transactions.json` for recent closed-trade review, if available
- `vault/data/portfolio-state.json` for prior equity snapshots and high-water mark
- Latest EOD note or review from yesterday, if available

## Step 1 — Portfolio Growth & Health

Run `portfolio_health.py compute_portfolio_state()` → equity, MTD, drawdown, utilization, position count.

Apply DD posture rules from `skills/trader/portfolio-management.md`.

## Step 2 — Weighting & Concentration

Run `portfolio_health.py compute_concentration_flags()`. Apply per-position / per-sector / total-deployed limits from `portfolio-management.md`.

## Step 3 — Sector Exposure

Run `portfolio_health.py compute_exposure_breakdown()` → bucket map. Apply sector rules from `skills/trader/sector-exposure.md`. Flag orphan holds (no active L1 theme).

## Step 4 — Thesis Drift Per Hold

For each hold: invoke `skills/trader/thesis-drift-check.md` against `vault/thesis/<TICKER>.md`. Mark `intact | watch | reduce | exit-candidate | needs refresh`.

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

1. **Portfolio health card** — total equity, MTD, drawdown, cash utilization, top exposure
2. **Action list** — rebalance / reduce / add-to / exit-candidate per hold
3. **Sector exposure snapshot**
4. **Self-review note** — `vault/journal/YYYY-MM-DD-review.md`
5. **Portfolio state update** — `vault/data/portfolio-state.json`
6. **PortfolioLog sync candidate** — prepare a clean summary for Airtable once that table exists
7. **Daily-note append** — call `journal.append_daily_layer_section('0', summary)` with a compact one-liner (equity + DD + top action) so today's `vault/daily/YYYY-MM-DD.md` has a running timeline

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
