# L2 — Stock Screening (daily 05:00 WIB)

Entry: `/trade:screening`. Triggered by CRON Mon–Fri at 05:00 WIB after L0 (04:45) and L1 (04:00).

L2 writes `lists.superlist` and `lists.exitlist`. Preserves all L0 + L1 fields (balance, pnl, holdings, aggressiveness, regime, sectors, narratives, watchlist). Does NOT write orders, does NOT touch `lists.filtered`.

Spec: `docs/superpowers/specs/2026-04-21-trading-agents-revamp-spec-4-l2-screening.md`.

## Step 1 — Load prior state

```python
from tools._lib import current_trade as ct
ct_prior = ct.load()
regime = ct_prior.trader_status.regime or ""
sectors = list(ct_prior.trader_status.sectors)
narratives = [
    {"ticker": n.ticker, "content": n.content, "source": n.source, "confidence": n.confidence}
    for n in ct_prior.trader_status.narratives
]
aggressiveness = ct_prior.trader_status.aggressiveness or ""
watchlist = ct_prior.lists.watchlist
holdings = ct_prior.trader_status.holdings
holding_tickers = {h.ticker for h in holdings}
```

If `load()` raises, send Telegram alert and exit — manual repair required.

## Step 2 — Healthcheck gate

```python
import datetime as dt, pathlib
from tools.trader import l2_healthcheck, telegram_client

today_wib = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
hapcu_path = pathlib.Path(f"vault/data/hapcu-{today_wib.isoformat()}.json")
retail_path = pathlib.Path(f"vault/data/retail-{today_wib.isoformat()}.json")

hc = l2_healthcheck.check(ct_prior, str(hapcu_path), str(retail_path))
if not hc["ok"]:
    ct.save(ct_prior, layer="l2", status="error", note=f"healthcheck: {hc['reason']}")
    telegram_client.send_message(f"⚠️ <b>L2 abort</b> — {hc['reason']}")
    exit()
```

## Step 3 — Build dedup universe

Watchlist order preserved; holdings-only tickers appended at the end. Holdings are always judged even if not in watchlist.

```python
universe = []
seen = set()
for w in watchlist:
    if w.ticker not in seen:
        universe.append(w.ticker)
        seen.add(w.ticker)
for h in holdings:
    if h.ticker not in seen:
        universe.append(h.ticker)
        seen.add(h.ticker)
```

## Step 4 — Fetch yesterday broker-flow caches (fail-soft)

```python
import json
from tools.trader import sb_screener_hapcu_foreign_flow, sb_screener_retail_avoider

if hapcu_path.exists():
    hapcu_cache = json.loads(hapcu_path.read_text())
else:
    try:
        raw = sb_screener_hapcu_foreign_flow.post_screener(
            name="L2 HAPCU", description="", save=False,
            page=1, ordercol=2, ordertype="desc",
        )
        hapcu_cache = raw.get("data", {}) if isinstance(raw, dict) else {}
        hapcu_path.write_text(json.dumps(hapcu_cache))
    except Exception:
        hapcu_cache = {}

if retail_path.exists():
    retail_cache = json.loads(retail_path.read_text())
else:
    try:
        retail_cache = sb_screener_retail_avoider.run(date=None)
        retail_path.write_text(json.dumps(retail_cache))
    except Exception:
        retail_cache = {"tickers": []}
```

## Step 5 — Per-ticker judge loop (openclaude serial)

```python
from tools.trader import l2_dim_gather as dg
from tools.trader import l2_synth
from tools._lib import claude_model

judgments = {}  # ticker -> (scores, rationale, is_holding)
fallback_count = 0

def _primary_sector(t):
    # Best-effort: pick the first L1 sector; konglo_loader can refine.
    return sectors[0] if sectors else None

for t in universe:
    dims = {
        1: dg.gather_price(t, sector=_primary_sector(t)),
        2: dg.gather_broker(t, hapcu_cache, retail_cache, l1_sectors=sectors),
        3: dg.gather_book(t),
        4: dg.gather_narrative(t, narratives),
    }
    is_holding = t in holding_tickers
    context = {
        "regime": regime,
        "sectors": sectors,
        "aggressiveness": aggressiveness,
        "is_holding": is_holding,
    }
    prompt = l2_synth.format_judge_prompt(t, dims, context)
    try:
        raw = claude_model.run(prompt, model="openclaude", fallback="opus")
        scores, rationale = l2_synth.parse_judge_response(raw)
    except Exception:
        # one retry with explicit error instruction
        try:
            raw = claude_model.run(prompt + "\n\nReturn STRICT JSON only.", model="openclaude", fallback="opus")
            scores, rationale = l2_synth.parse_judge_response(raw)
        except Exception as e2:
            scores = {"price": "weak", "broker": "weak", "book": "weak", "narrative": "weak"}
            rationale = f"fallback (judge failed: {e2})"
            fallback_count += 1

    # Apply judge_floor from dim-1 spring
    floor = dims[1].get("judge_floor") if isinstance(dims[1], dict) else None
    if floor == "strong":
        for k, v in list(scores.items()):
            if v == "weak":
                scores[k] = "strong" if k == "price" else scores[k]
    judgments[t] = (scores, rationale, is_holding)

# Safety: abort layer if >50% tickers fell through to fallback
if fallback_count * 2 > len(universe):
    ct.save(ct_prior, layer="l2", status="error",
            note=f"judge fallback {fallback_count}/{len(universe)} — upstream fail")
    telegram_client.send_message(f"⚠️ <b>L2 abort</b> — judge fallback {fallback_count}/{len(universe)}")
    exit()
```

