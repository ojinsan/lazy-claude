# Spec #6 — L4 Trade Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build L4 trade plan: two modes — **Mode A** (post-L2 morning batch over `lists.superlist/exitlist` where `current_plan.mode ∈ {buy_at_price, sell_at_price}` and `plan is None`) and **Mode B** (intraday sizing-only, invoked by L3 BUY-NOW popen with ticker arg). Opus produces entry/stop/TP floats + rationale; Python handles IDX tick rounding + lot sizing + 30% BP cap + notch-tier shrink. Writes `lists.{superlist,exitlist}[i].{current_plan.price, details, plan}` + `layer_runs['l4']`. Telegram event per finalized plan; daily note append.

**Architecture:** Same shape as L2/L3 — pure-function helpers in `tools/trader/` for dim gather + synth + healthcheck; playbook Markdown orchestrates mode detect → per-ticker loop (gather → Opus plan → parse → size → write). No AI inside gatherers or sizers. IDX tick table + lot math live in `l4_synth.py`.

**Tech Stack:** Python 3.12 stdlib only (dataclasses, json, pathlib, datetime, math, unittest, unittest.mock). No pydantic, no pytest. Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`, `tools/_lib/daily_note.py`. Existing tools: `api.compute_indicators_from_price_data` (ATR), `market_structure.analyze_market_structure` (S/R + swing points), `l3_buy_now_ledger` (Mode B detect), `telegram_client.py`.

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md`

---

## File Structure

**Create:**
- `tools/trader/l4_synth.py` — IDX tick + lot math (`get_tick`, `round_to_tick`, `size_plan`); prompt builders (`format_plan_prompt_a`, `format_plan_prompt_b`); response parser (`parse_opus_plan_response`); struct builder (`build_plan_struct`); formatters (`format_details_line`, `format_telegram_event`, `format_daily_note_block`).
- `tools/trader/l4_dim_gather.py` — Mode A: `gather_structure(t)` (indicators + market_structure). Mode B: adds `gather_orderbook(t)` + `gather_last_tape_note(t)`. Graceful-degrade.
- `tools/trader/l4_healthcheck.py` — `check(ct, mode, ticker=None)` → gates per spec §8.
- `playbooks/trader/layer-4-tradeplan.md` — arg-parse → healthcheck → mode detect → per-ticker loop → save + telegram + daily note.
- `tests/trader/test_l4_synth.py`
- `tests/trader/test_l4_dim_gather.py`
- `tests/trader/test_l4_healthcheck.py`
- `tests/trader/fixtures/l4/structure_ADMR.json`
- `tests/trader/fixtures/l4/indicators_ADMR.json`
- `tests/trader/fixtures/l4/orderbook_ADMR_fresh.json`
- `tests/trader/fixtures/l4/notes_10m_ADMR.json`
- `tests/trader/fixtures/l4/opus_plan_A_approve.json`
- `tests/trader/fixtures/l4/opus_plan_B_approve.json`
- `tests/trader/fixtures/l4/opus_plan_B_abort.json`
- `tests/trader/fixtures/l4/opus_malformed.json`

**Modify:**
- `tools/_lib/current_trade.py` — add `TradePlan` dataclass + `ListItem.plan: Optional[TradePlan] = None`, parse/serialize, back-compat (`None` if missing).
- `tests/_lib/test_current_trade.py` — add `TradePlan` parse/save + back-compat tests.
- `.claude/commands/trade/tradeplan.md` — replace stub with thin trigger + arg passthrough.
- `playbooks/trader/CLAUDE.md` — flip L4 row stub → live.
- `skills/trader/CLAUDE.md` — add L4 playbook row.
- `docs/revamp-progress.md` — fill Used-by=L4 for: `api.py` (compute_indicators), `market_structure.py`, `claude_model.py`, `daily_note.py`, `telegram_client.py`, `l3_buy_now_ledger.py` (Mode B detect), `current_trade.py` (schema). Add rows for new `l4_synth.py`, `l4_dim_gather.py`, `l4_healthcheck.py`. Spec #6 status → `in progress (plan-complete, pre-dry-run)`.
- `tools/INDEX.md` — add 3 new rows; tag `api.py`/`market_structure.py`/`claude_model.py`/`daily_note.py`/`telegram_client.py` with L4.

---

## Task 1: Fixtures + package markers

**Files:** `tests/trader/fixtures/l4/*` (8 files).

- [ ] **Step 1: Create dir.**
```bash
mkdir -p tests/trader/fixtures/l4
```

- [ ] **Step 2: `structure_ADMR.json`** — shape matches `market_structure.MarketStructure.__dict__`:
```json
{
  "ticker": "ADMR",
  "current_price": 1870,
  "trend": "uptrend",
  "trend_strength": 3,
  "support": 1820,
  "resistance": 1960,
  "support_strength": 4,
  "resistance_strength": 3,
  "wyckoff_phase": "accumulation",
  "wyckoff_position": "lps",
  "last_swing_low": {"price": 1830, "time": "2026-04-18", "type": "low", "strength": 3},
  "last_swing_high": {"price": 1920, "time": "2026-04-21", "type": "high", "strength": 2}
}
```

