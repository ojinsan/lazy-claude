# Layer 5 — Execution

Synthesize all layers → place real orders. Default execution window.

## When This Runs

- **08:30 WIB** pre-market: review overnight L4 plans, place pre-open limit orders
- **On-demand**: when L3 monitoring flags Boss O alert
- **Inline from L2/L3/L4**: when Confidence Gate met (see `skills/trader/execution.md`)

## Inputs

- `runtime/screening/YYYY-MM-DD.md` — L1/L2 regime + shortlist
- `runtime/tradeplans/YYYY-MM-DD.md` — L4 plans with entry/stop/target
- `runtime/monitoring/YYYY-MM-DD.md` — latest L3 signals (if market open)

## Step 1 — Portfolio Health Check

For each Airtable `Superlist` Status = `Hold`: verify qty, cancel stale orders, flag holds breaching invalidation. Use `api.get_position_detail`, `get_cash_info`, `get_orders`, `cancel_order`.

## Step 2 — Exit Decisions

For each flagged hold from Step 1: apply exit rules from `skills/trader/execution.md` (`## Exit Rules`). Execute via Execution Protocol in same skill.

## Step 3 — Entry Decisions

Confluence gate <!-- M3.6 -->: require `confluence_score.score(ticker).score >= 60` before entry. Inline execution only if `score >= 80`.

For each ticker in today's L4 plan with level `superlist` or `alert`: apply entry rules from `skills/trader/execution.md` (`## Entry Rules` + sizing + protocol).

## Step 4 — Output

Append per-order to `runtime/orders/YYYY-MM-DD.jsonl`:
```json
{"ts": "...", "action": "BUY|SELL", "ticker": "...", "shares": 0, "price": 0, "order_id": "...", "reason": "..."}
```

Send `execution-summary` via `skills/trader/telegram-notify.md` at session end.

After each order placed or cut: call `journal.append_daily_layer_section('5', summary)` with side + ticker + shares + price + order_id so the daily timeline captures the fill.

Do NOT post to Airtable beyond Superlist updates — scripts handle Insights.

## Skills To Load

- `skills/trader/execution.md`
- `skills/trader/telegram-notify.md`
- `skills/trader/airtable-trading.md`
- `skills/trader/risk-rules.md`