## Step 6 — Apply promotion truth table

```python
promoted_raw = []  # for merge prompt
exits_raw = []

for t, (scores, rationale, is_holding) in judgments.items():
    verdict = l2_synth.promotion_decision(scores, is_holding)
    entry = {"ticker": t, "scores": scores, "rationale": rationale, "is_holding": is_holding}
    if verdict == "superlist":
        promoted_raw.append(entry)
    elif verdict == "exitlist":
        exits_raw.append(entry)
```

## Step 7 — Opus merge → current_plan per ticker

```python
merge_prompt = l2_synth.format_merge_prompt(
    promoted=promoted_raw,
    exits=exits_raw,
    holdings=list(holding_tickers),
    regime=regime,
)
try:
    merge_raw = claude_model.run(merge_prompt, model="opus", fallback="openclaude")
    merge_out = l2_synth.parse_merge_response(merge_raw)
except Exception:
    merge_out = {}  # fall back to wait_bid_offer below

def _plan_from(ticker, default_plan):
    m = merge_out.get(ticker) or {}
    return m.get("current_plan", default_plan), m.get("details", "")

from tools._lib.current_trade import ListItem, CurrentPlan

superlist_items = []
for entry in promoted_raw:
    plan, details = _plan_from(entry["ticker"], "wait_bid_offer")
    confidence = 80  # openclaude doesn't emit a numeric; derive later if useful
    superlist_items.append(ListItem(
        ticker=entry["ticker"],
        confidence=confidence,
        current_plan=CurrentPlan(mode=plan),
        details=details or entry["rationale"][:120],
    ))

exit_items = []
for entry in exits_raw:
    plan, details = _plan_from(entry["ticker"], "sell_at_price")
    exit_items.append(ListItem(
        ticker=entry["ticker"],
        confidence=70,
        current_plan=CurrentPlan(mode=plan),
        details=details or entry["rationale"][:120],
    ))
```

## Step 8 — Commit draft

```python
prev_super_count = len(ct_prior.lists.superlist)
ct_prior.lists.superlist = superlist_items
ct_prior.lists.exitlist = exit_items
summary = (
    f"judged {len(judgments)} (watchlist {len(watchlist)} + holdings {len(holdings)} dedup), "
    f"promoted {len(superlist_items)}, exit {len(exit_items)}"
)
ct.save(ct_prior, layer="l2", status="ok", note=summary)
```

## Step 9 — Daily note + Telegram recap (always send)

```python
from tools._lib import daily_note
hhmm = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).strftime("%H:%M")

top3_super = ", ".join(f"{s.ticker}[{s.current_plan.mode}]" for s in superlist_items[:3]) or "—"
top3_exit = ", ".join(f"{e.ticker}[{e.current_plan.mode}]" for e in exit_items[:3]) or "—"
body = (
    f"Regime: {regime}. "
    f"Judged {len(judgments)} → superlist {len(superlist_items)}, exitlist {len(exit_items)}. "
    f"Top super: {top3_super}. Top exit: {top3_exit}."
)
daily_note.append_section(
    date_str=today_wib.isoformat(),
    section_heading=f"L2 — {hhmm}",
    body=body,
)

recap = l2_synth.format_telegram_recap(
    superlist=[{"ticker": s.ticker, "current_plan": s.current_plan.mode, "details": s.details} for s in superlist_items],
    exitlist=[{"ticker": e.ticker, "current_plan": e.current_plan.mode, "details": e.details} for e in exit_items],
    n_judged=len(judgments),
    regime=regime,
    prev_superlist_count=prev_super_count,
    now_hhmm=hhmm,
)
telegram_client.send_message(recap)
```

## Guardrails

- Never write orders, never cancel orders.
- Never touch `trader_status.*` (L0+L1 own those).
- Never touch `lists.watchlist` (L1 owns it) or `lists.filtered` (reserved).
- Hard abort paths: `current_trade.load()` raises, healthcheck fails, judge fallback >50% of universe.
- Fail-soft paths: broker-flow cache missing, per-ticker judge parse fail (retry + fallback weak), Opus merge fail (wait_bid_offer default).
- Idempotent: rerun same day overwrites superlist/exitlist; snapshot becomes new `l2-HHMM.json`; daily note appends new `### L2 — HH:MM` section; Telegram resends.