- [ ] **Step 3: `indicators_ADMR.json`** — subset of `compute_indicators_from_price_data` output:
```json
{"ticker": "ADMR", "close": 1870, "atr_14": 32, "high_60d": 1960, "low_60d": 1620}
```

- [ ] **Step 4: `orderbook_ADMR_fresh.json`** — snapshot shape matches L3 producer:
```json
{
  "ticker": "ADMR",
  "ts": "2026-04-22T12:10:05+07:00",
  "last_price": 1875,
  "best_bid": 1870, "best_offer": 1875,
  "bids": [{"price": 1870, "lot": 8500}, {"price": 1865, "lot": 12000}],
  "offers": [{"price": 1875, "lot": 3200}, {"price": 1880, "lot": 18000}]
}
```

- [ ] **Step 5: `notes_10m_ADMR.json`** — last entry from `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl`:
```json
{"ts": "2026-04-22T12:10:00+07:00", "ticker": "ADMR", "label": "strengthening", "composite": "ideal_markup", "thick_wall_buy_strong": true, "spring_confirmed": true}
```

- [ ] **Step 6: `opus_plan_A_approve.json`** — Opus Mode A response:
```json
{"entry": 1855, "stop": 1835, "tp1": 1955, "tp2": 2050, "rationale": "Accumulation LPS at support 1820; entry above last_swing_low 1830 with tight stop. TP1 at 2R structural, TP2 near 60d_high resistance."}
```

- [ ] **Step 7: `opus_plan_B_approve.json`** — Opus Mode B response (sizing-only):
```json
{"entry": 1875, "stop": 1825, "tp1": 1940, "tp2": 1960, "rationale": "BUY-NOW tape + thick offer absorb. Stop = last_swing_low -1 tick. TP1 = entry + 2*ATR, TP2 at resistance."}
```

- [ ] **Step 8: `opus_plan_B_abort.json`** — Mode B abort case:
```json
{"abort": true, "reason": "stop distance 78 > 1.5*ATR=48 — too loose"}
```

- [ ] **Step 9: `opus_malformed.json`** — missing required key:
```json
{"entry": 1855, "stop": 1835, "rationale": "forgot tp1"}
```

- [ ] **Step 10: Commit fixtures.**
```bash
git add tests/trader/fixtures/l4/
git commit -m "L4 test fixtures (spec #6 Task 1)"
```

**Verify:** `ls tests/trader/fixtures/l4/ | wc -l` → 8.

---

## Task 2: `current_trade.py` — `TradePlan` + `ListItem.plan`

**Files:** `tools/_lib/current_trade.py`, `tests/_lib/test_current_trade.py`.

- [ ] **Step 1: Add `TradePlan` dataclass + field.** After `CurrentPlan`:
```python
@dataclass
class TradePlan:
    entry: float
    stop: float
    tp1: float
    tp2: Optional[float] = None
    lots: int = 0
    risk_idr: float = 0.0
    mode: str = "A"              # "A" | "B"
    rationale: str = ""
    updated_at: str = ""
```

Update `ListItem`:
```python
@dataclass
class ListItem:
    ticker: str
    confidence: int
    current_plan: Optional[CurrentPlan] = None
    details: str = ""
    plan: Optional[TradePlan] = None
```

- [ ] **Step 2: Parser.** In `_parse_list_item`:
```python
raw_plan = d.get("plan")
plan = None
if raw_plan:
    plan = TradePlan(
        entry=float(raw_plan["entry"]),
        stop=float(raw_plan["stop"]),
        tp1=float(raw_plan["tp1"]),
        tp2=float(raw_plan["tp2"]) if raw_plan.get("tp2") is not None else None,
        lots=int(raw_plan.get("lots", 0)),
        risk_idr=float(raw_plan.get("risk_idr", 0)),
        mode=raw_plan.get("mode", "A"),
        rationale=raw_plan.get("rationale", ""),
        updated_at=raw_plan.get("updated_at", ""),
    )
return ListItem(ticker=..., confidence=..., current_plan=..., details=..., plan=plan)
```

Serializer: `asdict` already handles Optional dataclass — verify round-trip.

- [ ] **Step 3: Tests.** Add to `tests/_lib/test_current_trade.py`:
  - `test_parse_list_item_with_plan` — all fields present
  - `test_parse_list_item_missing_plan_key_back_compat` — old JSON without `plan` → `None`
  - `test_trade_plan_tp2_null_roundtrip` — `tp2=None` survives save→load
  - `test_save_load_full_schema_with_plan` — full current_trade.json with plans round-trips

- [ ] **Step 4: Run + commit.**
```bash
python3 -m unittest tests._lib.test_current_trade -v
git add tools/_lib/current_trade.py tests/_lib/test_current_trade.py
git commit -m "current_trade: add TradePlan + ListItem.plan (spec #6 Task 2)"
```

---

## Task 3: `l4_synth.py` — IDX tick math

