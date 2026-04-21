# Spec #4 — L2 Screening (4-dim per-ticker judge + Opus merge)

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Spec #1 (prereq):** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-1-core-design.md`
**Spec #2 (prereq):** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`
**Spec #3 (prereq):** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-3-l1-insight.md`

## 1. Scope & Trigger

- **Trigger:** CRON 05:00 WIB (Mon–Fri) → `claude /trade:screening`.
- **Upstream:** L0 (04:45) sets `holdings`+`aggressiveness`; L1 (04:00) sets `watchlist`+`narratives`+`regime`+`sectors`.
- **Model:** **openclaude per-ticker serial full-judge** (all 4 dims in one call per ticker), **Opus for final merge + current_plan assignment**.
- **Writes:** `lists.superlist` (promoted), `lists.exitlist` (holdings ≥2 redflags). Updates `layer_runs['l2']`.
- **Does NOT write:** any `trader_status` field (L0/L1), `lists.watchlist` (L1), `lists.filtered` (reserved). No order writes.

Universe = `lists.watchlist` ∪ `trader_status.holdings` (no cap — PRD §L2).

## 2. Inputs

| Dim | Source | Purpose |
|-----|--------|---------|
| 1. Price / volume / Wyckoff | `tools/trader/api.py::get_eod_bars(ticker, days=60)` + `wyckoff.py::classify(bars)` + `spring_detector.py::detect(ticker)` + `vp_analyzer.py::classify(ticker, '1d')` + `relative_strength.py::rank(ticker, sector)` + `indicators.py` (ATR) | 60-day structure: trend, Wyckoff phase, spring/upthrust, vol-price state, sector RS rank, vol surge. Spring hit → judge floor = `strong`; `vp_state in {weak_rally, distribution}` without spring offset → redflag candidate |
| 2. Broker + SID | yesterday's HAPCU row from `sb_screener_hapcu_foreign_flow.py` (cache), retail-avoider from `sb_screener_retail_avoider.py` (cache), `sid_tracker.py::get(ticker, days=5)`, `broker_profile.py::lookup(ticker)`, `konglo_loader.group_for(ticker)` cross-checked vs `trader_status.sectors` | smart/retail net flow direction, SID add/reduce, top-broker identity, konglo-group alignment with today's L1 sector tilt |
| 3. Yesterday tx / bid-offer | `runtime/monitoring/orderbook_state/{TICKER}.json` (last 10m snapshot ≈15:50 WIB close) + last entry in `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl` for the ticker | bid/offer wall structure, stance/score from L3 10m cycle, whale-tick counts |
| 4. Narrative | `trader_status.narratives[i]` where `ticker == t` (if present) + `narrative.py::load(ticker)` thesis file | thematic fit with today's regime + sector tilt |
| Context | `trader_status.{regime, sectors, aggressiveness}`, holdings flag per ticker | scoring conditioning; holdings get exit-oriented judge |

Prefetch/cache pattern: each dim has a pure Python data-gather function invoked by the playbook **once per ticker sequentially** (no global prefetch — simpler, bounded by per-ticker rate limit already).

## 3. Outputs

### 3.1 `current_trade` fields

```json
{
  "lists": {
    "superlist": [
      {
        "ticker": "ADMR",
        "confidence": 82,
        "current_plan": "buy_at_price",
        "details": "3 strong dims (price/broker/narrative). Buy 1855 support, stop 1835. HAPCU +1.2T, SID +5d streak. Coal theme aligned."
      }
    ],
    "exitlist": [
      {
        "ticker": "BUMI",
        "confidence": 72,
        "current_plan": "sell_at_price",
        "details": "2 redflags (price/broker). Sell 240 break, cover loss 5%. Smart-money exiting."
      }
    ]
  },
  "layer_runs": {
    "l2": {
      "status": "ok",
      "last_run": "2026-04-22T05:18:42+07:00",
      "note": "judged 14 (watchlist 11 + holdings 7 dedup), promoted 3, exit 1, model=openclaude+opus"
    }
  }
}
```

### 3.2 Promotion rules (PRD bible)

Per ticker scoring across 4 dims, each ∈ `{redflag, weak, strong, superstrong}`:

| Condition | Destination |
|-----------|-------------|
| ≥1 `superstrong` | superlist |
| ≥3 `strong` | superlist |
| ≥2 `strong` AND 0 `redflag` | superlist |
| Holding AND ≥2 `redflag` | exitlist |
| Otherwise | dropped (not written) |

