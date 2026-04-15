# Telegram Notify

Single source for every Telegram message the trader emits. All layers + execution call this skill instead of inlining bash.

## Tool

`tools/trader/telegram_client.py` — see `tools/manual/telegram.md` for env vars and dry-run usage.

Required env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (optional `TELEGRAM_MESSAGE_THREAD_ID`).

Use `--dry-run` to render locally without sending.

## Anti-Spam Rules

- One message per layer per session unless explicitly multi-event (L3, L4).
- Same signal on same ticker = no repeat in a session.
- L1: skip resend on rerun; L2: skip if shortlist empty; L3: only on signal change; L4: only on plan finalize or significant edit.

## Subcommand Reference

### `layer0` — L0 portfolio
```bash
python3 tools/trader/telegram_client.py layer0 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --equity "{equity}" \
  --mtd-return "{X}%" \
  --dd "{X}%" \
  --open-risk "{X}%" \
  --top-exposure "{TICKER}" \
  --action "{one-line action summary}"
```
Trigger: every scheduled 04:30 L0 run; urgent if DD > 5% or any hold breaches invalidation overnight.

### `layer1` — L1 global context
```bash
python3 tools/trader/telegram_client.py layer1 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --regime "{risk-on|cautious|risk-off}" \
  --posture "{N}/5" \
  --sectors "{themes, comma-separated}" \
  --key-risk "{one sentence or 'none'}"
```
Trigger: scheduled 05:00 run; or aggression posture ≤ 2; or regime flipped vs yesterday; or critical macro event.

### `layer2` — L2 screening
```bash
python3 tools/trader/telegram_client.py layer2 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --shortlist "{TICK1, TICK2, ...}" \
  --top-pick "{TICKER}" \
  --top-reason "{one-line reason}" \
  --watch "{borderline names}"
```
Trigger: ≥1 high-conviction name (≥4/5 criteria); or any name promoted to Superlist.

### `layer3` — L3 monitoring signal
```bash
python3 tools/trader/telegram_client.py layer3 \
  --timestamp "$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M WIB')" \
  --ticker "{TICKER}" \
  --signal "{accumulation_setup|shakeout_trap|wick_shakeout|distribution_setup|thesis_break}" \
  --note "{one-line description}" \
  --action "{watch|promote to L4|demote|exit}"
```
Trigger: new signal on shortlisted ticker; thesis break; promotion/demotion. NOT every 30-min tick.

### `layer4` — L4 trade plan
```bash
python3 tools/trader/telegram_client.py layer4 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --ticker "{TICKER}" --thesis "{one sentence}" \
  --entry-low "{X,XXX}" --entry-high "{X,XXX}" \
  --stop "{X,XXX}" --stop-pct "{X}%" \
  --target1 "{X,XXX}" --target1-pct "{X}%" \
  --size-amount "{XX,XXX,XXX}" --size-pct "{X}%" \
  --risk "{X}%" --trigger "{trigger description}"
# add --urgent for immediate-action plans
```
Trigger: every finalized plan. Urgent plans send before Airtable post.

### `intent` — pre-execution intent (L2/L3/L4 inline)
```bash
python3 tools/trader/telegram_client.py intent \
  --layer "{2|3|4}" \
  --ticker "{TICKER}" \
  --action "{BUY|SELL}" \
  --price "{X,XXX}" \
  --shares "{N}" \
  --reason "{one-line reason}"
```
Trigger: BEFORE inline execution from L2/L3/L4. Wait 60s after sending for Boss O cancel signal.

### `order-placing` — pre-order announce
```bash
python3 tools/trader/telegram_client.py order-placing \
  --side "{BUY|SELL}" --ticker "{TICKER}" \
  --shares "{N}" --price "{X,XXX}" \
  [--stop "{X,XXX}"] [--risk "{X}%"] [--reason "{...}"]
```
Trigger: immediately before `api.place_buy_order()` / `api.place_sell_order()` at L5.

### `order-confirmed` — broker accepted
```bash
python3 tools/trader/telegram_client.py order-confirmed \
  --order-id "{ID}" --side "{BUY|SELL}" --ticker "{TICKER}" \
  --shares "{N}" --price "{X,XXX}"
```

### `order-failed` — broker rejected
```bash
python3 tools/trader/telegram_client.py order-failed \
  --ticker "{TICKER}" --side "{BUY|SELL}" --error "{message}"
```

### `execution-summary` — session wrap
```bash
python3 tools/trader/telegram_client.py execution-summary \
  --timestamp "$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M WIB')" \
  --exits "{summary}" --entries "{summary}" \
  --holds "{summary}" --cash "{cash}"
```
Trigger: end of L5 session and EOD publish.
