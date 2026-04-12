# Layer 3 — Stock Monitoring

Watch shortlisted names closely during market hours. Understand whale intent, not just price.

## What To Monitor

### Price & Volume
- Running trades: are real buyers/sellers stepping in?
- Volume surge vs price action — accumulation or distribution?
- Tape speed: slow grind up = controlled; spike with panic = retail-driven

### Orderbook (Bid/Offer Shape)
- Where is the nearest thick offer wall? Is it fake (retail blocker) or real resistance?
- Does the wall refresh, shrink, or disappear?
- Does bid step up per tick into the wall?
- Price acceptance above the wall after absorption = constructive

### Manipulation Signals
- `accumulation_setup`: thick offer wall + whale bids underneath → smart money accumulating while retail fears the wall
- `distribution_setup`: thick bid wall + whale offers behind it → whale distributing into retail attraction
- `shakeout_trap`: engineered price dip (wall appears, price drops) but whale bids hold → deliberate retail flush
- `wick_shakeout`: price dips >1.5% but whale bids remain → smart money held through the dip

### Wyckoff Phase
- Is the stock in accumulation, markup, distribution, or markdown?
- Any spring / test / sign of strength pattern?

## Tools

| Tool | How |
|------|-----|
| Orderbook + running trade | `tools/trader/runtime_monitoring.py` (cron every 10m → `intraday-10m.log`) |
| 30-min summary | `tools/trader/runtime_summary_30m.py` (cron every 30m → `summary-30m.log`) |
| Tick walls | `tools/trader/tick_walls.py` |
| Orderbook WS | `tools/trader/orderbook_ws.py` |
| Running trade | `tools/trader/running_trade_poller.py` |
| Wyckoff | `tools/trader/wyckoff.py` |

## Output (Required)

1. **Signal update**: per ticker — accumulating / distributing / noisy / wait
2. **Manipulation flag**: note any `accumulation_setup` or `shakeout_trap` explicitly
3. **Promotion**: move names to Layer 4 if golden setup appears
4. **Demotion**: remove names from watchlist if thesis breaks
5. **Post to Airtable** `Insights` for clean early-accumulation or manipulation-edge signals

## Skills To Load

- `skills/trader/orderbook-reading.md`
- `skills/trader/bid-offer-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/realtime-monitoring.md`
- `skills/trader/airtable-trading.md`