**Files:** `tools/trader/l4_synth.py`, `tests/trader/test_l4_synth.py`.

- [ ] **Step 1: Skeleton.**
```python
"""L4 pure helpers: IDX tick math, sizing, prompt builders, parsers, formatters."""
from __future__ import annotations
import math
from dataclasses import asdict
from datetime import datetime
from typing import Optional

# IDX fraksi harga
def get_tick(price: float) -> int:
    p = float(price)
    if p < 200:   return 1
    if p < 500:   return 2
    if p < 2000:  return 5
    if p < 5000:  return 10
    return 25

def round_to_tick(price: float, side: str, role: str) -> int:
    """side ∈ {'buy','sell'}, role ∈ {'entry','stop','tp'}.
    Conservative bias: buy fills → round down entry; wider stop → round down for buy stop;
    aspirational TP → round up for buy TP. Sell mirrors."""
    t = get_tick(price)
    if side == "buy":
        direction = {"entry": "down", "stop": "down", "tp": "up"}[role]
    else:  # sell
        direction = {"entry": "up", "stop": "up", "tp": "down"}[role]
    if direction == "up":
        return int(math.ceil(price / t) * t)
    return int(math.floor(price / t) * t)
```

- [ ] **Step 2: Tests — tick table matrix.**
```python
def test_get_tick_bands(self):
    self.assertEqual(get_tick(150), 1)
    self.assertEqual(get_tick(199), 1)
    self.assertEqual(get_tick(200), 2)
    self.assertEqual(get_tick(499), 2)
    self.assertEqual(get_tick(500), 5)
    self.assertEqual(get_tick(1999), 5)
    self.assertEqual(get_tick(2000), 10)
    self.assertEqual(get_tick(4999), 10)
    self.assertEqual(get_tick(5000), 25)
    self.assertEqual(get_tick(12500), 25)
```

- [ ] **Step 3: Tests — round_to_tick per side/role.**
```python
def test_round_buy_entry_down(self):
    self.assertEqual(round_to_tick(1872, "buy", "entry"), 1870)   # tick 5, down
def test_round_buy_stop_down(self):
    self.assertEqual(round_to_tick(1833, "buy", "stop"), 1830)
def test_round_buy_tp_up(self):
    self.assertEqual(round_to_tick(1951, "buy", "tp"), 1955)
def test_round_sell_entry_up(self):
    self.assertEqual(round_to_tick(1872, "sell", "entry"), 1875)
def test_round_sell_stop_up(self):
    self.assertEqual(round_to_tick(1921, "sell", "stop"), 1925)
def test_round_sell_tp_down(self):
    self.assertEqual(round_to_tick(1832, "sell", "tp"), 1830)
def test_round_exact_tick_noop(self):
    self.assertEqual(round_to_tick(1870, "buy", "entry"), 1870)
def test_round_cross_band(self):
    self.assertEqual(round_to_tick(201, "buy", "entry"), 200)     # tick 2
```

- [ ] **Step 4: Run + commit.**
```bash
python3 -m unittest tests.trader.test_l4_synth -v
git add tools/trader/l4_synth.py tests/trader/test_l4_synth.py
git commit -m "l4_synth: IDX tick math (spec #6 Task 3)"
```

---

## Task 4: `l4_synth.py` — sizing formula

**Files:** `tools/trader/l4_synth.py`, `tests/trader/test_l4_synth.py`.

- [ ] **Step 1: Add `TIER` + `size_plan`.**
```python
TIER = {"low": 0.01, "med": 0.02, "high": 0.03, "off": None}
BP_SINGLE_NAME_CAP = 0.30

def size_plan(entry: float, stop: float, buying_power: float,
              aggressiveness: str, intraday_notch: int, side: str = "buy") -> dict:
    tier = TIER.get((aggressiveness or "").lower())
    if tier is None:
        return {"abort": True, "reason": "aggressiveness=off"}
    if buying_power <= 0:
        return {"abort": True, "reason": "buying_power<=0"}
    if intraday_notch < 0:
        tier = max(round(tier - 0.01, 2), 0.01)
    dist = abs(float(entry) - float(stop))
    if dist <= 0:
        return {"abort": True, "reason": "zero stop distance"}
    risk_idr = buying_power * tier
    shares = risk_idr / dist
    lots = int(shares // 100)
    max_lots_cap = int((buying_power * BP_SINGLE_NAME_CAP) / (entry * 100)) if entry > 0 else 0
    lots = min(lots, max_lots_cap)
    if lots <= 0:
        return {"abort": True, "reason": "sub-lot size"}
    return {
        "lots": lots,
        "risk_idr": round(lots * 100 * dist),
        "notional": round(lots * 100 * entry),
        "tier": tier,
    }
```

