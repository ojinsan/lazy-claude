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

## Execution Trigger (Integrated)

Inline execution allowed if ALL of:
- Plan marked `urgent` (entry window is live now, not just anticipated)
- Current price is within the entry zone defined in this plan
- Portfolio DD < 5% from HWM

**If all conditions met:**
1. Send Telegram `intent`: `python3 tools/trader/telegram_client.py intent --layer 4 --ticker {T} --action BUY --price {P} --shares {N} --reason "{thesis one-liner}"`
2. Wait 60 seconds
3. Place order via `api.place_buy_order(ticker, price, qty)`
4. Send `order-confirmed` or `order-failed`

Otherwise: plan is queued for the scheduled L5 window at 08:30 WIB.

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
python3 tools/trader/telegram_client.py layer4 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --ticker "{TICKER}" \
  --thesis "{one sentence}" \
  --entry-low "{X,XXX}" \
  --entry-high "{X,XXX}" \
  --stop "{X,XXX}" \
  --stop-pct "{X}%" \
  --target1 "{X,XXX}" \
  --target1-pct "{X}%" \
  --size-amount "{XX,XXX,XXX}" \
  --size-pct "{X}%" \
  --risk "{X}%" \
  --trigger "{what to see before buying}"
# add --urgent for immediate-action plans
```

**Format:** emoji header + bold title + short takeaway + structured `<pre>` block.

**Required env:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**Anti-spam:** One message per trade plan. Do not resend on plan edits unless entry/SL changes significantly (>1 tick).

## Skills To Load

- `skills/trader/trade-planning.md`
- `skills/trader/swing-trade-plan.md`
- `skills/trader/pro-orderbook-trade-plan.md`
- `skills/trader/risk-rules.md`
- `skills/trader/airtable-trading.md`
