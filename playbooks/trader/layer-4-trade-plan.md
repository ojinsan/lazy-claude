# Layer 4 — Trade Plan

Connect all layers into a precise, actionable trade plan. Easy to follow, no ambiguity.

## Inputs

- Layer 1: market regime, sector view, aggression posture
- Layer 2: shortlisted tickers with reasons
- Layer 3: tape signal, manipulation detection, Wyckoff phase
- Airtable `Superlist` and `Insights`: existing notes and history

## Trade Plan Format (Per Ticker)

```
Ticker: XXXX
Thesis: [one sentence — why this stock, why now]
Catalyst: [what triggers the move]
Setup type: [accumulation / breakout / shakeout-recovery / swing]

Entry: Rp X,XXX – X,XXX (trigger: [what to see before buying])
Add zone: Rp X,XXX (only if: [condition])
Stop loss: Rp X,XXX ([% from entry], invalidation: [what breaks the thesis])
Target 1: Rp X,XXX ([%R], [timeline])
Target 2: Rp X,XXX ([%R], [condition to hold])
Exit rule: [time-based / price-based / thesis-break]

Position size: Rp XX,XXX,XXX ([X]% of capital)
Max risk: Rp XX,XXX,XXX ([X]% of capital)

Monitoring: [what to watch — wall behavior / volume / tape]
Invalidation signal: [one clear thing that says exit now]
```

## Sizing & Exit

Apply sizing formula + caps from `skills/trader/execution.md` (`## Sizing Formula`).
Apply exit rules from `skills/trader/execution.md` (`## Exit Rules`).
Risk-per-trade tier: 1% low conv | 2% med | 3% high (L3 signal + L1 narrative). Cap at L1 aggression posture.

## Execution Trigger

L4 inline gate: plan marked `urgent` + current price in entry zone + DD < 5%. If met → invoke `skills/trader/execution.md` (`## Confidence Gate`). Otherwise → queue for 08:30 L5.

## Output (Required)

Apply three output levels per plan:

| Level | When | Action |
|-------|------|--------|
| **local only** | Setup developing, not yet actionable | Write to tradeplans log only |
| **Airtable Superlist** | High conviction, entry logic clear | Post/update `Superlist` record |
| **Boss O alert** | Entry window opening, immediate action needed | Flag explicitly, send Telegram first |

1. **Trade plan**: one block per ticker in the format above
2. **Priority ranking**: which name to act on first today
3. **Superlist update**: post final plans to Airtable `Superlist` when warranted
4. **Daily-note append** — call `journal.append_daily_layer_section('4', summary)` with ticker + setup + entry zone for each finalized plan

## Telegram Notify

Send `layer4` via `skills/trader/telegram-notify.md` — one message per finalized plan, urgent plans send before Airtable post.

Trigger: every finalized plan. Skip resends unless entry/SL changes >1 tick.

## Skills To Load

- `skills/trader/trade-planning.md`
- `skills/trader/swing-trade-plan.md`
- `skills/trader/pro-orderbook-trade-plan.md`
- `skills/trader/risk-rules.md`
- `skills/trader/airtable-trading.md`
