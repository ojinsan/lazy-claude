# L1 — Insight & Context Synthesis (daily 04:00 WIB)

Entry: `/trade:insight`. Triggered by CRON Mon–Fri at 04:00 WIB.

L1 writes `trader_status.regime`, `trader_status.sectors`, `trader_status.narratives`, and `lists.watchlist`. Preserves all L0 fields (balance, pnl, holdings, aggressiveness). Does NOT touch filtered/superlist/exitlist (L2) or execute orders.

Spec: `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-3-l1-insight.md`.

## Step 1 — Load prior state

```python
from tools._lib import current_trade as ct
ct_prior = ct.load()
prior_status = ct_prior.trader_status
prev_regime = prior_status.regime or ""
```

If `load()` raises `ValueError`, send Telegram alert and exit — manual repair required.

## Step 2 — L1-A freshness gate

```python
from tools.trader import l1a_healthcheck
hc = l1a_healthcheck.check()  # {fresh, last_seen_minutes_ago, threshold_minutes}
```

If `hc["fresh"] is False`:

```python
from tools.trader import telegram_client
mins = hc["last_seen_minutes_ago"]
note = f"L1-A stale {mins}min" if mins is not None else "L1-A backend unreachable"
ct.save(ct_prior, layer="l1", status="error", note=note)
telegram_client.send_message(f"⚠️ <b>L1 abort</b> — {note}")
exit()
```

L1-A scraper feeds `:8787/feed/telegram/insight`. Stale = scraper down or network fault; never run synthesis on dead data.

## Step 3 — Parallel fetches (fail-soft per spec §6)

```python
from tools.trader import (
    sb_screener_hapcu_foreign_flow,
    sb_screener_retail_avoider,
    macro,
    catalyst_calendar,
    fund_manager_client,
    overnight_macro,
)
from tools.trader import api  # legacy stockbit+backend client
import datetime as dt, json, pathlib

today_wib = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()

rag_resp = fund_manager_client.rag_search(
    query="IDX OR IHSG OR sektor OR saham", limit=30
)  # list[dict] — empty on failure, never raises

try:
    hapcu_resp = sb_screener_hapcu_foreign_flow.post_screener(
        name="L1 HAPCU probe", description="", save=False,
        page=1, ordercol=2, ordertype="desc",
    )
except Exception:
    hapcu_resp = {}

try:
    retail_resp = sb_screener_retail_avoider.run(date=None)
except Exception:
    retail_resp = {"date": today_wib.isoformat(), "tickers": []}

macro_path = pathlib.Path(f"vault/data/overnight-{today_wib.isoformat()}.json")
if macro_path.exists():
    macro_snap = json.loads(macro_path.read_text())
else:
    try:
        macro_snap = overnight_macro.fetch_all()
    except Exception:
        macro_snap = {}

try:
    live_regime = macro.assess_regime()
except Exception:
    live_regime = None

catalyst_path = pathlib.Path(f"vault/data/catalyst-{today_wib.isoformat()}.json")
if catalyst_path.exists():
    catalysts = json.loads(catalyst_path.read_text())
else:
    catalysts = catalyst_calendar.build(date=today_wib.isoformat())

lark_seed = fund_manager_client.get_watchlist()  # []-on-error
```

`rag_empty = not rag_resp`. Log warnings on any exception but continue — only L1-A freshness and Opus failure are fatal.

## Step 4 — Build candidate pool

```python
from tools.trader import l1_synth

pool = l1_synth.union_candidate_pool(
    rag_top=rag_resp,
    broker_flow_hapcu=(hapcu_resp.get("data", {}).get("calcs", []) if isinstance(hapcu_resp, dict) else []),
    broker_flow_retail_avoider=retail_resp,
    lark_seed=lark_seed,
    holdings=prior_status.holdings,
)
```

Holdings always included. Preserves first-seen order. Cap to 40 for prompt budget:

```python
pool = pool[:40]
```

## Step 5 — Opus synthesis

Build one prompt with skeletal blocks. Truncate insight bodies to ≤200 chars. Expected output: strict JSON with `regime`, `sectors`, `narratives`, `watchlist`.

```python
from tools._lib import claude_model

prompt = f"""You are the L1 synthesizer for an IDX equities portfolio.

# Guardrails
- regime MUST be exactly one of: risk_on | cautious | risk_off
- sectors: 3–5 lowercase strings (e.g. "coal", "banking", "consumer")
- narratives: 3–5 items, each {{ticker, content (≤120 chars), source, confidence (int 0–100)}}
- watchlist: 5–15 items, each {{ticker, confidence (int 0–100), details (≤80 chars)}}
- Every narrative.ticker MUST appear in watchlist.
- Yesterday's regime: {prev_regime or "<none>"} — prefer stability unless clear new evidence.

# Inputs
## Candidate pool ({len(pool)})
{", ".join(pool)}

## RAG top insights (empty → rely on broker flow + macro only)
{json.dumps([
    {k: (v[:200] if isinstance(v, str) else v) for k, v in r.items()}
    for r in rag_resp[:20]
], ensure_ascii=False)}

## HAPCU smart-money net-buy
{json.dumps(hapcu_resp.get("data", {}).get("calcs", [])[:10] if isinstance(hapcu_resp, dict) else [], ensure_ascii=False)}

## Retail-avoider (retail sell + smart buy)
{json.dumps(retail_resp.get("tickers", [])[:10], ensure_ascii=False)}

## Macro overnight
{json.dumps(macro_snap, ensure_ascii=False)}

## Live regime probe
{getattr(live_regime, "__dict__", {}) if live_regime else {}}

## Catalysts today
{json.dumps(catalysts[:10], ensure_ascii=False)}

## Lark watchlist seed
{json.dumps(lark_seed[:20], ensure_ascii=False)}

## Current holdings
{json.dumps([{"ticker": h.ticker, "pnl_pct": h.pnl_pct, "details": h.details} for h in prior_status.holdings], ensure_ascii=False)}

# Output (JSON only — no prose, no code fences)
{{"regime": "...", "sectors": [...], "narratives": [...], "watchlist": [...]}}
"""

raw = claude_model.run(prompt, model="opus", fallback="openclaude")
```

