# Execution — Synthesize All Layers → Place Real Orders

## When This Runs

- **08:30 WIB** (pre-market): review overnight L4 plans, place pre-open limit orders
- **On-demand**: when L3 monitoring flags Boss O alert level signal

## Load First

1. `skills/trader/execution.md` — entry/exit/sizing/safety rules
2. `skills/trader/CLAUDE.md` — SID rules, broker classification
3. Today's files:
   - `runtime/screening/YYYY-MM-DD.md` — L1/L2 regime + shortlist
   - `runtime/tradeplans/YYYY-MM-DD.md` — L4 plans with entry/stop/target
   - `runtime/monitoring/YYYY-MM-DD.md` — latest L3 signals (if market open)

---

## Step 1 — Portfolio Health Check

For each ticker in Airtable `Superlist` where Status = `Hold`:
```python
pos = api.get_position_detail(ticker)
cash = api.get_cash_info()
orders = api.get_orders(ticker)
```
- Verify qty vs Superlist record
- Check for stale unfilled orders → `api.cancel_order(order_id)` if placed >1 session ago
- Flag any hold where price < invalidation from L4 plan → candidate for exit

---

## Step 2 — Exit Decisions

For each flagged hold from Step 1, apply exit rules from `skills/trader/execution.md`.

If exit triggered:
1. Calculate sell shares (partial or full per exit rules)
2. Send Telegram via `python3 tools/trader/telegram_client.py order-placing --side SELL --ticker "{TICKER}" --shares "{shares}" --price "{price}" --reason "{thesis break / target hit / SID dist}"`
3. `api.place_sell_order(symbol, price, shares)`
4. Log to `runtime/orders/YYYY-MM-DD.jsonl`
5. Update Airtable `Superlist` Status → `Sold` (full exit) or update qty (partial)
6. Send Telegram confirmation via `python3 tools/trader/telegram_client.py order-confirmed --order-id "{order_id}" --side SELL --ticker "{TICKER}" --shares "{shares}" --price "{price}"`

---

## Step 3 — Entry Decisions

For each ticker in today's L4 plan (`runtime/tradeplans/YYYY-MM-DD.md`) with level = `superlist` or `alert`:

1. Check current price vs entry range — still valid?
2. Check cash: `api.get_cash_info()` → `trade_limit`
3. Apply all entry rules from `skills/trader/execution.md`
4. If all pass → calculate shares using sizing formula
5. Send Telegram via `python3 tools/trader/telegram_client.py order-placing --side BUY --ticker "{TICKER}" --shares "{shares}" --price "{price}" --stop "{stop}" --risk "{pct}%" --reason "{entry rationale}"`
6. `api.place_buy_order(symbol, price, shares)`
7. Log to `runtime/orders/YYYY-MM-DD.jsonl`
8. Update Airtable `Superlist` Status → `Hold`, add entry fields
9. Send Telegram confirmation via `python3 tools/trader/telegram_client.py order-confirmed --order-id "{order_id}" --side BUY --ticker "{TICKER}" --shares "{shares}" --price "{price}"`

---

## Step 4 — Output

Append to `runtime/orders/YYYY-MM-DD.jsonl`:
```json
{"ts": "...", "action": "BUY|SELL", "ticker": "...", "shares": 0, "price": 0, "order_id": "...", "reason": "..."}
```

Send Telegram summary via:
```bash
python3 tools/trader/telegram_client.py execution-summary \
  --timestamp "{date} {time} WIB" \
  --exits "{list or 'none'}" \
  --entries "{list or 'none'}" \
  --holds "{n}" \
  --cash "{remaining}"
```

Format: emoji header + bold title + short takeaway + structured `<pre>` block.

Do NOT post to Airtable beyond Superlist updates — scripts handle Insights.
