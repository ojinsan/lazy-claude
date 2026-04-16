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

## Execution Trigger

L2 inline gate: 5/5 criteria + price in open entry window + DD < 5%. If met → invoke `skills/trader/execution.md` (`## Confidence Gate`). Otherwise → pass to L4.

## Output (Required)

1. **Shortlist**: 3–8 tickers, each with one-line reason
2. **Rejected names**: quick note on why each screened-out candidate was skipped
3. **Superlist updates**: promote strong names to Airtable `Superlist`
4. **Post to Airtable** `Insights` for any strong screening signal
5. **Daily-note append** — call `journal.append_daily_layer_section('2', summary)` with shortlist + top pick + reason

## Telegram Notify

Send `layer2` via `skills/trader/telegram-notify.md`.

Triggers: shortlist has ≥1 high-conviction name (≥4/5 criteria); or any name promoted to Superlist. Skip if empty.

## Skills To Load

- `skills/trader/technical-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/sid-tracker.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/airtable-trading.md`
