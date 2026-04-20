# Spec #3 — L1 Insight & Context Synthesis (+ L1-A healthcheck)

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Spec #1 (prereq):** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-1-core-design.md`
**Spec #2 (prereq):** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`

## 1. Scope & Trigger

Spec #3 covers **L1** (new playbook + thin slash trigger) and **L1-A** (healthcheck + progress-doc tag). L1-B threads ingestion is deferred to a later spec.

### L1

- **Trigger:** CRON 04:00 WIB (Mon–Fri) → `claude /trade:insight`.
- **Model:** Opus (bidirectional fallback to openclaude via `tools/_lib/claude_model.py`).
- **Writes:** `trader_status.regime` (`risk_on | cautious | risk_off`), `trader_status.sectors` (3–5 `list[str]`), `trader_status.narratives` (3–5 entries, `Narrative` dataclass), `lists.watchlist` (Opus-curated `list[ListItem]`).
- **Does NOT write:** `trader_status.balance`, `trader_status.pnl`, `trader_status.holdings`, `trader_status.aggressiveness` (L0), `lists.filtered`, `lists.superlist`, `lists.exitlist` (L2). Does not cancel orders or reduce positions.

### L1-A (existing service)

- **Status:** LIVE systemd unit `services/telegram-scraper/` → posts to fund-manager `:8787` insight ingest endpoint. Poll interval 30 min.
- **This spec's delta:** add `tools/trader/l1a_healthcheck.py` (new) and progress-doc row. No change to systemd unit or scraper code.
- **Healthcheck role:** L1 playbook runs healthcheck first; if stale (last insight > 120 min) → L1 aborts without overwriting `trader_status`.

### L1-B (deferred)

`tools/general/playwright/threads-scraper.js` remains one-shot CLI only. No 6-hour wrapper, no RAG ingest, no L1 consumption from threads. Will get its own spec when threads data is wired in.

## 2. Inputs

| Input | Source | Purpose |
|-------|--------|---------|
| L1-A freshness gate | `tools/trader/l1a_healthcheck.py` (new) | abort if RAG stale >120 min |
| RAG top-confidence tickers + themes | `tools/trader/api.py::rag_search(query, top_n, min_confidence)` | candidate ticker pool + narrative evidence |
| Recent insights per ticker | `tools/trader/api.py::get_insights(ticker, limit, days)` | detail for Opus narrative synthesis |
| Broker flow (HAPCU / foreign) | `tools/trader/sb_screener_hapcu_foreign_flow.py` (existing) | smart-money net direction |
| Retail-avoidance screener | `tools/trader/sb_screener_retail_avoider.py` (**new** — wraps Stockbit `/order-trade/broker/activity` fetch per PRD) | tickers retail brokers net-selling |
| Macro / overnight | `tools/trader/macro.py` + `vault/data/overnight-YYYY-MM-DD.json` (prefetched by `overnight_macro.py`) | regime inputs |
| Catalyst calendar | `tools/trader/catalyst_calendar.py` or `vault/data/catalyst-YYYY-MM-DD.json` | sector / event flagging |
| Manual watchlist seed | `tools/trader/fund_manager_client.py::get_watchlist()` (Lark + SQLite merged via `/api/v1/watchlist`) | Boss O's manual picks merge into Opus pool |
| Prior day `trader_status` | `current_trade.json` via spec #1 `load()` | previous regime for stability check; revert target on abort |
| L0 output same day | `current_trade.trader_status.holdings` + `aggressiveness` | Opus factors current holdings + posture into regime and watchlist |

All inputs collected by the playbook, consolidated into a single Opus prompt. Only two new Python files: `sb_screener_retail_avoider.py` and `l1a_healthcheck.py`.

## 3. Outputs

### 3.1 `current_trade` fields

```json
{
  "trader_status": {
    "regime": "cautious",
    "sectors": ["coal", "banking", "consumer"],
    "narratives": [
      {
        "ticker": "ADMR",
        "content": "coal exporters riding China winter restock + weak rupiah tailwind; ADMR strongest margin leverage in group",
        "source": "rag:telegram+broker-flow",
        "confidence": 78
      }
    ]
  },
  "lists": {
    "watchlist": [
      {
        "ticker": "ADMR",
        "confidence": 78,
        "current_plan": null,
        "details": "coal theme exemplar; smart-money net buy 3d; RAG top ticker"
      }
    ]
  }
}
```

**Field rules:**