Holdings are ALWAYS judged even if not in watchlist (L2 is last gate before stop-loss review at L4).

### 3.3 `current_plan` assignment (Opus merge step)

| Input signal | `current_plan` |
|--------------|----------------|
| Dim-3 reads "clean above bid wall, whales parked below" | `wait_bid_offer` (observe book intraday first) |
| Dim-3 reads "whale bid at support, tape confirmed" + dim-1 accumulation | `buy_at_price` |
| Exitlist entries OR dim-1 distribution + dim-2 smart-money out | `sell_at_price` |

Fallback: if Opus merge fails → write raw superlist with `current_plan=wait_bid_offer`, log warning, continue.

### 3.4 Daily note + Telegram

- Daily note `### L2 — HH:MM`: regime recap, superlist/exitlist counts, top 3 promoted with 1-line details.
- Telegram: always-send. Empty superlist case → `L2: 0 promoted (N judged, regime=X)`.

## 4. Guardrails

- No writes to `trader_status` or `lists.watchlist`. Validated by `current_trade.save(layer='l2')` merge logic (spec #1 §4.3).
- `lists.filtered` left untouched (reserved for future use).
- On any fatal error (dim-gather, model failure both paths, parse fail after 1 retry): keep prior `lists.superlist`/`exitlist`, set `layer_runs['l2'].status='error'`, send Telegram abort.
- Rate limit: honor `claude_api` token bucket in `_lib/ratelimit.py`. Sequential per-ticker already bounds call rate; no batch parallel.
- Idempotent: rerunning same day overwrites superlist/exitlist with new judgment (not append).

## 5. New code

All new files under `tools/trader/` or `tools/_lib/`:

| File | Purpose |
|------|---------|
| `tools/trader/l2_dim_gather.py` | 4 pure functions, each returning a compact dict for the prompt; graceful-degrade on missing data (`{"status": "unavailable", "reason": ...}`) → judge dim falls back to `weak`. <br>• `gather_price(t, sector)` — merges `get_eod_bars(60)`, `wyckoff.classify`, `spring_detector.detect` (bool + confidence), `vp_analyzer.classify('1d')`, `relative_strength.rank(t, sector)`, ATR. Emits `{spring_hit: bool, vp_state: str, rs_rank: int, wyckoff_phase: str, ...}` as pre-computed facts — judge sees facts, not raw bars. <br>• `gather_broker(t, hapcu_cache, retail_cache)` — merges hapcu row + retail-avoider row + `sid_tracker.get(days=5)` + `broker_profile.lookup` + `konglo_loader.group_for(t)` with boolean `konglo_in_l1_sectors` flag. <br>• `gather_book(t)` — reads `runtime/monitoring/orderbook_state/{t}.json` (last 10m snapshot) + last entry of `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl` for ticker. <br>• `gather_narrative(t, narratives)` — hit/miss in `trader_status.narratives` + optional `vault/thesis/{t}.md` load via `narrative.py`. |
| `tools/trader/l2_synth.py` | Pure helpers: `promotion_decision(scores: dict[str,str]) -> Literal['superlist','exitlist','drop']`, `format_judge_prompt(ticker, dims, context)`, `parse_judge_response(raw) -> ({dim: label}, rationale)`, `format_merge_prompt(judgments, holdings, regime)`, `format_telegram_recap(superlist, exitlist, n_judged, regime)`. All unit-testable. |
| `tools/trader/l2_healthcheck.py` | Pre-run check: watchlist exists AND (holdings exist OR watchlist non-empty) AND cached hapcu/retail for yesterday present. Returns `{ok, reason}`. Abort if `!ok`. |
| `playbooks/trader/layer-2-screening.md` | 9-step combined skill+workflow (mirrors L1 shape). |
| `.claude/commands/trade/screening.md` | Thin trigger loading playbook. |

No Go backend changes.

## 6. Playbook outline (`playbooks/trader/layer-2-screening.md`)

1. Load `current_trade` (spec #1). Extract `watchlist`, `holdings`, `narratives`, `regime`, `sectors`, `aggressiveness`.
2. L2 healthcheck: `l2_healthcheck.check()`. Stale / missing → abort + telegram.
3. Build dedup universe: `set(watchlist) ∪ set(holdings_tickers)` preserving watchlist order, then appending holdings-only tickers.
4. Fetch yesterday caches: `hapcu_cache = sb_screener_hapcu_foreign_flow.load_latest()` + `retail_cache = sb_screener_retail_avoider.run(date=YESTERDAY)`. Fail-soft to `{}`.
5. For each ticker in universe (sequential):
   - `dims = {1: gather_price(t, primary_sector_for(t)), 2: gather_broker(t, hapcu, retail), 3: gather_book(t), 4: gather_narrative(t, narratives)}`
   - `prompt = l2_synth.format_judge_prompt(t, dims, context)`
   - `raw = claude_model.run(prompt, model='openclaude', fallback='opus')`
   - `scores, rationale = l2_synth.parse_judge_response(raw)` — single retry on parse fail; if still fails → `{dim: 'weak'}` fallback
   - Track `{ticker: (scores, rationale, is_holding)}`
6. `promotion_decision(scores)` per ticker → bucket into superlist / exitlist / drop.
7. Opus merge: `format_merge_prompt(promoted, exits, holdings, regime)` → Opus returns `{ticker: current_plan}` + refined details. Fallback `wait_bid_offer` on merge fail.
8. `ct.save(layer='l2', status='ok', note=...)` — only touches `lists.superlist`, `lists.exitlist`.
9. Daily note append + Telegram recap + snapshot `runtime/history/YYYY-MM-DD/l2-HHMM.json`.

## 7. Validation

### 7.1 Unit tests (new `tests/trader/test_l2_synth.py`)

- `promotion_decision`: 16-case truth table covering PRD rules + holding flag edge cases.
- `parse_judge_response`: strips fences, handles `{dim, label, reason}` shape, errors on missing dims.
- `format_judge_prompt`: contains ticker, all 4 dim blobs, regime, holding flag.
- `format_telegram_recap`: empty superlist path + full path.

### 7.2 Fixture tests (`tests/trader/test_l2_dim_gather.py`)

Static JSON fixtures for `get_eod_bars`, hapcu/retail caches, orderbook_state snapshot, narratives.
- `gather_price`: wyckoff + spring + vp_state + rs_rank + ATR populated, spring-hit fixture promotes `judge_floor='strong'`, `weak_rally` without spring flags `vp_redflag=True`.
- `gather_broker`: merges hapcu+retail+sid+broker_profile+konglo into single dict; `konglo_in_l1_sectors` true when group ∈ `trader_status.sectors`.
- `gather_book`: reads last orderbook_state + last 10m note entry. Missing ticker → `unavailable`.
- `gather_narrative`: hit / miss.

### 7.3 Integration dry-run (Task 9)

Real run against current watchlist (5–15) + holdings (7). Accept criteria:
- `layer_runs['l2'].status == 'ok'`
- `lists.superlist` written, `lists.exitlist` written (possibly empty)
- No write to `watchlist`, `regime`, `sectors`, `narratives`, `holdings`, `balance`, `aggressiveness`
- Telegram recap sent
- Daily note has `### L2 — HH:MM` section
- Snapshot in `runtime/history/2026-04-22/`

## 8. Task breakdown

| # | Task | Tests first | Files |
|---|------|-------------|-------|
| 1 | L2 fixtures | — | `tests/trader/fixtures/l2_*` |
| 2 | `l2_synth.py` pure helpers | yes | `tools/trader/l2_synth.py` + `tests/trader/test_l2_synth.py` |
| 3 | `l2_dim_gather.py` 4 gatherers | yes | `tools/trader/l2_dim_gather.py` + `tests/trader/test_l2_dim_gather.py` |
| 4 | `l2_healthcheck.py` | yes | `tools/trader/l2_healthcheck.py` + test |
| 5 | Playbook `layer-2-screening.md` + slash | — | `playbooks/trader/layer-2-screening.md`, `.claude/commands/trade/screening.md` |
| 6 | Progress-doc + INDEX | — | `docs/revamp-progress.md`, `tools/INDEX.md` |
| 7 | Plan-complete tag | — | `spec-4-plan-complete` |
| 8 | Manual dry-run | — | `runtime/history/YYYY-MM-DD/l2-HHMM.json` |
| 9 | Accept + tag | — | `spec-4-complete` |

## 9. Out of scope

- `lists.filtered` — reserved for a future pre-screen stage.
- Intraday L2 re-runs — daily 05:00 only; L3 handles intraday state.
- Trade plans (sizing, stop placement) — belong to L4.
- Order writes — belong to L5.

## 10. Acceptance

Ship spec #4 when:
- All unit+fixture tests green.
- Dry-run writes superlist/exitlist with Opus-assigned `current_plan`, preserves all L0/L1 fields.
- Telegram recap received.
- Progress-doc updated; `spec-4-complete` tagged.
