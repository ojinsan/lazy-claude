# Spec #6 — L4 Trade Plan (Opus per-ticker sizing + entry/stop/TP)

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Prereqs:** spec #1 (core), #2 (L0), #3 (L1), #4 (L2), #5 (L3).

## 1. Scope & Trigger

- **Trigger:**
  - **Mode A (full plan)** — invoked after L2 run (CRON wiring in spec #8): `claude -p "/trade:tradeplan"` (no arg) → batch over `lists.superlist` where `current_plan.mode in {"buy_at_price","sell_at_price"}` AND `plan is None`.
  - **Mode B (sizing-only)** — invoked by L3 BUY-NOW async popen: `claude -p "/trade:tradeplan ADMR"` (single ticker).
- **Model:** Opus (reasoning matters — entry/stop/TP placement).
- **Writes:**
  - `lists.superlist[t].plan` (new `TradePlan` struct; see §7)
  - `lists.superlist[t].current_plan.price` = entry price (overwrites L2/L3 value)
  - `lists.superlist[t].details` ← one-line L4 summary (overwrites L2/L3 details)
  - `lists.exitlist[t]` same fields for `sell_at_price`
  - `layer_runs['l4']`
- **Does NOT write:** regime, sectors, narratives, aggressiveness, watchlist, filtered, holdings, balance. No order placement (L5).

## 2. Mode Detection

```
args = sys.argv[1:]  # from slash-command arg passthrough
if args:
    ticker = args[0].upper()
    # Mode B if L3 just fired BUY-NOW for this ticker today
    if l3_buy_now_ledger.contains(ticker, today) AND layer_runs['l3'].last_run within 20m:
        mode = "B"
    else:
        mode = "A"  # single-ticker Mode A (manual re-plan)
    process_one(ticker, mode)
else:
    # Batch Mode A: all buy/sell_at_price entries with no plan yet
    for item in superlist + exitlist:
        if item.current_plan.mode in {"buy_at_price","sell_at_price"} and item.plan is None:
            process_one(item.ticker, "A")
```

Duplicate guard: if `item.plan.updated_at` ≥ today start AND `item.plan.mode == mode` → skip.

## 3. Inputs

| Source | Field | Use |
|--------|-------|-----|
| `current_trade.json` | `trader_status.aggressiveness` | risk_pct tier: low=1%, med=2%, high=3%, off=abort |
| `current_trade.json` | `trader_status.balance.buying_power` | position cap |
| `current_trade.json` | `trader_status.holdings` | existing exposure + sell-side reference price |
| `current_trade.json` | `trader_status.intraday_notch` | -1 → shrink risk by 1 tier (Mode B only) |
| `current_trade.json` | `lists.{superlist,exitlist}[t]` | confidence, current_plan.mode, prior details |
| `trader/api.compute_indicators_from_price_data(t, limit=60)` | `atr_14` | stop-distance sanity check |
| `trader/market_structure.analyze_market_structure(t, days=30)` | `support`, `resistance`, `wyckoff_phase`, `last_swing_low` | entry zone + stop choice |
| `runtime/monitoring/orderbook_state/{t}.json` | `bids[0].price`, `offers[0].price`, `last_price` | Mode B entry reference (already-fresh from L3 cycle) |
| `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl` last entry | tape composite / spring / thick-wall | Mode B rationale context |

Mode A skips orderbook (pre-market, stale). Mode B reads orderbook snapshot (fresh from triggering L3 cycle).

## 4. Outputs

### 4.1 `current_trade` write-back

```json
{
  "lists": {
    "superlist": [{
      "ticker": "ADMR",
      "confidence": 82,
      "current_plan": {"mode": "buy_at_price", "price": 1855},
      "details": "L4-A: E 1855 | SL 1835 (1.1%) | T1 1950 (2.1R) | T2 2050 | 50 lots 9.25M/9.3%BP",
      "plan": {
        "entry": 1855, "stop": 1835,
        "tp1": 1950, "tp2": 2050,
        "lots": 50, "risk_idr": 100000,
        "mode": "A", "rationale": "…",
        "updated_at": "2026-04-22T05:45:12+07:00"
      }
    }]
  },
  "layer_runs": {"l4": {"status": "ok", "last_run": "...", "note": "planned 3 (A:2 B:1), skipped 1 (dup)"}}
}
```

### 4.2 Telegram (event per finalized plan)

```
[L4-{mode}] {ticker} {buy|sell}
E {entry} | SL {stop} ({stop_pct}%) | T1 {tp1} ({r1}R) | T2 {tp2}
Size {lots}lot ({idr}/{pct}%BP) | Conv {confidence}
{rationale_one_line}
```

Skip resend if re-plan same ticker within same day with entry/stop unchanged ±1 tick.

### 4.3 Daily note

Append per plan under `## L4 Trade Plan — {date}`. Batch mode → one append block per run (all tickers). Mode B → individual appends.

## 5. Sizing (Python-side, not Opus)

```python
TIER = {"low": 0.01, "med": 0.02, "high": 0.03, "off": None}

def size_plan(entry: float, stop: float, buying_power: float,
              aggressiveness: str, intraday_notch: int, side: str = "buy") -> dict:
    tier = TIER.get(aggressiveness.lower())
    if tier is None or buying_power <= 0:
        return {"abort": True, "reason": "aggressiveness=off or BP<=0"}
    if intraday_notch < 0:
        tier = max(tier - 0.01, 0.01)  # shrink one tier, floor 1%
    dist = abs(entry - stop)
    if dist <= 0:
        return {"abort": True, "reason": "zero stop distance"}
    risk_idr = buying_power * tier
    shares   = risk_idr / dist
    lots     = int(shares // 100)
    # cap: single-name ≤ 30% BP
    max_lots_cap = int((buying_power * 0.30) / (entry * 100))
    lots = min(lots, max_lots_cap)
    if lots <= 0:
        return {"abort": True, "reason": "sub-lot size"}
    return {"lots": lots, "risk_idr": round(lots * 100 * dist),
            "notional": round(lots * 100 * entry), "tier": tier}
```

### IDX tick table (verified against current fraksi harga)

```python
def get_tick(price: float) -> int:
    if price < 200:   return 1
    if price < 500:   return 2
    if price < 2000:  return 5
    if price < 5000:  return 10
    return 25

def round_to_tick(price: float, direction: str = "nearest") -> int:
    t = get_tick(price)
    if direction == "up":   return int(math.ceil(price / t) * t)
    if direction == "down": return int(math.floor(price / t) * t)
    return int(round(price / t) * t)
```

Rules:
- `buy_at_price` entry → round **down** (conservative fill bias).
- `sell_at_price` entry → round **up**.
- Stop → always round **down** for buy (wider stop), **up** for sell.
- TP → round **up** for buy (aspirational), **down** for sell.

## 6. Opus Prompt (Mode A)

```
You are L4 trade-plan synth for IDX ticker {ticker}. Output one trade plan as JSON.

Context:
- regime={regime}, aggressiveness={aggressiveness}, side={buy|sell}
- buying_power={bp_idr}, confidence={conf}/100
- prior details (L2): {details}
- narrative: {nar_snippet or "—"}
- structure: trend={trend}, wyckoff={wyckoff_phase}, support={support}, resistance={resistance}, last_swing_low={lsl}
- ATR(14)={atr}, last_close={close}, 60d_high={hi}, 60d_low={lo}

Rules:
- Buy: entry near support OR above last_swing_low, stop below structural invalidation (last_swing_low -1 tick OR support -0.5*ATR), TP1 ≥ 1.5R, TP2 ≥ 3R OR near resistance.
- Sell: mirror. Entry near resistance (buy-side book) or at break of support; stop above last_swing_high.
- Do NOT compute lot size — Python handles sizing.
- Round numbers as raw floats; Python applies tick rounding.

Output strict JSON:
{"entry": <float>, "stop": <float>, "tp1": <float>, "tp2": <float|null>, "rationale": "<≤180 chars>"}
```

## 7. Mode B Prompt (sizing-only)

```
You are L4 sizing-only synth for IDX ticker {ticker}. L3 just fired BUY-NOW.

Context:
- side=buy, confidence={conf}/100
- orderbook: best_bid={bb}, best_offer={bo}, last={last}
- tape: {composite_label} | thick_wall_buy={bool} | spring_confirmed={bool}
- structure: support={support}, last_swing_low={lsl}, ATR(14)={atr}
- intraday_notch={notch}

Rules:
- Entry = current best_offer (sweep) OR last+1 tick; Python will tick-round.
- Stop = last_swing_low - 1 tick. If dist > 1.5*ATR → abort (too loose; return {"abort": true, "reason": "..."}).
- TP1 = entry + 2*ATR (min 1.5R). TP2 = entry + 4*ATR OR resistance, whichever closer.

Output strict JSON:
{"entry": <float>, "stop": <float>, "tp1": <float>, "tp2": <float|null>, "rationale": "<≤140 chars>"}
OR {"abort": true, "reason": "<≤80 chars>"}
```

## 8. Healthcheck (pre-run gate)

Abort reasons (write `layer_runs['l4'].status='skipped'`, telegram warn):
- `aggressiveness == "off"` → kill-switch implied
- `buying_power <= 0` (Mode A buy batch)
- Empty queue (Mode A batch, nothing to plan)
- Ticker not in superlist/exitlist (Mode B single)
- `current_plan.mode == "wait_bid_offer"` (not ready for plan)

## 9. `current_trade.py` schema addition

```python
@dataclass
class TradePlan:
    entry: float
    stop: float
    tp1: float
    tp2: Optional[float] = None
    lots: int = 0
    risk_idr: float = 0
    mode: str = "A"              # "A" | "B"
    rationale: str = ""
    updated_at: str = ""

@dataclass
class ListItem:
    ticker: str
    confidence: int
    current_plan: Optional[CurrentPlan] = None
    details: str = ""
    plan: Optional[TradePlan] = None   # NEW
```

Back-compat: `_parse_list_item` treats missing `plan` key → `None`.

## 10. Guardrails

- No write to `watchlist`, `filtered`, `regime`, `sectors`, `narratives`, `holdings`, `balance`, `aggressiveness`.
- No order placement; `plan` struct is input for L5 only.
- Abort propagates as `layer_runs['l4'].status='error'` only on exception; `skipped` for planned aborts (aggressiveness=off, empty queue, etc.).
- Idempotency: duplicate-guard prevents re-plan same day same mode unless entry/stop changed.
- Ticker arg validation: `A-Z`, ≤6 chars, ASCII only (reject shell injection).

## 11. Task Breakdown (TDD, 10 tasks)

1. **Fixtures** — `tests/trader/fixtures/l4/`: structure_ADMR.json, indicators_ADMR.json, orderbook_ADMR_fresh.json, notes_10m_ADMR.json, opus_plan_A_approve.json, opus_plan_B_approve.json, opus_plan_B_abort.json, opus_malformed.json.
2. **`current_trade.py`** — add `TradePlan` + `ListItem.plan` field + parser + serializer. Back-compat test.
3. **`l4_synth.py`** — IDX tick math: `get_tick`, `round_to_tick(price, side, role)` where role ∈ {entry,stop,tp}. Full unit-test matrix for all price bands × sides × roles.
4. **`l4_synth.py`** — `size_plan(entry, stop, bp, aggressiveness, intraday_notch, side)` per §5. Tests: normal, notch-shrink, sub-lot, 30%-cap, zero-dist abort, off abort.
5. **`l4_synth.py`** — prompt builders `format_plan_prompt_a`, `format_plan_prompt_b`, parser `parse_opus_plan_response` (validates schema, accepts `{abort:true}`).
6. **`l4_synth.py`** — `build_plan_struct(ticker, raw, sizing, mode, now)` → `TradePlan`; formatters `format_details_line`, `format_telegram_event`, `format_daily_note_block`.
7. **`l4_dim_gather.py`** — Mode A: indicators + market_structure. Mode B: adds orderbook snapshot + last notes row. Graceful-degrade (missing files → skip that dim, mark context_missing).
8. **`l4_healthcheck.py`** — `check(ct, mode, ticker=None)` → all §8 gates.
9. **Playbook** — `playbooks/trader/layer-4-tradeplan.md`: arg-parse → healthcheck → mode detect → per-ticker loop (gather → opus → parse → size → write) → telegram + daily note → save. Slash command `.claude/commands/trade/tradeplan.md` rewrite (live).
10. **Progress doc + INDEX update + plan-complete tag** — `docs/revamp-progress.md` flips L4 stub → live; `tools/INDEX.md` adds 4 new rows; spec #6 status → `in progress (plan-complete, pre-dry-run)`. Tag `spec-6-plan-complete`.

Task 11 (deferred) — manual dry-run at next market session (Mode A batch post-L2, Mode B triggered by L3).
Task 12 (deferred) — accept + tag `spec-6-complete`.

## 12. CRON wiring (defer to spec #8)

- Mode A batch: `30m after L2 run` Mon–Fri (e.g. 05:30 WIB) — spec #8 CRON.
- Mode B: fires on-demand from L3 popen; no CRON needed.
- L5 reads `plan` field to place orders; spec #7.
