# Spec #3 — L1 Insight & Context Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build L1 insight-synthesis layer: two mechanical Python helpers (healthcheck + retail-avoider screener) + pure-function L1 synth helpers + Claude-executed playbook running at CRON 04:00 WIB. Writes `trader_status.regime`, `trader_status.sectors`, `trader_status.narratives`, `lists.watchlist` to `current_trade.json`; appends daily note; always-send Telegram recap.

**Architecture:** Same pattern as L0 (spec #2) — thin helpers in `tools/trader/` for mechanical data reshape + validation; playbook Markdown in `playbooks/trader/layer-1-insight.md` orchestrates I/O, RAG calls, broker-flow fetches, macro pulls, Opus synthesis, validation retry budget, conditional abort. L1-A healthcheck gate runs first; stale → hard abort.

**Tech Stack:** Python 3.12 stdlib only (dataclasses, json, pathlib, datetime, unittest, unittest.mock). No pydantic, no pytest. Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`, `tools/_lib/daily_note.py` (spec #2). Existing tools: `api.py` (rag_search, get_insights), `macro.py`, `catalyst_calendar.py`, `overnight_macro.py`, `sb_screener_hapcu_foreign_flow.py`, `fund_manager_client.py`, `telegram_client.py`, `stockbit_auth.py`.

**Spec:** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-3-l1-insight.md`

---

## File Structure

**Create:**
- `tools/trader/l1a_healthcheck.py` — queries `:8787` for most-recent insight timestamp; returns `{fresh: bool, last_seen_minutes_ago: int, threshold_minutes: 120}`.
- `tools/trader/sb_screener_retail_avoider.py` — wraps Stockbit `/order-trade/broker/activity` fetch + retail-broker-code filter + ratio calc. Pure fetch + reshape.
- `tools/trader/l1_synth.py` — pure helpers: watchlist-pool union, narrative-anchor validation, regime literal validation, sectors/narratives count validation. No AI, no I/O.
- `playbooks/trader/layer-1-insight.md` — Claude-executed playbook (step-by-step, prompt template, tool-call examples).
- `tests/trader/test_l1a_healthcheck.py`
- `tests/trader/test_l1_retail_avoider.py`
- `tests/trader/test_l1_synth.py`
- `tests/trader/test_l1_e2e.py` — optional integration (mocked I/O).
- `tests/trader/fixtures/l1/rag_top_tickers.json`
- `tests/trader/fixtures/l1/rag_empty.json`
- `tests/trader/fixtures/l1/broker_flow_hapcu.json`
- `tests/trader/fixtures/l1/broker_flow_retail_avoider.json`
- `tests/trader/fixtures/l1/macro_overnight.json`
- `tests/trader/fixtures/l1/catalyst_today.json`
- `tests/trader/fixtures/l1/fund_manager_watchlist.json`
- `tests/trader/fixtures/l1/insight_recent_fresh.json`
- `tests/trader/fixtures/l1/insight_recent_stale.json`
- `tests/trader/fixtures/l1/broker_activity_raw.json` — raw `/order-trade/broker/activity` response sample for retail-avoider parser test.

**Modify:**
- `.claude/commands/trade/insight.md` — replace stub with thin trigger (model: `playbooks/trade:insight` calls `playbooks/trader/layer-1-insight.md`, mirroring `trade:portfolio`).
- `playbooks/trader/CLAUDE.md` — flip L1 row from stub → live.
- `skills/trader/CLAUDE.md` — add L1 playbook row to active-layer table.
- `docs/revamp-progress.md` — fill `Used-by-layer=L1` for: `api.py`, `macro.py`, `catalyst_calendar.py`, `overnight_macro.py`, `narrative.py`, `sb_screener_hapcu_foreign_flow.py`, `fund_manager_client.py`, `telegram_client.py`, `stockbit_auth.py`. Add rows for new `l1a_healthcheck.py`, `sb_screener_retail_avoider.py`, `l1_synth.py`. Add row under `tools/_lib/*.py` already covered. Add external-services row for `services/telegram-scraper/` (L1-A systemd).

---

## Task 1: Fixtures + package markers

**Files:**
- Create: `tests/trader/fixtures/l1/*.json` (10 files listed above).
- Create (if missing): `tests/trader/fixtures/l1/__init__.py` (empty marker — optional; only if test discovery needs it).

- [ ] **Step 1:** Write plausible sample data for each fixture. Shapes must match the real producers:
  - `rag_top_tickers.json`: list of `{ticker, confidence, source_insights, top_theme}` rows — at least 8 entries spanning 2–3 themes.
  - `rag_empty.json`: `{"results": []}` or whatever `api.rag_search` returns on empty.
  - `broker_flow_hapcu.json`: list of `{ticker, hapcu_net_buy, foreign_net_buy, days_in_window}` rows — include at least 3 names with strong smart-money net buy.
  - `broker_flow_retail_avoider.json`: `{date, tickers: [{ticker, retail_net_sell, smart_net_buy, ratio}]}` — same schema the new screener will produce.
  - `macro_overnight.json`: `{dxy, us10y, wti, ihsg_prev_close, foreign_net_3d}`.
  - `catalyst_today.json`: `[{date, type, tickers, description}]` — Fed/BI/earnings sample.
  - `fund_manager_watchlist.json`: list of `{ticker, source: 'lark'|'sqlite', note}` — Lark + SQLite merged shape from `fund_manager_client.get_watchlist()`.
  - `insight_recent_fresh.json`: `{last_insight_at: "<10 min ago ISO>"}`.
  - `insight_recent_stale.json`: `{last_insight_at: "<180 min ago ISO>"}`.
  - `broker_activity_raw.json`: raw Stockbit `/order-trade/broker/activity` response. Copy shape from live call via temporary probe script.

- [ ] **Step 2: Verify** fixtures parse: `python3 -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/trader/fixtures/l1/*.json')]"`.

- [ ] **Step 3: Commit:** `git add tests/trader/fixtures/l1/ && git commit -m "Add L1 test fixtures"`

---

## Task 2: `l1a_healthcheck.py` — fresh/stale check

**Files:**
- Create: `tools/trader/l1a_healthcheck.py`
- Create: `tests/trader/test_l1a_healthcheck.py`

- [ ] **Step 1: Write failing tests** — TDD red phase.

```python
# tests/trader/test_l1a_healthcheck.py
import unittest
from unittest.mock import patch
import datetime as dt

from tools.trader import l1a_healthcheck as hc


class L1AHealthcheckTest(unittest.TestCase):
    def test_fresh_when_under_threshold(self):
        fresh_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).isoformat()
        with patch.object(hc, "_fetch_last_insight_ts", return_value=fresh_ts):
            r = hc.check()
        self.assertTrue(r["fresh"])
        self.assertLess(r["last_seen_minutes_ago"], 120)
        self.assertEqual(r["threshold_minutes"], 120)

    def test_stale_when_over_threshold(self):
        stale_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=180)).isoformat()
        with patch.object(hc, "_fetch_last_insight_ts", return_value=stale_ts):
            r = hc.check()
        self.assertFalse(r["fresh"])
        self.assertGreater(r["last_seen_minutes_ago"], 120)

    def test_backend_unreachable_returns_fresh_false(self):
        with patch.object(hc, "_fetch_last_insight_ts", side_effect=ConnectionError):
            r = hc.check()
        self.assertFalse(r["fresh"])
        self.assertIsNone(r["last_seen_minutes_ago"])
```

- [ ] **Step 2: Verify tests fail**: `python3 -m unittest tests.trader.test_l1a_healthcheck -v`.

- [ ] **Step 3: Implement** `tools/trader/l1a_healthcheck.py`:
  - `THRESHOLD_MINUTES = 120`
  - `_fetch_last_insight_ts()` hits `:8787/api/v1/insights/last` (or equivalent — confirm endpoint from `fund_manager_client.py`). Returns ISO timestamp string or raises.
  - `check()` returns `{fresh, last_seen_minutes_ago, threshold_minutes}`. On `ConnectionError`/timeout: `fresh=False, last_seen_minutes_ago=None`.

- [ ] **Step 4: Verify tests pass** + smoke import: `python3 -c "from tools.trader import l1a_healthcheck; print(l1a_healthcheck.check())"` (live — will hit :8787; confirm not a crash).

- [ ] **Step 5: Commit:** `git add tools/trader/l1a_healthcheck.py tests/trader/test_l1a_healthcheck.py && git commit -m "Add l1a_healthcheck fresh/stale gate"`

---

## Task 3: `sb_screener_retail_avoider.py` — broker-activity wrap

**Files:**
- Create: `tools/trader/sb_screener_retail_avoider.py`
- Create: `tests/trader/test_l1_retail_avoider.py`

- [ ] **Step 1: Write failing tests** — parse fixture `broker_activity_raw.json` into normalized `{date, tickers: [{ticker, retail_net_sell, smart_net_buy, ratio}]}`. Cover: retail-broker-code filter (`XL|YP|XC|PD` etc), ratio math, zero-activity tickers excluded, date echoed.

- [ ] **Step 2: Verify fail.**

- [ ] **Step 3: Implement.** Reference spec §4.1 + `sb_screener_hapcu_foreign_flow.py` for style parity. Keep as pure fetch + reshape; no AI. Auth via `stockbit_auth.py`.

- [ ] **Step 4: Verify pass** + live smoke: one-shot script prints today's top 5 retail-avoiders.

- [ ] **Step 5: Commit.**

---

## Task 4: `l1_synth.py` — pure validators + pool union

**Files:**
- Create: `tools/trader/l1_synth.py`
- Create: `tests/trader/test_l1_synth.py`

Helpers to extract from playbook (keep playbook thin, keep pure logic testable):

- `valid_regime(s: str) -> bool` — `s in {"risk_on", "cautious", "risk_off"}`.
- `narrative_anchors_in_watchlist(narratives: list[Narrative], watchlist: list[ListItem]) -> bool`.
- `sectors_count_valid(sectors: list[str]) -> bool` — 3 ≤ len ≤ 5, all non-empty lowercase strings.
- `narratives_count_valid(narratives: list[Narrative]) -> bool` — 3 ≤ len ≤ 5.
- `union_candidate_pool(rag_top, broker_flow_hapcu, broker_flow_retail_avoider, lark_seed, holdings) -> list[str]` — deduped tickers, preserves first-seen order. Holdings always included.
- `format_telegram_recap(regime, sectors, narratives, watchlist, prev_regime, l1a_fresh_minutes, rag_empty: bool) -> str` — per spec §3.3 template, incl. `⚠️ regime flipped:` + `⚠️ RAG empty` prefixes when applicable.

- [ ] **Step 1: Write failing tests** covering each helper including edge cases (anchor in watchlist but duplicate ticker count, regime flipped, rag_empty prefix ordering when both regime flip + rag empty, holdings already in pool).

- [ ] **Step 2: Verify fail.**

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Verify pass.**

- [ ] **Step 5: Commit.**

---

## Task 5: Playbook `layer-1-insight.md`

**Files:**
- Create: `playbooks/trader/layer-1-insight.md`

Structure mirrors `layer-0-portfolio.md`:

1. **Header** — trigger, writes, guardrails (copy from spec §1).
2. **Step 1 — Load prior state** via `ct.load()`.
3. **Step 2 — L1-A healthcheck gate.** Call `l1a_healthcheck.check()`. Stale → `ct.save(layer="l1", status="error", note="L1-A stale Xmin")`, Telegram `⚠️ L1-A stale`, exit.
4. **Step 3 — Parallel fetches** (wrap in try/except, fail-soft per spec §6):
   - `api.rag_search(top_n=20, min_confidence=50)` → `rag_resp`
   - `sb_screener_hapcu_foreign_flow.run()` → `hapcu_resp`
   - `sb_screener_retail_avoider.run()` → `retail_resp`
   - `macro.snapshot()` or load `vault/data/overnight-YYYY-MM-DD.json` → `macro`
   - `catalyst_calendar.today()` or load `vault/data/catalyst-YYYY-MM-DD.json` → `catalysts`
   - `fund_manager_client.get_watchlist()` → `lark_seed`
5. **Step 4 — Build candidate pool** via `l1_synth.union_candidate_pool(...)`, always including `prior_status.holdings[*].ticker`.
6. **Step 5 — Opus synthesis.** Prompt template includes: regime guardrails (§5.1), watchlist curation rules (§5.2), narrative anchor invariant (§5.3), output JSON schema with regime literal + sectors list + narratives list + watchlist list. Expect strict JSON back.
7. **Step 6 — Validate.** Run all `l1_synth.valid_*` checks. First failure → trigger the single shared retry with error details appended to prompt. Retried response fails ANY check → `ct.save(status="error")`, Telegram alert, exit.
8. **Step 7 — Commit draft.** `draft = TraderStatus(regime=..., sectors=..., narratives=..., balance=prior.balance, pnl=prior.pnl, holdings=prior.holdings, aggressiveness=prior.aggressiveness)` (preserve L0 fields). `ct.lists.watchlist = ...`. `ct.save(layer="l1", status="ok", note=...)`.
9. **Step 8 — Daily note append** via `daily_note.append_section`.
10. **Step 9 — Telegram recap** via `l1_synth.format_telegram_recap(...)` + `telegram_client.send_message(...)` (always sent).
11. **Guardrails** block mirroring spec §1 "Does NOT write" list.

- [ ] **Step 1: Draft** the playbook in one pass.
- [ ] **Step 2: Verify** it compiles as prose — no undefined symbols. Check each Python code block imports match what the tools actually export (`grep` each `from X import Y`).
- [ ] **Step 3: Commit.**

---

## Task 6: Replace `/trade:insight` stub with trigger

**Files:**
- Modify: `.claude/commands/trade/insight.md`

Copy format from `.claude/commands/trade/portfolio.md`. Point at `playbooks/trader/layer-1-insight.md`, cite spec #3, note L1-A gate + 04:00 WIB schedule.

- [ ] **Step 1:** write + commit.

---

## Task 7: Index + progress doc updates

**Files:**
- Modify: `playbooks/trader/CLAUDE.md` (L1 row: stub → live).
- Modify: `skills/trader/CLAUDE.md` (append L1 to active-layer table).
- Modify: `docs/revamp-progress.md` (see File Structure above — fill Used-by-layer for L1 consumers, add new-tool rows, add `services/telegram-scraper/` external row).

- [ ] **Step 1:** edit all three files.
- [ ] **Step 2:** verify via `grep -n "L1" playbooks/trader/CLAUDE.md skills/trader/CLAUDE.md docs/revamp-progress.md`.
- [ ] **Step 3:** commit.

---

## Task 8: Full test suite + smoke imports

- [ ] `python3 -m unittest discover tests -v` — all green.
- [ ] Smoke imports: `python3 -c "from tools.trader import l1a_healthcheck, sb_screener_retail_avoider, l1_synth"`.
- [ ] Tag plan: `git tag spec-3-plan-complete`.

---

## Task 9: Manual dry-run (acceptance)

- [ ] Invoke `/trade:insight` interactively. Expected:
  - L1-A freshness gate passes (check telegram-scraper is up: `systemctl --user is-active telegram-scraper` — adjust if unit name differs).
  - RAG + broker-flow + macro + catalyst + Lark fetches complete.
  - Opus returns valid regime + 3–5 sectors + 3–5 narratives + watchlist anchoring all narratives.
  - `current_trade.json` bumps version, `trader_status.regime` set, `lists.watchlist` populated, `layer_runs.l1.status == "ok"`.
  - `vault/daily/YYYY-MM-DD.md` gets a `### L1 — HH:MM` section.
  - Telegram recap arrives with correct format.
- [ ] If dry-run green: `docs/revamp-progress.md` spec #3 → `complete`; tag `spec-3-complete`.

---

## Self-Review Notes

- **Watch for**: stale MCP tool registry if new MCP tools added mid-session — same trap as spec #2. L1 adds no new MCP tools (all deps are Python-direct or existing), so no MCP restart dance expected.
- **Blocker risk**: L1-A healthcheck depends on `:8787` endpoint shape. Confirm endpoint path/response before writing `_fetch_last_insight_ts`. Peek `tools/trader/fund_manager_client.py` and Go backend for the live route.
- **Opus prompt length**: spec lists 7+ inputs fed into one prompt. Keep prompt template skeletal; truncate insight bodies to ≤200 chars each before injection.
- **Fail-soft vs hard-abort paths**: wire the table in spec §6 exactly — confusion there will leak into user-visible Telegram messages.
- **Retry budget**: single shared retry across all validation dimensions. Easy to accidentally allow per-dimension retries; enforce with a single counter variable in the playbook.
