# Layer 4 — Trade Plan

Connect all layers into a precise, actionable trade plan. Easy to follow, no ambiguity.

## Inputs

- **L0**: portfolio equity, DD, utilization, sector exposure, concentration flags (`vault/data/portfolio-state.json`)
- **L0 thesis actions**: `vault/data/thesis-actions.json` — if ticker is `exit-candidate`, skip; only exit plan is valid.
- **L0 kill-switch**: `journal.kill_switch_state()` — if active, no new entries.
- **L1**: market regime, sector view, aggression posture
- **Catalyst calendar**: `vault/data/catalyst-<today>.json` — check within 3 trading days. Either use as trigger or note "avoid entry pre-catalyst" explicitly in the plan.
- **L1 intraday**: `journal.get_intraday_posture()` — if set and posture < morning posture, apply the lower value.
- **L2**: shortlisted tickers with gate-cleared reasons
- **L3**: tape signal, manipulation detection, Wyckoff phase (if arrived from L3)
- Airtable `Superlist` and `Insights`: existing notes and history

L0 is a required input — not optional context. Position size, sector cap, and add/substitute decision all depend on it.

## Mode — Full Plan vs Sizing-Only

L4 runs in one of two modes depending on how you arrived here:

### Mode A — Full Trade Plan
**Arrives from**: L2 high-confidence path (all 3 gates passed, confidence HIGH).

Build the complete plan below. Use L0 data to determine position size, check sector exposure cap, and confirm substitute/add decision made in Gate 2.

### Mode B — Sizing-Only
**Arrives from**: L3 "Signal BUY NOW" decision.

Tape already defines entry price. Do not rebuild the full plan — that wastes a live window. Do only:
1. Confirm entry price from tape (current ask / best offer absorbing)
2. Set stop: last accumulation low or invalidation from existing thesis
3. Calculate position size using L0 equity + sizing formula (see `execution.md`)
4. Confirm portfolio room (sector cap, utilization) from L0 state
5. Advance directly to L5 Execution

Mode B output is a one-block summary, not the full format below.

---

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