- `regime` — one of 3 literals: `risk_on | cautious | risk_off`. Invalid → status=error, keep previous.
- `sectors` — 3–5 lowercase sector tags. No fixed vocab; Opus picks.
- `narratives` — 3–5 entries. Each anchored to an exemplar ticker that MUST also appear in `watchlist`. Other tickers riding the same theme live in `watchlist` without duplicating narrative rows.
- `watchlist` — Opus decides size + composition. `current_plan=null` on L1 write (L4 fills). `details` free-text ≤1 sentence explaining why-picked.
- `source` in a Narrative — colon-separated origin list (e.g. `rag:telegram+broker-flow`, `lark`, `holding-seed`, `no-rag` when RAG empty).

### 3.2 Daily note append — `vault/daily/YYYY-MM-DD.md`

Appended to the `## Auto-Appended` section:

```markdown
### L1 — 04:00
Regime: cautious (IHSG below MA50, foreign net sell 3d, DXY firming). Sectors: coal, banking, consumer. Narratives: 4 active themes. Watchlist: 12 tickers (top: ADMR, BUMI, BBCA). L1-A freshness: 18min.
```

If file does not exist, create with header `# YYYY-MM-DD\n\n## Auto-Appended\n\n`.

### 3.3 Telegram recap (always)

Short, always-send at 04:00 via `telegram_client.py`:

```
L1 04:00 — regime: CAUTIOUS
Sectors: coal, banking, consumer
Themes (4):
  • coal exporters China winter
  • banking BI cut repricing
  • consumer Lebaran restock
  • property BI-rate pause
Watchlist: 12 (ADMR, BUMI, BBCA, …)
```

Watchlist line shows total count + first 3 tickers. If ≤3, show all without ellipsis. Prepend `⚠️ regime flipped: {prev} → {new}` when regime changes vs. yesterday's `trader_status.regime`.

### 3.4 `current_trade.layer_runs.l1`

Updated via `tools/_lib.current_trade.save(ct, layer="l1", status="ok"|"error", note=summary)`. Spec #1 handles atomic write + snapshot (`runtime/history/YYYY-MM-DD/l1-HHMM.json`).

## 4. Files to Create / Modify

### 4.1 Create

- `playbooks/trader/layer-1-insight.md` — combined skill+workflow. Step-by-step: L1-A healthcheck gate → RAG queries → broker flow + retail-avoider snapshots → macro + catalyst pull → Lark seed merge → Opus synthesis prompt template → watchlist/regime/sectors/narratives output validation → daily-note append → Telegram recap.
- `tools/trader/l1a_healthcheck.py` — queries fund-manager `:8787` for most-recent insight row timestamp. Returns `{fresh: bool, last_seen_minutes_ago: int, threshold_minutes: 120}`. Exit code 0 always; caller reads `fresh`.
- `tools/trader/sb_screener_retail_avoider.py` — wraps the Stockbit `/order-trade/broker/activity` fetch shown in PRD. Input: date range + retail broker codes (`XL|YP|XC|PD|…`). Output: JSON `{date, tickers: [{ticker, retail_net_sell, smart_net_buy, ratio}]}`. No AI; pure fetch + reshape. Auth via existing `stockbit_auth.py`.
- `tests/trader/test_l1_*.py` — unit tests (see §7).
- `tests/trader/fixtures/l1/` — canned RAG responses, broker-flow snapshots, macro JSON, healthcheck fresh/stale samples.

### 4.2 Replace (stub → real)

- `.claude/commands/trade/insight.md` — thin trigger. Loads playbook, runs it.

### 4.3 Modify

