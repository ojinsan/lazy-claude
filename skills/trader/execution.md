# Execution Skill

## What This Is

Final layer — turns analysis into real orders via Carina (Stockbit broker).
Uses `api.py`: `place_buy_order`, `place_sell_order`, `cancel_order`, `amend_orders`, `get_cash_info`, `get_position_detail`, `get_orders`.

**These are REAL orders. No dry-run.**

---

## Entry Rules (all must pass)

1. L4 trade plan exists for the ticker today (`runtime/tradeplans/YYYY-MM-DD.md`)
2. Current price is within entry range from L4 plan (±1 tick tolerance)
3. At least 3/5 signals aligned (narrative + structure + broker + SID + orderbook)
4. Market regime posture ≥ 2 (not risk-off)
5. No conflicting open order for the same ticker already exists

If any fails → skip, log reason, do NOT place.

---

## Exit Rules (any triggers exit)

1. Price closed below L4 invalidation level
2. SID confirmed distribution (>+5%) AND smart money net selling confirmed in broker flow
3. `distribution_setup` signal in L3 for a held name
4. Time-based: thesis hasn't played in X market days (from L4 plan)
5. Target 1 hit → reduce 50%, trail remainder

---

## Sizing Formula

```
capital_at_risk = total_capital × risk_pct
risk_pct = 1% (low conv) | 2% (med) | 3% (high conv, L3 signal confirmed)

shares_raw = capital_at_risk / (entry_price - stop_price)
lots = floor(shares_raw / 100)          # 1 lot = 100 shares
shares = lots × 100

position_value = shares × entry_price
max_position = total_capital × 0.20     # hard cap 20% per name

if position_value > max_position:
    shares = floor(max_position / entry_price / 100) * 100
```

Get `total_capital` from `api.get_cash_info()` → `trade_limit` field.

---

## Execution Protocol

**Before placing:**
1. Call `get_cash_info()` — verify sufficient balance
2. Call `get_orders()` — verify no duplicate open order for ticker
3. Calculate shares using sizing formula above
4. Send Telegram via `tools/trader/telegram_client.py order-placing` using the matching BUY/SELL template. Include ticker, shares, price, and any stop/risk/reason fields available.

**Place order:**
```python
api.place_buy_order(symbol, price=entry_price, shares=shares)
# or
api.place_sell_order(symbol, price=exit_price, shares=shares)
```

**After placing:**
1. Log order_id to `runtime/orders/YYYY-MM-DD.jsonl`
2. Update Airtable `Superlist` — set Status to `Hold` (buy) or `Sold` (sell)
3. Send Telegram via `tools/trader/telegram_client.py order-confirmed` with order_id, ticker, side, shares, and price

**On error:**
- Log error, send Telegram via `tools/trader/telegram_client.py order-failed --ticker "{TICKER}" --side "{BUY/SELL}" --error "{error}"`
- Do NOT retry automatically

---

## Portfolio Health Check

Run before any new entry:
1. `get_position_detail(ticker)` for each hold — verify qty matches Superlist
2. Check unrealized P&L: if any hold is >-5% from avg cost AND thesis broken → flag for exit
3. Check open orders: stale orders (placed >1 session ago, unfilled) → cancel via `cancel_order()`

---

## Hard Safety Rules

- Never place order if `trade_limit` from `get_cash_info()` < position_value × 1.1
- Never exit >50% of a hold in one order without Boss O alert first
- Never chase: if price moved >2% above entry range → skip, log "missed entry"
- Max 2 new entries per session (posture 2) | 3 entries (posture 3+)
- Always send Telegram BEFORE placing, not only after
- Telegram sender requires env vars `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
