# Spec #4 — L2 Screening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build L2 screening layer: per-ticker full-judge via openclaude across 4 dims (price/wyckoff/RS/spring/vp, broker+SID+konglo, yesterday bid-offer, narrative) → deterministic promotion truth table → Opus final merge assigning `current_plan`. Writes `lists.superlist` + `lists.exitlist` only. Runs CRON 05:00 WIB, Mon–Fri. Always-send Telegram recap, daily note append.

**Architecture:** Same shape as L1 (spec #3) — pure-function helpers in `tools/trader/` for dim gather + synth validation + promotion truth table; playbook Markdown orchestrates sequential per-ticker openclaude calls + Opus merge. No AI inside gatherers — they return pre-computed facts only.

**Tech Stack:** Python 3.12 stdlib only (dataclasses, json, pathlib, datetime, unittest, unittest.mock). No pydantic, no pytest. Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`, `tools/_lib/daily_note.py`. Existing tools: `api.py` (get_eod_bars), `wyckoff.py`, `spring_detector.py`, `vp_analyzer.py`, `relative_strength.py`, `indicators.py` (ATR), `sid_tracker.py`, `broker_profile.py`, `konglo_loader.py`, `sb_screener_hapcu_foreign_flow.py`, `sb_screener_retail_avoider.py` (spec #3), `narrative.py`, `telegram_client.py`.

**Spec:** `docs/superpowers/specs/2026-04-21-trading-agents-revamp-spec-4-l2-screening.md`

---

## File Structure

**Create:**
- `tools/trader/l2_dim_gather.py` — 4 pure functions: `gather_price(t, sector)`, `gather_broker(t, hapcu_cache, retail_cache, l1_sectors)`, `gather_book(t)`, `gather_narrative(t, narratives)`. Each returns a compact dict. No AI. Graceful degrade.
- `tools/trader/l2_synth.py` — pure helpers: `promotion_decision`, `format_judge_prompt`, `parse_judge_response`, `format_merge_prompt`, `parse_merge_response`, `format_telegram_recap`. No AI, no I/O.
- `tools/trader/l2_healthcheck.py` — pre-run gate: watchlist exists + (holdings OR watchlist non-empty) + yesterday hapcu+retail caches present. Returns `{ok, reason}`.
- `playbooks/trader/layer-2-screening.md` — Claude-executed playbook (9 steps per spec §6).
- `tests/trader/test_l2_dim_gather.py`
- `tests/trader/test_l2_synth.py`
- `tests/trader/test_l2_healthcheck.py`
- `tests/trader/fixtures/l2/eod_bars_ADMR.json`
- `tests/trader/fixtures/l2/eod_bars_BUMI.json`
- `tests/trader/fixtures/l2/hapcu_cache.json`
- `tests/trader/fixtures/l2/retail_cache.json`
- `tests/trader/fixtures/l2/sid_ADMR.json`
- `tests/trader/fixtures/l2/broker_profile_ADMR.json`
- `tests/trader/fixtures/l2/orderbook_state_ADMR.json` (copy of real 10m snapshot)
- `tests/trader/fixtures/l2/notes_10m_latest.jsonl`
- `tests/trader/fixtures/l2/narratives.json`
- `tests/trader/fixtures/l2/judge_response_valid.json`
- `tests/trader/fixtures/l2/judge_response_malformed.json`
- `tests/trader/fixtures/l2/merge_response.json`

**Modify:**
- `.claude/commands/trade/screening.md` — replace stub with thin trigger pointing at `playbooks/trader/layer-2-screening.md`.
- `playbooks/trader/CLAUDE.md` — flip L2 row stub → live.
- `skills/trader/CLAUDE.md` — add L2 playbook row to active-layer table.
- `docs/revamp-progress.md` — fill `Used-by-layer=L2` for: `api.py` (get_eod_bars), `wyckoff.py`, `spring_detector.py`, `vp_analyzer.py`, `relative_strength.py`, `indicators.py`, `sid_tracker.py`, `broker_profile.py`, `konglo_loader.py`, `narrative.py`, `sb_screener_hapcu_foreign_flow.py`, `sb_screener_retail_avoider.py`, `telegram_client.py`. Add rows for new `l2_dim_gather.py`, `l2_synth.py`, `l2_healthcheck.py`.

---

## Task 1: Fixtures + package markers

**Files:** `tests/trader/fixtures/l2/*` (12 files).

- [ ] **Step 1:** Generate plausible fixtures. Shapes must match real producers:
  - `eod_bars_ADMR.json`: 60 rows of `{date, open, high, low, close, volume}`. Fabricate an accumulation pattern (narrowing range, pickup on the last 5 bars).
  - `eod_bars_BUMI.json`: 60 rows of a distribution pattern (lower highs, volume climax).
  - `hapcu_cache.json`: `{date, calcs: [{ticker, hapcu_net_buy, foreign_net_buy, days_in_window}]}` — matches `sb_screener_hapcu_foreign_flow` shape.
  - `retail_cache.json`: `{date, tickers: [{ticker, retail_net_sell, smart_net_buy, ratio}]}` — spec #3 producer shape.
  - `sid_ADMR.json`: 5 rows of `{date, net_shares, direction}`.
  - `broker_profile_ADMR.json`: `{ticker, top_brokers: [{code, role, net}]}`.
  - `orderbook_state_ADMR.json`: copy real snapshot from `runtime/monitoring/orderbook_state/ADMR.json`.
  - `notes_10m_latest.jsonl`: one JSONL line per `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl` shape — last entry with ADMR + BUMI records.
  - `narratives.json`: 3 `Narrative` dicts matching spec #1 schema — includes ADMR, excludes BUMI.
  - `judge_response_valid.json`: `{"scores": {"price":"strong","broker":"strong","book":"weak","narrative":"strong"}, "rationale": "..."}`.
  - `judge_response_malformed.json`: missing `broker` key.
  - `merge_response.json`: `{"ADMR": {"current_plan":"buy_at_price","details":"..."}, "BUMI": {"current_plan":"sell_at_price","details":"..."}}`.

- [ ] **Step 2: Verify** parseable: `python3 -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/trader/fixtures/l2/*.json')]"` plus one `jsonl` read loop.

- [ ] **Step 3: Commit:** `git add tests/trader/fixtures/l2/ && git commit -m "Add L2 test fixtures"`

---

## Task 2: `l2_synth.py` — pure validators + truth table + recap

**Files:**
- Create: `tools/trader/l2_synth.py`
- Create: `tests/trader/test_l2_synth.py`

Helpers:
- `promotion_decision(scores: dict[str,str], is_holding: bool) -> Literal['superlist','exitlist','drop']` — implements PRD truth table (≥1 superstrong OR ≥3 strong OR ≥2 strong + 0 redflag → superlist; holding + ≥2 redflag → exitlist; else drop).
- `format_judge_prompt(ticker: str, dims: dict, context: dict) -> str` — injects all 4 dim blobs + regime + sectors + aggressiveness + is_holding flag. Includes explicit label enum guardrails in header.
- `parse_judge_response(raw: str) -> tuple[dict[str,str], str]` — strips fences, parses `{scores: {price,broker,book,narrative}, rationale}`. Validates enum membership. Raises on malformed.
- `format_merge_prompt(promoted: list[dict], exits: list[dict], holdings: list[str], regime: str) -> str` — asks Opus to assign `current_plan` per ticker + tidy `details` (≤120 chars).
- `parse_merge_response(raw: str) -> dict[str, dict]` — returns `{ticker: {current_plan, details}}`. Validates `current_plan ∈ {buy_at_price, sell_at_price, wait_bid_offer}`.
- `format_telegram_recap(superlist, exitlist, n_judged, regime, prev_superlist_count, now_hhmm) -> str` — empty-superlist path (`L2: 0 promoted (N judged, regime=X)`) + full path with top-3 per bucket.

- [ ] **Step 1: Write failing tests** covering each helper:
  - promotion_decision: 16-case truth table (each combo of superstrong/strong/weak/redflag counts + holding flag) + edge: all weak → drop.
  - parse_judge_response: valid fixture, malformed fixture (missing key), fences present, fences absent, unknown enum label raises.
  - format_judge_prompt: contains ticker, all 4 dim keys, regime literal, aggressiveness string, is_holding flag.
  - parse_merge_response: valid fixture, invalid current_plan raises.
  - format_telegram_recap: empty path + full path + caveman-friendly line budget.

- [ ] **Step 2: Verify tests fail:** `python3 -m unittest tests.trader.test_l2_synth -v`

- [ ] **Step 3: Implement** `tools/trader/l2_synth.py`. Keep ≤300 lines. No AI. No I/O.

- [ ] **Step 4: Verify tests pass.**

- [ ] **Step 5: Commit:** `git add tools/trader/l2_synth.py tests/trader/test_l2_synth.py && git commit -m "Add l2_synth pure validators + promotion truth table + recap"`

---

## Task 3: `l2_dim_gather.py` — 4 dim gatherers

**Files:**
- Create: `tools/trader/l2_dim_gather.py`
- Create: `tests/trader/test_l2_dim_gather.py`

Signatures:
- `gather_price(ticker: str, sector: str | None) -> dict` — calls `api.get_eod_bars(ticker, days=60)`, `wyckoff.classify(bars)`, `spring_detector.detect(ticker)`, `vp_analyzer.classify(ticker, '1d')`, `relative_strength.rank(ticker, sector)`, computes 14-ATR. Returns `{bars_len, last_close, wyckoff_phase, spring_hit, spring_confidence, vp_state, rs_rank, atr, judge_floor, vp_redflag}`. `judge_floor='strong'` if spring hit with confidence ≥ med. `vp_redflag=True` if vp_state in {weak_rally, distribution} AND not spring_hit.
- `gather_broker(ticker, hapcu_cache, retail_cache, l1_sectors) -> dict` — look up ticker in hapcu+retail, fetch `sid_tracker.get(ticker, days=5)` + `broker_profile.lookup(ticker)` + `konglo_loader.group_for(ticker)`. Returns merged dict + `konglo_in_l1_sectors: bool`.
- `gather_book(ticker) -> dict` — reads `runtime/monitoring/orderbook_state/{ticker}.json` (last snapshot) + last matching entry in `runtime/monitoring/notes/10m-YYYY-MM-DD.jsonl` (latest file available). Returns `{last_price, bid_walls_top3, offer_walls_top3, pressure_side, stance, score, summary}`.
- `gather_narrative(ticker, narratives) -> dict` — returns `{hit: bool, content: str|None, source: str|None, confidence: int|None, thesis_snippet: str|None}`. Loads `vault/thesis/{ticker}.md` via `narrative.py` if present.

All return `{"status":"unavailable", "reason":...}` on gather failure. No exceptions escape.

- [ ] **Step 1: Write failing tests** using L2 fixtures. Mock underlying tool calls via `unittest.mock.patch`. Cover: spring hit promotes judge_floor, vp_redflag logic, missing ticker → unavailable shape, konglo-in-sectors flag flip, book gather missing state file.

- [ ] **Step 2: Verify fail.**

- [ ] **Step 3: Implement.** Each function ≤50 lines. No logic beyond data shaping + degrade.

- [ ] **Step 4: Verify pass** + live smoke: `python3 -c "from tools.trader.l2_dim_gather import gather_price, gather_book; print(gather_price('BBRI','banking')); print(gather_book('BBRI'))"`.

- [ ] **Step 5: Commit.**

---

## Task 4: `l2_healthcheck.py` — pre-run gate

**Files:**
- Create: `tools/trader/l2_healthcheck.py`
- Create: `tests/trader/test_l2_healthcheck.py`

`check(ct_prior, hapcu_path, retail_path) -> {ok: bool, reason: str}`:
- ok=False if `ct_prior.lists.watchlist` empty AND `ct_prior.trader_status.holdings` empty.
- ok=False if L1 layer_run missing or older than 6 hrs (stale upstream).
- ok=False if hapcu_cache missing AND retail_cache missing (need at least one broker-flow source).
- Otherwise ok=True.

- [ ] **Step 1: Write failing tests** — 4 branch coverage.
- [ ] **Step 2: Verify fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Verify pass.**
- [ ] **Step 5: Commit.**

---

## Task 5: Playbook `layer-2-screening.md`

**Files:**
- Create: `playbooks/trader/layer-2-screening.md`

Mirror L1 structure (spec §6 9-step outline). Key details:

1. Load `ct.load()`; extract watchlist + holdings + narratives + regime + sectors + aggressiveness.
2. L2 healthcheck gate — abort + telegram on `!ok`.
3. Build dedup universe preserving watchlist order, appending holdings-only tickers.
4. Fetch caches: hapcu (load yesterday JSON or run fresh), retail (same). Fail-soft `{}`.
5. Sequential per-ticker loop:
   - Gather 4 dims.
   - Build judge prompt.
   - `claude_model.run(prompt, model="openclaude", fallback="opus")`.
   - Parse scores; 1 retry on parse fail with error appended; else fall back `{all: "weak"}`.
   - Stash `{ticker: (scores, rationale, is_holding)}`.
6. Apply `promotion_decision` per ticker → split into superlist/exitlist/drop.
7. Build merge prompt for Opus. Parse. Fallback `current_plan=wait_bid_offer` on any merge fail.
8. Commit: `ct.lists.superlist = [...]`, `ct.lists.exitlist = [...]`. `ct.save(layer='l2', status='ok', note=...)`.
9. Daily note append + Telegram recap + `runtime/history/YYYY-MM-DD/l2-HHMM.json` snapshot.

- [ ] **Step 1:** Draft playbook one pass.
- [ ] **Step 2:** Verify every `from X import Y` in playbook matches real exports (`grep`).
- [ ] **Step 3:** Commit.

---

## Task 6: Replace `/trade:screening` stub + CLAUDE.md flips

**Files:**
- Modify: `.claude/commands/trade/screening.md` — mirror `/trade:insight` thin-trigger shape.
- Modify: `playbooks/trader/CLAUDE.md` — L2 row stub → live.
- Modify: `skills/trader/CLAUDE.md` — add L2 playbook row.

- [ ] **Step 1:** Edit all three.
- [ ] **Step 2:** `grep -n "L2" playbooks/trader/CLAUDE.md skills/trader/CLAUDE.md`.
- [ ] **Step 3:** Commit.

---

## Task 7: Progress-doc + INDEX updates

**Files:**
- Modify: `docs/revamp-progress.md` — fill Used-by-layer=L2 for listed tools; add new-tool rows; flip spec #4 row to in-progress.
- Modify: `tools/INDEX.md` — add l2_dim_gather, l2_synth, l2_healthcheck entries.

- [ ] **Step 1:** Edit.
- [ ] **Step 2:** Commit.

---

## Task 8: Full test suite + smoke imports + plan-tag

- [ ] `python3 -m unittest discover tests -v` — all green.
- [ ] Smoke imports: `python3 -c "from tools.trader import l2_dim_gather, l2_synth, l2_healthcheck"`.
- [ ] Tag: `git tag spec-4-plan-complete`.

---

## Task 9: Manual dry-run (acceptance)

- [ ] Invoke `/trade:screening` interactively after L0 + L1 have run same day. Expected:
  - L2 healthcheck passes.
  - Sequential judge loop runs over universe (watchlist ∪ holdings).
  - Opus merge assigns `current_plan` per promoted name.
  - `current_trade.json` version bumps; `lists.superlist` + `lists.exitlist` written; NO write to watchlist/regime/sectors/narratives/holdings/balance/aggressiveness.
  - `vault/daily/YYYY-MM-DD.md` gets `### L2 — HH:MM` section.
  - Telegram recap arrives.
  - `runtime/history/YYYY-MM-DD/l2-HHMM.json` snapshot exists.
- [ ] If green: flip spec #4 in progress doc → `complete (dry-run passed YYYY-MM-DD)`; tag `spec-4-complete`.

---

## Self-Review Notes

- **Per-ticker rate**: sequential openclaude calls honor `claude_api` token bucket. Universe ~15–20 tickers → ~15–20 calls. Budget OK.
- **Openclaude failure mode**: fallback is Opus (reversed vs L1). If both fail → dim scores default `weak` → ticker drops silently. Log loudly per-ticker fall-through count; abort layer if >50% fall-through.
- **Orderbook state freshness**: last 10m snapshot could be multi-day old if market closed. Gate on snapshot `ts` within 24hr; else treat as `unavailable`.
- **Konglo loader**: confirm `konglo_loader.group_for(ticker)` returns a group string matching `trader_status.sectors` taxonomy. If mismatch, `konglo_in_l1_sectors` will always be False silently. Add a one-shot alignment check during Task 3 smoke.
- **Spring confidence threshold**: use `{"med","high"}` → `judge_floor='strong'` (matches archived override). Low-confidence spring → no floor.
- **Dry-run timing**: L2 needs L1 done same day; invoke L1 first if stale.