- [ ] **Step 2: Tests.**
```python
def test_size_plan_normal(self):
    r = size_plan(entry=1850, stop=1830, buying_power=100_000_000, aggressiveness="med", intraday_notch=0)
    # risk = 2M, dist = 20, shares = 100000, lots = 1000 → cap check: 0.30*100M / (1850*100) = 162
    self.assertFalse(r.get("abort"))
    self.assertEqual(r["lots"], 162)  # BP-cap binds

def test_size_plan_notch_shrinks_tier(self):
    r = size_plan(1850, 1830, 100_000_000, "high", intraday_notch=-1)
    self.assertEqual(r["tier"], 0.02)   # high(3%) → med(2%)

def test_size_plan_low_notch_floors_at_1pct(self):
    r = size_plan(1850, 1830, 100_000_000, "low", intraday_notch=-1)
    self.assertEqual(r["tier"], 0.01)

def test_size_plan_off_aborts(self):
    r = size_plan(1850, 1830, 100_000_000, "off", 0)
    self.assertTrue(r["abort"]); self.assertIn("off", r["reason"])

def test_size_plan_zero_bp_aborts(self):
    r = size_plan(1850, 1830, 0, "med", 0)
    self.assertTrue(r["abort"])

def test_size_plan_zero_dist_aborts(self):
    r = size_plan(1850, 1850, 100_000_000, "med", 0)
    self.assertTrue(r["abort"]); self.assertIn("zero", r["reason"])

def test_size_plan_sub_lot_aborts(self):
    r = size_plan(50000, 49999, 100_000, "low", 0)
    self.assertTrue(r["abort"])
```

- [ ] **Step 3: Run + commit.**
```bash
python3 -m unittest tests.trader.test_l4_synth -v
git commit -am "l4_synth: size_plan (spec #6 Task 4)"
```

---

## Task 5: `l4_synth.py` — prompts + parser

**Files:** `tools/trader/l4_synth.py`, `tests/trader/test_l4_synth.py`.

- [ ] **Step 1: Prompt builders.**
```python
def format_plan_prompt_a(ctx: dict) -> str:
    """ctx keys: ticker, regime, aggressiveness, side, bp_idr, conf, details, narrative,
    structure (dict), atr, close, hi60, lo60."""
    s = ctx["structure"]
    lsl = s.get("last_swing_low") or {}
    return (
        f"You are L4 trade-plan synth for IDX ticker {ctx['ticker']}. Output one trade plan as JSON.\n\n"
        f"Context:\n"
        f"- regime={ctx['regime']}, aggressiveness={ctx['aggressiveness']}, side={ctx['side']}\n"
        f"- buying_power={ctx['bp_idr']:,.0f}, confidence={ctx['conf']}/100\n"
        f"- prior details (L2): {ctx.get('details','—')}\n"
        f"- narrative: {ctx.get('narrative','—')}\n"
        f"- structure: trend={s.get('trend','?')}, wyckoff={s.get('wyckoff_phase','?')}, "
        f"support={s.get('support')}, resistance={s.get('resistance')}, "
        f"last_swing_low={lsl.get('price','?')}\n"
        f"- ATR(14)={ctx['atr']}, last_close={ctx['close']}, 60d_high={ctx['hi60']}, 60d_low={ctx['lo60']}\n\n"
        f"Rules:\n"
        f"- Buy: entry near support OR above last_swing_low, stop below invalidation "
        f"(last_swing_low -1 tick OR support -0.5*ATR), TP1 >=1.5R, TP2 >=3R OR near resistance.\n"
        f"- Sell: mirror. Entry near resistance or break of support; stop above last_swing_high.\n"
        f"- Do NOT compute lot size — Python handles sizing.\n"
        f"- Output raw float prices; Python applies tick rounding.\n\n"
        f'Output strict JSON: {{"entry": <float>, "stop": <float>, "tp1": <float>, '
        f'"tp2": <float|null>, "rationale": "<=180 chars"}}'
    )

def format_plan_prompt_b(ctx: dict) -> str:
    ob = ctx["orderbook"]; nt = ctx["last_note"]
    return (
        f"You are L4 sizing-only synth for IDX ticker {ctx['ticker']}. L3 just fired BUY-NOW.\n\n"
        f"Context:\n"
        f"- side=buy, confidence={ctx['conf']}/100\n"
        f"- orderbook: best_bid={ob['best_bid']}, best_offer={ob['best_offer']}, last={ob['last_price']}\n"
        f"- tape: {nt.get('composite','?')} | thick_wall_buy_strong={nt.get('thick_wall_buy_strong',False)} "
        f"| spring_confirmed={nt.get('spring_confirmed',False)}\n"
        f"- structure: support={ctx['support']}, last_swing_low={ctx['last_swing_low']}, ATR(14)={ctx['atr']}\n"
        f"- intraday_notch={ctx['intraday_notch']}\n\n"
        f"Rules:\n"
        f"- Entry = current best_offer (sweep) OR last+1 tick.\n"
        f"- Stop = last_swing_low - 1 tick. If dist > 1.5*ATR → abort.\n"
        f"- TP1 = entry + 2*ATR (min 1.5R). TP2 = entry + 4*ATR OR resistance, whichever closer.\n\n"
        f'Output strict JSON: {{"entry": <float>, "stop": <float>, "tp1": <float>, '
        f'"tp2": <float|null>, "rationale": "<=140 chars"}} '
        f'OR {{"abort": true, "reason": "<=80 chars"}}'
    )
```