- `tools/_lib/current_trade.py` — no changes. `regime`, `sectors`, `narratives`, `watchlist` already present in dataclasses (spec #1).
- `docs/revamp-progress.md` — fill `Used-by-layer` with `L1` for: `macro.py`, `catalyst_calendar.py`, `overnight_macro.py`, `sb_screener_hapcu_foreign_flow.py`, `api.py` (rag_search + get_insights), `narrative.py`, `fund_manager_client.py` (get_watchlist Lark merge), `telegram_client.py`. Add rows for new `sb_screener_retail_avoider.py` (L1, live) and `l1a_healthcheck.py` (L1, live). Add external-service row for `services/telegram-scraper/` (L1-A: systemd, posts to `:8787/insight`).
- `playbooks/trader/CLAUDE.md` — add layer index row for L1.
- `skills/trader/CLAUDE.md` — note L1 playbook location.

### 4.4 Not created (deliberate)

- `skills/trader/insight-gathering.md` — collapsed into playbook.
- `tools/manual/telegram-scraper.md` — deferred. Ops-only concern.
- Threads listener (L1-B) infra — deferred to its own later spec.
- No sqlite mirror of RAG — Go backend stays source of truth.

## 5. Regime + Watchlist Logic

### 5.1 Regime synthesis

Opus synthesizes `regime` literal. No rule-based code. Playbook lists guardrails for Opus to weigh:

- IHSG trend + foreign net flow (from `macro.py`).
- DXY / US 10Y / commodity direction (overnight JSON).
- Catalyst calendar — Fed / BI events, geopolitics, earnings season.
- Broker flow: smart-money net direction across IHSG leaders.
- RAG theme density — count of distinct themes with ≥3 insights in last 24h.
- Yesterday's regime (stability — avoid flipping without cause).

**Output contract:**

- `trader_status.regime` MUST be one of `risk_on | cautious | risk_off`. Invalid → 1-shot retry; still invalid → status=error, keep previous.
- One-sentence reason lives in daily-note parenthetical only. Not in JSON.

### 5.2 Watchlist curation

Candidate pool (dedup union):

- RAG top tickers (`rag_search(top_n=20, min_confidence=50)`).
- Broker flow net-buy standouts (`sb_screener_hapcu_foreign_flow`).
- Retail-avoidance leaders (`sb_screener_retail_avoider`).
- Lark + local SQLite manual seeds (`fund_manager_client.get_watchlist()`).
- Current holdings (always included so L2 can rescreen them).

Opus receives the full pool + regime + sectors + narratives, returns final `lists.watchlist`. No fixed N cap — Opus decides. Playbook guardrails:

- Prefer tickers fitting ≥1 narrative.
- Keep all holdings in the watchlist. Advisory tag in `details`: prefix `holding — ` when ticker is also in `trader_status.holdings`. L2 MUST cross-reference against `trader_status.holdings[*].ticker` for authoritative holding status — not parse this tag.
- Exclude tickers where retail-avoider ratio disagrees sharply with RAG confidence (flag as conflict signal in `details`).

### 5.3 Sectors + Narratives

3–5 sectors, 3–5 narratives. Narrative anchor invariant:

```
all(n.ticker in {w.ticker for w in watchlist}) == True
```

Violation → 1-shot retry prompt. Still invalid → status=error, keep previous. No second retry (cost cap).

### 5.4 Consumers

- **L2** reads `watchlist` + `narratives` + `sectors` + `regime` for per-ticker screening.
- **L4** reads `regime` + `narratives` for position sizing and thesis entry writing.

## 6. Error Handling + Idempotence

| Failure | Behavior |
|---------|----------|
| L1-A healthcheck stale (>120 min) | Hard abort. `save(layer="l1", status="error", note="L1-A stale Xh")`, Telegram alert `⚠️ L1-A stale`, keep previous `regime`/`sectors`/`narratives`/`watchlist`. |
| fund-manager `:8787` unreachable | Playbook retries 3× with 2s backoff (inline try/except). Still fail → abort like L1-A stale. Note: `backend unreachable`. |
| `rag_search` returns empty across all 3 fallback sources | Not fatal. Opus proceeds on broker flow + macro + Lark only. Narratives tagged `source: "no-rag"`. Telegram recap prepends `⚠️ RAG empty`. |
| `sb_screener_hapcu_foreign_flow` or `sb_screener_retail_avoider` fails | Not fatal. Playbook logs warning, Opus proceeds without that input. Note appended to daily summary. |
| `overnight_macro` JSON missing | Not fatal. Fallback to live `macro.py` fetch. If that fails too, Opus proceeds on RAG + catalyst only. |
| Opus + openclaude both fail | `claude_model.run()` raises `ModelError` → abort. `status=error`, Telegram alert, keep previous state. |
| Invalid `regime` literal from Opus | Trigger shared 1-shot retry (see Retry budget below). Still invalid → abort, keep previous. |
| Narrative anchor ticker ∉ watchlist | Trigger shared 1-shot retry (see Retry budget below). Still invalid → abort, keep previous. |
| Sectors count outside 3–5 | Trigger shared 1-shot retry. Still invalid → abort, keep previous. |
| Narratives count outside 3–5 | Trigger shared 1-shot retry. Still invalid → abort, keep previous. |
| `current_trade.json` corrupt / schema mismatch | `load()` raises ValueError → Telegram alert, exit. Manual repair. No auto-recover. |
| Duplicate 04:00 run (2× CRON same day) | Idempotent: `save()` bumps version, overwrites regime/sectors/narratives/watchlist with fresh snapshot. History snapshot becomes new `l1-HHMM.json`. Daily note appends new `### L1 — HH:MM` section. Telegram recap re-sends. |

**Atomicity:** `current_trade.save()` atomic (spec #1 T5). Daily-note append uses `open(path, "a")` — single-writer at 04:00 = no race.

**Retry budget:** total of 1 Opus re-prompt per L1 run, shared across all validation dimensions (invalid regime, invalid sectors count, narrative-anchor mismatch, etc). First validation failure triggers the single retry with error details fed back into the prompt. If the retried response still fails ANY validation dimension → abort and keep previous state. Prevents cost spiral on a broken prompt.

## 7. Testing

Stdlib `unittest`. No new deps. Mocks via `unittest.mock.patch`.

### 7.1 Fixtures (`tests/trader/fixtures/l1/`)

- `rag_top_tickers.json` — canned `rag_search` response.
- `rag_empty.json` — empty-result case.
- `broker_flow_hapcu.json`, `broker_flow_retail_avoider.json` — canned screener outputs.
- `macro_overnight.json`, `catalyst_today.json` — sample snapshots.
- `fund_manager_watchlist.json` — sample Lark + SQLite merged rows.
- `insight_recent_fresh.json` (10 min ago), `insight_recent_stale.json` (180 min ago) — healthcheck cases.

### 7.2 Unit tests (`tests/trader/test_l1_*.py`)

| Test | Assertion |
|------|-----------|
| `test_l1a_healthcheck_fresh_passes` | fresh=True when last_seen_minutes_ago<120 |
| `test_l1a_healthcheck_stale_aborts_l1` | stale → status=error, regime/sectors unchanged |
| `test_rag_empty_not_fatal_degraded_tag` | narratives tagged `source="no-rag"`, regime still written |
| `test_broker_flow_fetch_failure_not_fatal` | warning logged, Opus still called |
| `test_watchlist_union_includes_holdings` | all holdings appear in final watchlist |
| `test_narrative_anchor_validation_retry` | invalid anchor → 1 prompt retry; still invalid → abort |
| `test_invalid_regime_literal_retries_then_aborts` | 1-shot retry, then status=error |
| `test_regime_flip_prepends_warning_to_telegram` | `⚠️ regime flipped:` in message body |
| `test_daily_note_append_creates_file_if_missing` | file created with `### L1 — HH:MM` section |
| `test_current_trade_save_called_with_layer_l1` | `save(ct, layer="l1", status="ok", …)` |
| `test_backend_unreachable_preserves_previous_state` | abort, regime/sectors/watchlist untouched |
| `test_retail_avoider_screener_parses_broker_activity` | output schema `{date, tickers: [...]}` |

### 7.3 Integration test (optional)

`tests/trader/test_l1_e2e.py`: full playbook with all I/O mocked. Asserts final `current_trade.json` + daily-note append + Telegram payload match golden fixture.

## 8. Dependencies + Out-of-Scope

### 8.1 Dependencies

- Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`.
- Existing tools: `tools/trader/api.py` (rag_search, get_insights, macro helpers), `tools/trader/fund_manager_client.py` (Lark watchlist merge), `tools/trader/macro.py`, `tools/trader/catalyst_calendar.py`, `tools/trader/overnight_macro.py`, `tools/trader/narrative.py`, `tools/trader/sb_screener_hapcu_foreign_flow.py`, `tools/trader/telegram_client.py`, `tools/trader/stockbit_auth.py` (used by new retail-avoider screener).
- External services: `services/telegram-scraper/` (systemd, live). `:8787` fund-manager Go backend (live) — RAG + Lark-merged watchlist both live here.
- Spec #2 artifacts: `trader_status.holdings` + `aggressiveness` read by L1 (never written).
- Vault paths: `vault/daily/YYYY-MM-DD.md`, `vault/data/overnight-YYYY-MM-DD.json`, `vault/data/catalyst-YYYY-MM-DD.json`.

### 8.2 Out-of-Scope

- **L1-B Threads listener** — deferred to its own spec. `threads-scraper.js` stays one-shot CLI.
- **Threads direct ingestion at L1 runtime** — no live Playwright call from L1 playbook. RAG-only for insight evidence.
- **Superlist / exitlist writes** — L2 territory.
- **Balance / PnL / holdings / aggressiveness writes** — L0 territory.
- **Order execution** — L5 only.
- **Thesis file maintenance** — L4 on entry.
- **New RAG sqlite mirror / JSON fallback** — Go backend is source of truth.
- **Manual for telegram-scraper ops** — deferred.
- **No post-trigger rerun.** Only CRON 04:00. Intraday regime changes happen via L3 posture flips, not L1.
