# L3 — Intraday Monitoring (10m cycle, 09:00–15:30 WIB)

Entry: `/trade:monitor`. Triggered by CRON every 10 minutes during IDX market hours, Mon–Fri.

L3 writes per-ticker `lists.{superlist,exitlist}[i].{current_plan,details}` + `trader_status.intraday_notch` + `layer_runs['l3']`. Preserves all L0 + L1 + L2 other fields (balance, pnl, holdings, regime, sectors, narratives, watchlist, aggressiveness). Does NOT write orders, does NOT touch `lists.watchlist` or `lists.filtered`.

Spec: `docs/superpowers/specs/2026-04-22-trading-agents-revamp-spec-5-l3-monitoring.md`.

## Step 1 — Load prior state

```python
from tools._lib import current_trade as ct
ct_prior = ct.load()
regime = ct_prior.trader_status.regime or ""
sectors = list(ct_prior.trader_status.sectors)
holdings = ct_prior.trader_status.holdings
superlist = ct_prior.lists.superlist
exitlist = ct_prior.lists.exitlist
intraday_notch = ct_prior.trader_status.intraday_notch
```

If `load()` raises, send Telegram alert and exit — manual repair required.

## Step 2 — Healthcheck gate

```python
from tools.trader import l3_healthcheck, telegram_client
hc = l3_healthcheck.check(ct_prior)
if not hc["ok"]:
    ct.save(ct_prior, layer="l3", status="error", note=f"healthcheck: {hc['reason']}")
    if "market closed" not in hc["reason"]:
        telegram_client.send_message(f"⚠️ <b>L3 abort</b> — {hc['reason']}")
    exit()
```

## Step 3 — Build dedup universe

Superlist first (highest priority), then exitlist, then holdings-only.

```python
seen = set()
universe = []
for item in superlist:
    if item.ticker not in seen:
        universe.append(("superlist", item))
        seen.add(item.ticker)
for item in exitlist:
    if item.ticker not in seen:
        universe.append(("exitlist", item))
        seen.add(item.ticker)
for h in holdings:
    if h.ticker not in seen:
        universe.append(("holding", h))
        seen.add(h.ticker)
holding_tickers = {h.ticker for h in holdings}
```

## Step 4 — Intraday-notch check (12:00 WIB single check)

Only run when current WIB time is in [12:00, 12:10).

```python
import datetime as dt
from tools.trader import api, sb_screener_hapcu_foreign_flow
from tools.trader import l3_synth

now_wib = dt.datetime.now(dt.timezone(dt.timedelta(hours=7)))
events = []
if now_wib.hour == 12 and now_wib.minute < 10:
    try:
        ihsg = api.get_stockbit_index("IHSG")
        foreign_now = sb_screener_hapcu_foreign_flow.foreign_net_flow_today()
        foreign_open = 0.0  # L1 may cache open baseline; fall back to 0
        if ihsg.get("pct_change", 0) < -1.0 and foreign_now < foreign_open:
            ct_prior.trader_status.intraday_notch = -1
            msg = l3_synth.format_intraday_notch_alert(ihsg["pct_change"], foreign_now - foreign_open)
            events.append({"kind": "notch", "message": msg})
    except Exception as e:
        print(f"[l3] notch check failed: {e}")
```

## Step 5 — Load BUY-NOW ledger

```python
from tools.trader import l3_buy_now_ledger
fired_set = l3_buy_now_ledger.load()
```

## Step 6 — Per-ticker tape judge (sequential openclaude)

For each ticker in universe:

```python
import subprocess, json, os
from pathlib import Path
from tools.trader import l3_dim_gather, l3_synth, api
from tools._lib import claude_model

WORKSPACE = Path("/home/lazywork/workspace")
PRIOR_OB_DIR = WORKSPACE / "runtime" / "monitoring" / "orderbook_state_prior"

judgments = {}  # ticker -> (judge, dim, prior_plan, is_holding, bucket)
for bucket, item in universe:
    t = item.ticker
    prior_plan_obj = getattr(item, "current_plan", None)
    prior_plan = {"mode": prior_plan_obj.mode, "price": prior_plan_obj.price} if prior_plan_obj else None

    prior_ob_path = str(PRIOR_OB_DIR / f"{t}.json")
    dim = l3_dim_gather.gather_tape(t, prior_orderbook_path=prior_ob_path)

    is_holding = t in holding_tickers
    is_superlist = (bucket == "superlist")
    is_exitlist = (bucket == "exitlist")

    ctx = {
        "is_holding": is_holding, "is_superlist": is_superlist, "is_exitlist": is_exitlist,
        "prior_plan": prior_plan, "regime": regime, "sectors": sectors, "intraday_notch": ct_prior.trader_status.intraday_notch,
    }
    prompt = l3_synth.format_judge_prompt(t, dim, ctx)

    try:
        raw = claude_model.run(prompt, model="openclaude")
        judge = l3_synth.parse_judge_response(raw)
    except Exception as e:
        try:
            raw = claude_model.run(prompt, model="openclaude")
            judge = l3_synth.parse_judge_response(raw)
        except Exception:
            print(f"[l3] judge parse fail for {t}, keep prior state: {e}")
            continue

    judgments[t] = (judge, dim, prior_plan, is_holding, bucket)
```