- [ ] **Step 2: Parser.**
```python
def parse_opus_plan_response(raw: str) -> dict:
    """Strip code fences, parse JSON, validate. Accepts {abort:true,reason:...} OR full plan."""
    s = raw.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        s = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    import json as _j
    d = _j.loads(s)
    if d.get("abort") is True:
        if "reason" not in d:
            raise ValueError("abort response missing 'reason'")
        return {"abort": True, "reason": str(d["reason"])[:80]}
    for k in ("entry", "stop", "tp1", "rationale"):
        if k not in d:
            raise ValueError(f"plan response missing key: {k}")
    return {
        "entry": float(d["entry"]),
        "stop": float(d["stop"]),
        "tp1": float(d["tp1"]),
        "tp2": float(d["tp2"]) if d.get("tp2") is not None else None,
        "rationale": str(d["rationale"])[:180],
    }
```

- [ ] **Step 3: Tests.**
```python
def test_prompt_a_contains_structure(self): ...     # keys rendered
def test_prompt_b_contains_orderbook(self): ...
def test_parse_approve_full(self):
    raw = open("tests/trader/fixtures/l4/opus_plan_A_approve.json").read()
    d = parse_opus_plan_response(raw)
    self.assertEqual(d["entry"], 1855); self.assertEqual(d["tp2"], 2050)
def test_parse_abort(self):
    raw = open("tests/trader/fixtures/l4/opus_plan_B_abort.json").read()
    d = parse_opus_plan_response(raw)
    self.assertTrue(d["abort"])
def test_parse_malformed_raises(self):
    raw = open("tests/trader/fixtures/l4/opus_malformed.json").read()
    with self.assertRaises(ValueError):
        parse_opus_plan_response(raw)
def test_parse_fenced(self):
    parse_opus_plan_response('```json\n{"entry":1,"stop":0.5,"tp1":2,"rationale":"x"}\n```')
def test_parse_tp2_null(self):
    d = parse_opus_plan_response('{"entry":1,"stop":0.5,"tp1":2,"tp2":null,"rationale":"x"}')
    self.assertIsNone(d["tp2"])
```

- [ ] **Step 4: Commit.**
```bash
python3 -m unittest tests.trader.test_l4_synth -v
git commit -am "l4_synth: prompts + parser (spec #6 Task 5)"
```

---

## Task 6: `l4_synth.py` — struct + formatters

**Files:** `tools/trader/l4_synth.py`, `tests/trader/test_l4_synth.py`.

- [ ] **Step 1: Struct builder.** Applies tick rounding + sizing → returns TradePlan-ready dict:
```python
def build_plan_struct(ticker: str, parsed: dict, sizing: dict, mode: str,
                      side: str, now_iso: str) -> dict:
    """parsed from parse_opus_plan_response; sizing from size_plan."""
    if parsed.get("abort") or sizing.get("abort"):
        return {"abort": True, "reason": parsed.get("reason") or sizing.get("reason")}
    entry = round_to_tick(parsed["entry"], side, "entry")
    stop  = round_to_tick(parsed["stop"],  side, "stop")
    tp1   = round_to_tick(parsed["tp1"],   side, "tp")
    tp2   = round_to_tick(parsed["tp2"],   side, "tp") if parsed.get("tp2") is not None else None
    return {
        "entry": entry, "stop": stop, "tp1": tp1, "tp2": tp2,
        "lots": sizing["lots"], "risk_idr": sizing["risk_idr"],
        "mode": mode, "rationale": parsed["rationale"], "updated_at": now_iso,
    }
```