On `claude_model.ModelError` (both models failed): `ct.save(status="error", note="opus+openclaude down")`, Telegram alert, exit.

## Step 6 — Validate (single shared retry)

```python
retry_used = False

def validate(draft_json: str):
    data = json.loads(draft_json)
    regime = data["regime"]
    sectors = data["sectors"]
    narratives = [
        # dataclass-compat dicts; converted below
        n for n in data["narratives"]
    ]
    watchlist_raw = data["watchlist"]
    # Convert to dataclasses for anchor check
    from tools._lib.current_trade import Narrative, ListItem, CurrentPlan
    narr_objs = [Narrative(**n) for n in narratives]
    wl_objs = [
        ListItem(
            ticker=w["ticker"],
            confidence=int(w.get("confidence", 0)),
            current_plan=None,
            details=w.get("details", ""),
        )
        for w in watchlist_raw
    ]
    errors = []
    if not l1_synth.valid_regime(regime):
        errors.append(f"regime '{regime}' not in risk_on|cautious|risk_off")
    if not l1_synth.sectors_count_valid(sectors):
        errors.append(f"sectors count/lowercase invalid: {sectors}")
    if not l1_synth.narratives_count_valid(narr_objs):
        errors.append(f"narratives count outside 3–5: {len(narr_objs)}")
    if not l1_synth.narrative_anchors_in_watchlist(narr_objs, wl_objs):
        errors.append("narrative.ticker not anchored in watchlist")
    return errors, regime, sectors, narr_objs, wl_objs

errors, regime, sectors, narr_objs, wl_objs = validate(raw)
if errors and not retry_used:
    retry_used = True
    retry_prompt = prompt + "\n\n# Previous attempt failed:\n" + "\n".join(f"- {e}" for e in errors) + "\nReturn JSON only, fix all errors."
    raw = claude_model.run(retry_prompt, model="opus", fallback="openclaude")
    errors, regime, sectors, narr_objs, wl_objs = validate(raw)

if errors:
    ct.save(ct_prior, layer="l1", status="error", note="validation: " + "; ".join(errors))
    telegram_client.send_message("⚠️ <b>L1 validation failed</b> — " + "; ".join(errors))
    exit()
```

## Step 7 — Commit draft

```python
ct_prior.trader_status.regime = regime
ct_prior.trader_status.sectors = sectors
ct_prior.trader_status.narratives = narr_objs
ct_prior.lists.watchlist = wl_objs
summary = f"regime {regime}, {len(sectors)} sectors, {len(narr_objs)} themes, watchlist {len(wl_objs)}"
ct.save(ct_prior, layer="l1", status="ok", note=summary)
```

## Step 8 — Daily note append

```python
from tools._lib import daily_note
hhmm = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).strftime("%H:%M")
body = (
    f"Regime: {regime} (prev: {prev_regime or '—'}). "
    f"Sectors: {', '.join(sectors)}. "
    f"Themes: {'; '.join(n.content for n in narr_objs)}. "
    f"Watchlist ({len(wl_objs)}): {', '.join(w.ticker for w in wl_objs)}."
)
daily_note.append_section(
    date_str=today_wib.isoformat(),
    section_heading=f"L1 — {hhmm}",
    body=body,
)
```

## Step 9 — Telegram recap (always send)

```python
recap = l1_synth.format_telegram_recap(
    regime=regime,
    sectors=sectors,
    narratives=narr_objs,
    watchlist=wl_objs,
    prev_regime=prev_regime,
    l1a_fresh_minutes=hc["last_seen_minutes_ago"] or 0,
    rag_empty=(not rag_resp),
    now_hhmm=hhmm,
)
telegram_client.send_message(recap)
```

## Guardrails

- Never write orders, never cancel orders.
- Never touch `trader_status.balance`, `pnl`, `holdings`, `aggressiveness` (L0's).
- Never touch `lists.filtered`, `superlist`, `exitlist` (L2's).
- Hard abort paths: L1-A stale, `current_trade.load()` raise, Opus+openclaude both fail, validation fails after single retry.
- Fail-soft paths: RAG empty, broker-flow fetch error, macro/catalyst missing, Lark unreachable — Opus proceeds on whatever remains.
- Idempotent: rerun same day overwrites regime/sectors/narratives/watchlist; snapshot becomes new `l1-HHMM.json`; daily note appends new `### L1 — HH:MM` section; Telegram resends.