## Step 7 — Apply label → plan updates + BUY-NOW gate

```python
ct_new = ct_prior
superlist_by_ticker = {i.ticker: i for i in ct_new.lists.superlist}
exitlist_by_ticker  = {i.ticker: i for i in ct_new.lists.exitlist}

for t, (judge, dim, prior_plan, is_holding, bucket) in judgments.items():
    update = l3_synth.merge_plan_update(t, judge["label"], judge["buy_now"], prior_plan, is_holding)
    if update is not None:
        if t in superlist_by_ticker and update["current_plan"] is not None:
            superlist_by_ticker[t].current_plan = ct.CurrentPlan(
                mode=update["current_plan"]["mode"], price=update["current_plan"].get("price")
            )
            superlist_by_ticker[t].details = update["details"]
        elif t in superlist_by_ticker and update["current_plan"] is None:
            ct_new.lists.superlist = [x for x in ct_new.lists.superlist if x.ticker != t]
        elif t in exitlist_by_ticker and update["current_plan"] is not None:
            exitlist_by_ticker[t].current_plan = ct.CurrentPlan(
                mode=update["current_plan"]["mode"], price=update["current_plan"].get("price")
            )
            exitlist_by_ticker[t].details = update["details"]
        elif is_holding and judge["thesis_break"] and t not in exitlist_by_ticker:
            price = prior_plan.get("price") if prior_plan else None
            ct_new.lists.exitlist.append(ct.ListItem(
                ticker=t, confidence=60,
                current_plan=ct.CurrentPlan(mode="sell_at_price", price=price),
                details=update["details"],
            ))
            events.append({"kind": "thesis_break", "ticker": t, "rationale": judge["rationale"]})

    if l3_synth.buy_now_gate(
        judge, prior_plan, dim.get("price_now", 0), ct_new.trader_status.intraday_notch,
        fired_set, dim, is_superlist=(bucket == "superlist"), ticker=t,
    ):
        confirm_prompt = l3_synth.format_opus_confirm_prompt(t, dim, judge, prior_plan, dim["price_now"])
        try:
            raw = claude_model.run(confirm_prompt, model="opus")
            confirm = l3_synth.parse_opus_confirm_response(raw)
        except Exception as e:
            print(f"[l3] opus confirm fail for {t}: {e}")
            continue
        if confirm["approve"]:
            subprocess.Popen(
                ["claude", "-p", f"/trade:tradeplan {t}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            l3_buy_now_ledger.record(t)
            events.append({
                "kind": "buy_now", "ticker": t, "price": dim["price_now"],
                "rationale": confirm["rationale"],
            })
        else:
            print(f"[l3] opus rejected buy-now for {t}: {confirm['rationale']}")
```

## Step 8 — Save + event-driven telegram + daily note + snapshot prior orderbook

```python
import shutil
from tools._lib import daily_note

OB_DIR = WORKSPACE / "runtime" / "monitoring" / "orderbook_state"
PRIOR_OB_DIR.mkdir(parents=True, exist_ok=True)
for f in OB_DIR.glob("*.json"):
    shutil.copy2(f, PRIOR_OB_DIR / f.name)

buy_now_count = sum(1 for e in events if e["kind"] == "buy_now")
judged_count = len(judgments)
note = f"cycle {now_wib.strftime('%H:%M')} | judged {judged_count} | buy_now {buy_now_count} | notch {ct_new.trader_status.intraday_notch}"
ct.save(ct_new, layer="l3", status="ok", note=note)

tg_msg = l3_synth.format_telegram_events(events)
if tg_msg:
    telegram_client.send_message(tg_msg)

dn_body = l3_synth.format_daily_note_events(events, now_wib.strftime("%H:%M"))
if dn_body:
    daily_note.append_section(now_wib.date().isoformat(), f"L3 — {now_wib.strftime('%H:%M')}", dn_body)
```

## Step 9 — Exit

Snapshot `runtime/history/YYYY-MM-DD/l3-HHMM.json` is auto-written by `ct.save`. No other action needed.

## Guardrails

- Quiet cycles: no events → no telegram, no daily note. Still writes `layer_runs['l3']`.
- Per-ticker failures isolated — one parse-fail does not abort cycle.
- BUY-NOW ledger prevents same-day re-fire.
- Prior-cycle orderbook diff is best-effort: missing prior snapshot → `wall_withdrawn=false`, `thick_wall_buy_strong=false`. First cycle after market-open always has no prior — expected.