- [ ] **Step 2: Formatters.**
```python
def format_details_line(ticker: str, plan: dict, bp_idr: float) -> str:
    """One-line summary for ListItem.details."""
    entry, stop, tp1, tp2, lots = plan["entry"], plan["stop"], plan["tp1"], plan.get("tp2"), plan["lots"]
    stop_pct = round(abs(entry - stop) / entry * 100, 2)
    r = abs(tp1 - entry) / max(abs(entry - stop), 1)
    notional = lots * 100 * entry
    bp_pct = round(notional / bp_idr * 100, 1) if bp_idr > 0 else 0
    tp2_s = f" | T2 {tp2}" if tp2 else ""
    return (f"L4-{plan['mode']}: E {entry} | SL {stop} ({stop_pct}%) | "
            f"T1 {tp1} ({r:.1f}R){tp2_s} | {lots}lot {notional/1e6:.2f}M/{bp_pct}%BP")

def format_telegram_event(ticker: str, plan: dict, side: str, confidence: int, bp_idr: float) -> str:
    entry, stop, tp1, tp2, lots = plan["entry"], plan["stop"], plan["tp1"], plan.get("tp2"), plan["lots"]
    stop_pct = round(abs(entry - stop) / entry * 100, 2)
    r = abs(tp1 - entry) / max(abs(entry - stop), 1)
    notional = lots * 100 * entry
    bp_pct = round(notional / bp_idr * 100, 1) if bp_idr > 0 else 0
    tp2_s = f" | T2 {tp2}" if tp2 else ""
    return (f"[L4-{plan['mode']}] {ticker} {side}\n"
            f"E {entry} | SL {stop} ({stop_pct}%) | T1 {tp1} ({r:.1f}R){tp2_s}\n"
            f"Size {lots}lot ({notional/1e6:.2f}M/{bp_pct}%BP) | Conv {confidence}\n"
            f"{plan['rationale']}")

def format_daily_note_block(date: str, plans: list[dict]) -> str:
    """plans: list of {ticker, plan, side, confidence}."""
    lines = [f"## L4 Trade Plan — {date}", ""]
    for p in plans:
        lines.append(f"- **{p['ticker']}** ({p['side']}, conv {p['confidence']}): "
                     f"E {p['plan']['entry']} / SL {p['plan']['stop']} / "
                     f"T1 {p['plan']['tp1']} / {p['plan']['lots']}lot — {p['plan']['rationale']}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 3: Tests.**
```python
def test_build_plan_applies_tick_rounding(self): ...  # 1853 → 1850 for buy entry
def test_build_plan_abort_propagates(self): ...
def test_details_line_contains_all_fields(self): ...
def test_telegram_event_sell_side(self): ...
def test_daily_note_block_multi_ticker(self): ...
```

- [ ] **Step 4: Commit.**
```bash
git commit -am "l4_synth: struct + formatters (spec #6 Task 6)"
```

---

## Task 7: `l4_dim_gather.py`

**Files:** `tools/trader/l4_dim_gather.py`, `tests/trader/test_l4_dim_gather.py`.

- [ ] **Step 1: Module.**
```python
"""L4 dim gatherers. Mode A: structure+indicators. Mode B: adds orderbook+last tape note."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

def gather_structure(ticker: str, *, market_structure_fn=None, indicators_fn=None) -> dict:
    """Returns {'structure': {...}, 'atr': float, 'close': float, 'hi60': float, 'lo60': float,
    'context_missing': list[str]}. Graceful-degrade on exceptions."""
    missing = []
    struct = {}
    try:
        if market_structure_fn is None:
            from tools.trader.market_structure import analyze_market_structure as market_structure_fn
        ms = market_structure_fn(ticker, days=30)
        struct = {
            "trend": ms.trend, "wyckoff_phase": ms.wyckoff_phase,
            "support": ms.support, "resistance": ms.resistance,
            "last_swing_low": ({"price": ms.last_swing_low.price} if ms.last_swing_low else None),
            "last_swing_high": ({"price": ms.last_swing_high.price} if ms.last_swing_high else None),
        }
    except Exception as e:
        missing.append(f"structure:{e}")
    atr = close = hi60 = lo60 = None
    try:
        if indicators_fn is None:
            from tools.trader._lib.api import compute_indicators_from_price_data as indicators_fn  # adjust path
        ind = indicators_fn(ticker, timeframe="1d", limit=60)
        atr = ind.get("atr_14"); close = ind.get("close")
        hi60 = ind.get("high_60d") or max(ind.get("highs", [0]) or [0])
        lo60 = ind.get("low_60d") or min(ind.get("lows", [0]) or [0])
    except Exception as e:
        missing.append(f"indicators:{e}")
    return {"structure": struct, "atr": atr, "close": close, "hi60": hi60, "lo60": lo60,
            "context_missing": missing}

def gather_orderbook(ticker: str, orderbook_state_dir: str) -> Optional[dict]:
    p = Path(orderbook_state_dir) / f"{ticker}.json"
    if not p.exists(): return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def gather_last_tape_note(ticker: str, notes_path: str) -> Optional[dict]:
    p = Path(notes_path)
    if not p.exists(): return None
    last = None
    for line in p.read_text().splitlines():
        try:
            d = json.loads(line)
            if d.get("ticker") == ticker:
                last = d
        except Exception:
            continue
    return last
```

- [ ] **Step 2: Tests.**
```python
def test_gather_structure_happy(self):          # inject mocks → merged dict
def test_gather_structure_indicators_fail(self):# still returns structure, atr=None, context_missing populated
def test_gather_structure_both_fail(self):      # context_missing has 2 entries
def test_gather_orderbook_reads_json(self):     # tmpdir fixture
def test_gather_orderbook_missing_returns_none(self):
def test_gather_orderbook_corrupt_returns_none(self):
def test_gather_last_note_returns_latest_for_ticker(self):  # jsonl with 3 lines, 2 for ADMR
def test_gather_last_note_no_ticker_match(self):
```

- [ ] **Step 3: Commit.**
```bash
python3 -m unittest tests.trader.test_l4_dim_gather -v
git add tools/trader/l4_dim_gather.py tests/trader/test_l4_dim_gather.py
git commit -m "l4_dim_gather: structure/indicators/orderbook/notes (spec #6 Task 7)"
```

---

## Task 8: `l4_healthcheck.py`

**Files:** `tools/trader/l4_healthcheck.py`, `tests/trader/test_l4_healthcheck.py`.

- [ ] **Step 1: Module.**
```python
"""L4 pre-run gates."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional
from tools._lib.current_trade import CurrentTrade

