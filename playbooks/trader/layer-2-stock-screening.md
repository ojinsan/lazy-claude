# Layer 2 — Stock Screening

Filter the full universe down to a high-conviction shortlist.

## Input

- Layer 1 market regime, sector view, and narrative list
- Current watchlist from Airtable `Superlist`

## Portfolio Health (Run First)

Before screening new candidates, check existing holds:

For each ticker in Airtable `Superlist` where Status = `Hold`:
1. Re-run screening criteria — does it still pass ≥3/5?
2. Check SID direction — still accumulation or flipped to distribution?
3. Check broker flow — smart money still holding or exiting?

If hold fails ≥2 criteria → flag for exit review in L4.
If hold still passes → confirm thesis intact, carry forward.

## Screening Criteria (Apply In Order)

1. **Narrative fit** — does the stock match an active Layer 1 theme?
2. **Technical structure** — base formation, trend, near support, not extended
3. **Volume / liquidity** — adequate volume, no illiquid traps
4. **Broker / whale signal** — accumulation pattern in broker flow or SID
5. **Orderbook quality** — is there real bid support, or just noise?

## Tools

| Tool | How |
|------|-----|
| Stockbit screener | `tools/trader/stockbit_screener.py` (**placeholder** — API credentials pending) |
| Watchlist API | `tools/trader/api.py` → `get_watchlist()`, `get_price()`, `get_broker_summary()` |
| Runtime script | `tools/trader/runtime_layer2_screening.py` |
| Wyckoff lens | `skills/trader/wyckoff-lens.md` |
| SID tracker | `skills/trader/sid-tracker.md` |
| Psychology at levels | `tools/trader/psychology.py` — call when price near key support/resistance to judge who is absorbing vs fleeing |

## Output (Required)

1. **Shortlist**: 3–8 tickers, each with one-line reason
2. **Rejected names**: quick note on why each screened-out candidate was skipped
3. **Superlist updates**: promote strong names to Airtable `Superlist`
4. **Post to Airtable** `Insights` for any strong screening signal

## Telegram Notify (Scarlett)

Send once after shortlist is finalized. Skip if shortlist is empty or all names low-conviction.

**Trigger conditions (any one):**
- Shortlist has ≥1 high-conviction name (≥4/5 criteria aligned)
- Any name promoted to Superlist

**Send via Bash:**
```bash
curl -s -X POST "https://api.telegram.org/bot8781123769:AAHceKJY0FepJIqBCnHqd9DP3_BHro01Cgc/sendMessage" \
  -d "chat_id=1139649438" \
  --data-urlencode "text=L2 $(date +%Y-%m-%d) | Shortlist: {TICK1, TICK2, ...}
Top pick: {TICKER} — {one-line reason}
Watch: {any names borderline or to watch}"
```

**Anti-spam:** One message per L2 run. Do not resend if L2 re-run produces no new names.

## Skills To Load

- `skills/trader/technical-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/sid-tracker.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/airtable-trading.md`
