# L4 — Trade Plan (Mode A batch / Mode B single-ticker)

Entry: `/trade:tradeplan [TICKER]`.

- **No arg → Mode A batch** — run post-L2 (CRON ~05:30 WIB Mon–Fri, spec #8). Loops `lists.{superlist,exitlist}` where `current_plan.mode ∈ {buy_at_price, sell_at_price}` and `plan is None`.
- **Ticker arg → Mode B (if L3 BUY-NOW recent) OR Mode A single re-plan** — L3 BUY-NOW async-popens `claude -p /trade:tradeplan {t}` from within its 10m cycle.

L4 writes per-ticker `lists.{superlist,exitlist}[i].{current_plan.price, details, plan}` + `layer_runs['l4']`. Preserves all other L0/L1/L2/L3 fields. Does NOT place orders (L5).

Spec: `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md`.

## Step 1 — Load prior state + parse arg

```python
import sys
from datetime import datetime, timezone, timedelta
from tools._lib import current_trade as ct
from tools._lib import daily_note
from tools.trader import l4_healthcheck, l4_dim_gather, l4_synth, telegram_client, claude_model

WIB = timezone(timedelta(hours=7))
now = datetime.now(WIB)
now_iso = now.replace(microsecond=0).isoformat()
today = now.date().isoformat()

ct_prior = ct.load()
ts = ct_prior.trader_status
bp = ts.balance.buying_power

args = [a for a in sys.argv[1:] if not a.startswith("-")]
ticker_arg = args[0].upper() if args else None
```

## Step 2 — Mode detection

```python
from tools.trader import l3_buy_now_ledger

def _detect_mode(ticker, ct_prior, now):
    if ticker is None:
        return "A_batch"
    l3_run = ct_prior.layer_runs.get("l3")
    try:
        last_l3 = datetime.fromisoformat(l3_run.last_run) if l3_run and l3_run.last_run else None
    except Exception:
        last_l3 = None
    l3_recent = last_l3 is not None and (now - last_l3.astimezone(WIB)).total_seconds() <= 1200
    fired_today = l3_buy_now_ledger.load(today) if l3_recent else set()
    return "B" if (l3_recent and ticker in fired_today) else "A"

mode = _detect_mode(ticker_arg, ct_prior, now)
```

## Step 3 — Healthcheck gate

```python
check_mode = "A" if mode == "A_batch" else mode
hc = l4_healthcheck.check(ct_prior, mode=check_mode, ticker=ticker_arg, now=now)
if not hc["ok"]:
    ct.save(ct_prior, layer="l4", status="skipped", note=f"healthcheck: {hc['reason']}")
    if "empty queue" not in hc["reason"]:
        telegram_client.send_message(f"⚠️ <b>L4 abort</b> — {hc['reason']}")
    exit()

queue = hc.get("queue") or [hc["ticker"]]
```

## Step 4 — Per-ticker loop

For each ticker:

```python
NOTES_PATH = f"runtime/monitoring/notes/10m-{today}.jsonl"
OB_DIR = "runtime/monitoring/orderbook_state"

events = []
planned = 0; aborted = 0

def _find(ct_obj, t):
    for lst in (ct_obj.lists.superlist, ct_obj.lists.exitlist):
        for it in lst:
            if it.ticker == t:
                return it
    return None

for t in queue:
    item = _find(ct_prior, t)
    if not item or not item.current_plan:
        continue
    side = "sell" if item.current_plan.mode == "sell_at_price" else "buy"

    dim = l4_dim_gather.gather_structure(t)

    ctx = {
        "ticker": t, "regime": ts.regime, "aggressiveness": ts.aggressiveness, "side": side,
        "bp_idr": bp, "conf": item.confidence, "details": item.details,
        "narrative": next((n.content for n in ts.narratives if n.ticker == t), ""),
        "structure": dim["structure"], "atr": dim["atr"], "close": dim["close"],
        "hi60": dim["hi60"], "lo60": dim["lo60"],
    }

    if mode == "B":
        ob = l4_dim_gather.gather_orderbook(t, OB_DIR) or {}
        note = l4_dim_gather.gather_last_tape_note(t, NOTES_PATH) or {}
        ctx_b = {
            "ticker": t, "conf": item.confidence,
            "orderbook": ob, "last_note": note,
            "support": dim["structure"].get("support"),
            "last_swing_low": (dim["structure"].get("last_swing_low") or {}).get("price"),
            "atr": dim["atr"], "intraday_notch": ts.intraday_notch,
        }
        prompt = l4_synth.format_plan_prompt_b(ctx_b)
    else:
        prompt = l4_synth.format_plan_prompt_a(ctx)

    try:
        raw = claude_model.call_opus(prompt)
        parsed = l4_synth.parse_opus_plan_response(raw)
    except Exception as e:
        aborted += 1
        telegram_client.send_message(f"⚠️ <b>L4 {t} error</b> — {e}")
        continue

    if parsed.get("abort"):
        aborted += 1
        telegram_client.send_message(f"⚠️ <b>L4 {t} abort</b> — {parsed['reason']}")
        continue

    sizing = l4_synth.size_plan(
        parsed["entry"], parsed["stop"], bp, ts.aggressiveness,
        ts.intraday_notch, side=side,
    )
    plan_dict = l4_synth.build_plan_struct(t, parsed, sizing, mode if mode != "A_batch" else "A",
                                           side, now_iso)
    if plan_dict.get("abort"):
        aborted += 1
        telegram_client.send_message(f"⚠️ <b>L4 {t} sizing abort</b> — {plan_dict['reason']}")
        continue

    item.plan = ct.TradePlan(**{k: v for k, v in plan_dict.items() if k != "abort"})
    item.current_plan.price = plan_dict["entry"]
    item.details = l4_synth.format_details_line(t, plan_dict, bp)
    events.append({"ticker": t, "plan": plan_dict, "side": side, "confidence": item.confidence})
    planned += 1
```

## Step 5 — Save state

```python
note = f"mode={mode} planned={planned} aborted={aborted}"
status = "ok" if planned > 0 else ("skipped" if aborted == 0 else "error")
ct.save(ct_prior, layer="l4", status=status, note=note)
```

## Step 6 — Telegram + daily note

```python
for e in events:
    msg = l4_synth.format_telegram_event(e["ticker"], e["plan"], e["side"], e["confidence"], bp)
    telegram_client.send_message(msg)

if events:
    block = l4_synth.format_daily_note_block(today, events)
    daily_note.append(today, block)
```

## Step 7 — Exit

```python
import json as _json
print(_json.dumps({
    "mode": mode, "planned": planned, "aborted": aborted,
    "tickers": [e["ticker"] for e in events],
}))
```

## Guardrails

- Whitelist writes: `lists.{superlist,exitlist}[i].{current_plan.price, details, plan}` + `layer_runs['l4']`. No writes to `trader_status.*`, `lists.watchlist`, `lists.filtered`.
- Ticker arg validated by regex `^[A-Z]{1,6}$` in healthcheck (reject shell injection).
- Duplicate guard: same-day same-mode plan → skip. Different mode OK (A → B allowed same day).
- `aggressiveness=="off"` → full abort with telegram warn.
- BP<=0 + buy-side in queue → abort. Sell-only queue OK with BP=0 (exit paths).
- Opus / parse errors per-ticker → skip that ticker, continue loop; don't fail whole run.
