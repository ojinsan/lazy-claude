# Layer 2 — Stock Screening

Filter the full universe down to a high-conviction shortlist.

## Input

- Layer 1 market regime, sector view, and narrative list
- Current watchlist from Airtable `Superlist`

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

## Output (Required)

1. **Shortlist**: 3–8 tickers, each with one-line reason
2. **Rejected names**: quick note on why each screened-out candidate was skipped
3. **Superlist updates**: promote strong names to Airtable `Superlist`
4. **Post to Airtable** `Insights` for any strong screening signal

## Skills To Load

- `skills/trader/technical-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/sid-tracker.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/airtable-trading.md`