TICKER_RE = re.compile(r"^[A-Z]{1,6}$")

def check(ct: CurrentTrade, mode: str, ticker: Optional[str] = None, now: Optional[datetime] = None) -> dict:
    """Returns {'ok': bool, 'reason': str, 'queue': list[str]} for Mode A batch; {'ok',reason,ticker} for B/single-A."""
    ts = ct.trader_status
    if (ts.aggressiveness or "").lower() == "off":
        return {"ok": False, "reason": "aggressiveness=off (kill-switch)"}
    if ticker is not None:
        if not TICKER_RE.match(ticker):
            return {"ok": False, "reason": f"invalid ticker '{ticker}'"}
        item = _find(ct, ticker)
        if not item:
            return {"ok": False, "reason": f"{ticker} not in superlist/exitlist"}
        if item.current_plan and item.current_plan.mode == "wait_bid_offer":
            return {"ok": False, "reason": f"{ticker} wait_bid_offer — not ready"}
        if item.plan and _is_today(item.plan.updated_at, now) and item.plan.mode == mode:
            return {"ok": False, "reason": f"{ticker} duplicate plan today ({mode})"}
        if mode == "A" and (item.current_plan.mode if item.current_plan else "") == "buy_at_price":
            if ts.balance.buying_power <= 0:
                return {"ok": False, "reason": "buying_power<=0"}
        return {"ok": True, "ticker": ticker}
    # Mode A batch
    queue = []
    for lst in (ct.lists.superlist, ct.lists.exitlist):
        for it in lst:
            if not it.current_plan:
                continue
            if it.current_plan.mode not in ("buy_at_price", "sell_at_price"):
                continue
            if it.plan and _is_today(it.plan.updated_at, now) and it.plan.mode == "A":
                continue
            queue.append(it.ticker)
    if not queue:
        return {"ok": False, "reason": "empty queue"}
    buy_side = any(_is_buy_side(ct, t) for t in queue)
    if buy_side and ts.balance.buying_power <= 0:
        return {"ok": False, "reason": "buying_power<=0 (batch has buy-side)"}
    return {"ok": True, "queue": queue}

def _find(ct, ticker): ...
def _is_today(iso, now): ...
def _is_buy_side(ct, ticker): ...
```

- [ ] **Step 2: Tests.**
```python
def test_aggressiveness_off_aborts(self)
def test_invalid_ticker_aborts(self)               # e.g. "foo!"
def test_ticker_not_in_lists_aborts(self)
def test_wait_bid_offer_aborts(self)
def test_duplicate_same_mode_today_aborts(self)
def test_duplicate_different_mode_allowed(self)    # A yesterday, B today OK
def test_mode_a_buy_bp_zero_aborts(self)
def test_mode_b_single_ok(self)
def test_mode_a_batch_queue_built(self)
def test_mode_a_batch_empty_queue_aborts(self)
def test_mode_a_batch_sell_only_bp_zero_ok(self)   # no buy-side in queue
```

- [ ] **Step 3: Commit.**
```bash
python3 -m unittest tests.trader.test_l4_healthcheck -v
git add tools/trader/l4_healthcheck.py tests/trader/test_l4_healthcheck.py
git commit -m "l4_healthcheck: gates (spec #6 Task 8)"
```

---

## Task 9: Playbook + slash command

**Files:** `playbooks/trader/layer-4-tradeplan.md`, `.claude/commands/trade/tradeplan.md`.

- [ ] **Step 1: Write playbook.** Structure:

```
# Layer 4 — Trade Plan

Non-interactive. Single-ticker (arg) or batch (no arg).

## 1. Load context
- `ct = current_trade.load()`, `today = datetime.now(WIB).date()`
- Parse arg: `ticker = sys.argv[1].upper() if sys.argv[1:] else None`

## 2. Mode detect
- If ticker is None → Mode A batch
- Else check l3_buy_now_ledger.contains(ticker, today) AND layer_runs['l3'].last_run within 20m → Mode B; else Mode A single

## 3. Healthcheck
- `res = l4_healthcheck.check(ct, mode, ticker)` → abort with telegram warn if !ok
- Mode A batch: iterate `res['queue']`; Mode B: process single

