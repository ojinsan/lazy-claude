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

## Sizing Rules

- Max single position: 20% of capital
- Max total exposure: 80% of capital
- Risk per trade: 1–3% of capital (match to aggression posture from Layer 1)
- Higher conviction (L3 manipulation signal + L1 narrative fit): allow up to 3%
- Lower conviction (only L2 screen, no L3 confirmation): cap at 1%

## Exit Discipline

- Time-based: if thesis doesn't play in [X] market days, cut
- Price-based: hit T1 → reduce 50%, trail the rest
- Thesis-break: exit same session, no holding hoping

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

## Telegram Notify (Scarlett)

Send one message per final trade plan. This is the most important notification layer.

**Trigger conditions:**
- Always send when a trade plan is finalized
- For urgent/immediate-action plans: send first before posting to Airtable

**Send via Bash (one message per ticker):**
```bash
curl -s -X POST "https://api.telegram.org/bot8781123769:AAHceKJY0FepJIqBCnHqd9DP3_BHro01Cgc/sendMessage" \
  -d "chat_id=1139649438" \
  --data-urlencode "text=L4 TRADE PLAN $(date +%Y-%m-%d) | {TICKER}
Thesis: {one sentence}
Entry: Rp {X,XXX}–{X,XXX} | SL: Rp {X,XXX} ({X}%) | T1: Rp {X,XXX} ({X}%)
Size: Rp {XX,XXX,XXX} ({X}% capital) | Risk: {X}%
Trigger: {what to see before buying}"
```

**Anti-spam:** One message per trade plan. Do not resend on plan edits unless entry/SL changes significantly (>1 tick).

## Skills To Load

- `skills/trader/trade-planning.md`
- `skills/trader/swing-trade-plan.md`
- `skills/trader/pro-orderbook-trade-plan.md`
- `skills/trader/risk-rules.md`
- `skills/trader/airtable-trading.md`
