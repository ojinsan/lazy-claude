# SID Tracker

## Purpose

Determine whether a stock is being accumulated (float draining) or distributed (shares spreading to retail).
SID is a SLOW signal — changes over days/weeks, not per tick. Use it to confirm operator intent.

## Critical Rule

```
SID DECREASING → fewer shareholders → shares concentrating → ACCUMULATION → BULLISH
SID INCREASING → more shareholders → shares spreading → DISTRIBUTION → BEARISH
```

This is the opposite of what feels intuitive. Rising SID does NOT mean "more interest."
It means retail is absorbing shares from stronger hands.

## Thresholds (SID % Change)

| Change | Signal | Meaning |
|--------|--------|---------|
| -10%+ | Strong accumulation | Float being drained hard, operator aggressive |
| -3% to -10% | Accumulation | Moderate consolidation into stronger hands |
| -3% to +3% | Stable | No meaningful change |
| +3% to +15% | Distribution | Retail starting to absorb shares |
| +15%+ | Heavy distribution | Retail FOMO phase — danger zone |

## Cross-Check With Broker Flow

| SID | Broker flow | Combined signal |
|-----|------------|----------------|
| Decreasing | Smart money accumulating | Strongest bullish — operator draining float |
| Decreasing | Mixed | Likely accumulation, some noise |
| Increasing | Retail dominating | Distribution confirmed — avoid |
| Increasing | Smart money selling | Clear distribution trap — exit or avoid |
| Increasing | Smart money buying | Conflicted — wait, something is off |

## Output

State:
- SID direction and approximate % change
- Accumulation / stable / distribution verdict
- Whether broker flow confirms or conflicts
- Overall signal: bullish / neutral / bearish

## Tool

`tools/trader/sid_tracker.py` → `api.get_stockbit_sid_count(ticker)` returns `current_sid`, `previous_sid`, `change`

Calculate change %: `(current_sid - previous_sid) / previous_sid * 100`