## 4. Per-ticker loop
For each ticker t:
  a. `side = "buy" if item.current_plan.mode == "buy_at_price" else "sell"`
  b. Gather dims:
     - Mode A: `dim = l4_dim_gather.gather_structure(t)`
     - Mode B: `dim = gather_structure(t)` + `ob = gather_orderbook(t, "runtime/monitoring/orderbook_state")` + `note = gather_last_tape_note(t, "runtime/monitoring/notes/10m-{today}.jsonl")`
  c. Build ctx dict (regime/aggressiveness/bp/conf/details/narrative/structure/atr/etc.)
  d. Build prompt: `format_plan_prompt_a(ctx)` or `..._b(ctx)`
  e. Invoke Opus: `raw = claude_model.call_opus(prompt)`
  f. `parsed = parse_opus_plan_response(raw)` (handle abort)
  g. `sizing = size_plan(parsed['entry'], parsed['stop'], ts.balance.buying_power, ts.aggressiveness, ts.intraday_notch, side)`
  h. `plan_struct = build_plan_struct(t, parsed, sizing, mode, side, now_iso)`
  i. If abort → log reason, continue to next ticker
  j. Write back: item.plan = TradePlan(**plan_struct); item.current_plan.price = plan_struct['entry']; item.details = format_details_line(...)
  k. Accumulate event for telegram + daily note

## 5. Save state
- Update `layer_runs['l4']`: status=ok, last_run=now, note=f"planned {n_ok}, aborted {n_abort}, skipped {n_skip}"
- `current_trade.save(ct)` whitelist: `lists.superlist`, `lists.exitlist`, `layer_runs.l4`

## 6. Telegram + daily note
- Telegram: one msg per finalized plan via `format_telegram_event`
- Daily note: batch-mode → one block via `format_daily_note_block`; single-B → individual append

## 7. Exit
- stdout: JSON summary {mode, planned, aborted, skipped, tickers}
```

- [ ] **Step 2: Update slash command.**
```markdown
# /trade:tradeplan — L4 Trade Plan

Non-interactive. Single-ticker arg → Mode B (intraday sizing) OR Mode A single re-plan. No arg → Mode A batch over superlist/exitlist where current_plan.mode ∈ {buy_at_price, sell_at_price}.

**Playbook:** `playbooks/trader/layer-4-tradeplan.md`

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md`

**CRON (spec #8):** Mode A batch ~05:30 WIB Mon–Fri (after L2). Mode B triggered on-demand by L3 BUY-NOW popen.

**Guardrails:** writes per-ticker `plan` + `current_plan.price` + `details`, `layer_runs['l4']`. No writes to watchlist / regime / sectors / narratives / holdings / balance / aggressiveness. No order placement.
```

- [ ] **Step 3: Commit.**
```bash
git add playbooks/trader/layer-4-tradeplan.md .claude/commands/trade/tradeplan.md
git commit -m "L4 tradeplan playbook + slash trigger (spec #6 Task 9)"
```

---

## Task 10: Progress doc + INDEX + plan-complete tag

**Files:** `docs/revamp-progress.md`, `tools/INDEX.md`, `playbooks/trader/CLAUDE.md`, `skills/trader/CLAUDE.md`.

- [ ] **Step 1: `playbooks/trader/CLAUDE.md`** — L4 row:
  - `stub — spec #6` → `layer-4-tradeplan.md` | status `stub` → `live`

- [ ] **Step 2: `skills/trader/CLAUDE.md`** — add row: `| L4 Tradeplan | playbooks/trader/layer-4-tradeplan.md |`

- [ ] **Step 3: `docs/revamp-progress.md`:**
  - Add L4 tag to Used-by column: `api.py`, `market_structure.py`, `claude_model.py`, `daily_note.py`, `telegram_client.py`, `l3_buy_now_ledger.py`
  - `current_trade.py`: note `spec #6 added ListItem.plan + TradePlan`
  - Add 3 new rows: `l4_synth.py`, `l4_dim_gather.py`, `l4_healthcheck.py` (all live, spec #6)
  - Spec #6 status: `not started` → `in progress (plan-complete, pre-dry-run)`

- [ ] **Step 4: `tools/INDEX.md`** — add 3 new rows after L3 block. Tag existing L4 users.

- [ ] **Step 5: Full suite green.**
```bash
python3 -m unittest discover -v
```

- [ ] **Step 6: Commit + tag.**
```bash
git add docs/revamp-progress.md tools/INDEX.md playbooks/trader/CLAUDE.md skills/trader/CLAUDE.md
git commit -m "Progress doc + index: L4 tools used-by tags (spec #6 Task 10)"
git tag spec-6-plan-complete
```

---

## Task 11 (deferred) — manual dry-run

- Mode A: trigger after next L2 run (CRON wiring in spec #8, OR manual `claude -p /trade:tradeplan`)
- Mode B: trigger when L3 fires BUY-NOW during market hours
- Inspect: `runtime/current_trade.json` (plan field populated, details rewritten, current_plan.price = entry)
- Verify: Telegram event received, daily note appended

## Task 12 (deferred) — accept + tag

```bash
# after dry-run green
# flip revamp-progress.md spec #6 → "complete (dry-run passed YYYY-MM-DD)"
git commit -am "Spec #6 accepted — dry-run passed"
git tag spec-6-complete
```

---

## Summary

10 build tasks + 2 deferred. All TDD: fixtures first, pure helpers before playbook. Sizing + tick math entirely Python-side (Opus only touches entry/stop/TP floats + rationale). Two modes detected via L3 ledger recency; duplicate guard prevents same-day re-plan. New schema field `ListItem.plan: TradePlan` read by L5 (spec #7).
