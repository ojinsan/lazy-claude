# Spec #2 — L0 Portfolio Analysis

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Spec #1 (prereq):** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-1-core-design.md`

## 1. Scope & Trigger

L0 is the daily portfolio-health entry layer. Runs once per trading day, seeds `trader_status` fields that every downstream layer reads.

- **Trigger:** CRON 03:00 WIB (Mon–Fri) → `claude /trade:portfolio`.
- **Model:** Opus (bidirectional fallback to openclaude via `tools/_lib/claude_model.py`).
- **Writes:** `trader_status.balance`, `trader_status.pnl`, `trader_status.holdings`, `trader_status.aggressiveness`.
- **Does NOT write:** `trader_status.regime` (L1), `trader_status.sectors` (L1), `trader_status.narratives` (L1), `lists.watchlist` (L1), `lists.superlist`/`lists.exitlist` (L2). Does not cancel orders or reduce positions.

## 2. Inputs

| Input | Source | Purpose |
|-------|--------|---------|
| Cash + buying power | `mcp__lazytools__carina_cash_balance` | live balance |
| Positions (lot, avg, current, unrealized PnL) | `mcp__lazytools__carina_position_detail` | live holdings + `pnl.unrealized` |
| Filled orders history | `mcp__lazytools__carina_orders` | source for MtD/YtD realized rollup + context on last close |
| Prior `trader_status.pnl` | `current_trade.json` (load via spec #1 `load()`) | seed for MtD/YtD carry-forward if carina_orders thin |
| Per-holding thesis | `vault/thesis/<TICKER>.md` (missing → skip gracefully) | drift-check input |
| Prior trading day's L-layer notes | `vault/daily/YYYY-MM-DD.md` | thesis context |

**MtD / YtD rollup:** playbook computes by summing realized PnL across filled sell orders from `carina_orders` within month / year window. If `carina_orders` does not return the full window, fall back to prior `trader_status.pnl.mtd`/`ytd` + today's increment. No separate script yet — playbook does it inline.

All inputs collected by the playbook, consolidated into a single prompt for Opus synthesis. No new Python aggregator script.

## 3. Outputs

### 3.1 `current_trade.trader_status` fields

```json
{
  "balance": { "cash": 19612924.64, "buying_power": 19612924.64 },
  "pnl": { "realized": 0, "unrealized": -150000, "mtd": -250000, "ytd": 1200000 },
  "holdings": [
    {
      "ticker": "ADMR",
      "lot": 40,
      "avg_price": 1950,
      "current_price": 1940,
      "pnl_pct": -0.5,
      "details": "thesis-drift: supply wall at 1985 unbroken 3d; hold_age: 18d"
    }
  ],
  "aggressiveness": "defensive"
}
```

Aggressiveness 5-tier literal: `very_defensive | defensive | neutral | aggressive | very_aggressive`.

Field meanings (matches `tools/_lib/current_trade.py` dataclass):
- `pnl.realized` — today's realized PnL in IDR (0 at 03:00 pre-market since no trades yet; kept in schema so L5 fills later in day).
- `pnl.unrealized` — sum of open-position unrealized across all holdings in IDR.
- `pnl.mtd` / `pnl.ytd` — month-to-date / year-to-date realized rollup in IDR.
- `holding.pnl_pct` — percent units, not fraction (e.g. `-0.5` means `-0.5%`, not `-50%`).
- `holding.details` — see prefix rules below. New field, added by this spec (§4.3).

`holding.details` stores free-text Opus notes. Exactly one prefix per holding, chosen by priority (highest → lowest):
1. `redflag: …` — overrides all others when redflag triggers fire (see §6.2)
2. `thesis-drift: …` — thesis present but holding diverging from thesis
3. `thesis-on-track: …` — thesis present and aligned
4. `no thesis: …` — when `vault/thesis/<TICKER>.md` missing

L2 consumes `holding.details` when deciding exitlist membership. L0 itself never writes to exitlist.

### 3.2 Daily note append — `vault/daily/YYYY-MM-DD.md`

Appended to `## Auto-Appended` section:

```markdown
### L0 — 03:00
Balance Rp 19.6M. Holdings: ADMR, IMPC, AADI, BUMI. MtD -Rp 250k. Aggressiveness: defensive (cash 11% of AUM, MtD negative, 1 redflag). Redflag: ADMR (thesis drift 5d under supply).
```

Aggressiveness tier goes verbatim into `trader_status.aggressiveness`; the `(reason)` parenthetical lives only in the daily note.

If file does not exist, create with header `# YYYY-MM-DD\n\n## Auto-Appended\n\n`.

### 3.3 Telegram alert (conditional)

Send iff ≥1 holding has `redflag:` prefix in `details`. Short message:

```
L0 redflags (1):
• ADMR — thesis drift, 5d under 1985 supply, hold_age 18d
```

No Telegram if zero redflags. L0 stays silent for clean days.

### 3.4 `current_trade.layer_runs.l0`

Updated via `tools/_lib.current_trade.save(ct, layer="l0", status="ok"|"error", note=summary)`. Spec #1 handles atomic write + snapshot.

## 4. Files to Create / Modify

### 4.1 Create
- `playbooks/trader/layer-0-portfolio.md` — combined skill+workflow. Contains: step-by-step, Carina MCP usage examples, MtD/YtD rollup snippet from `carina_orders`, aggressiveness prompt guardrails, redflag heuristics, Opus prompt template, daily-note append format, Telegram alert format.

### 4.2 Replace (stub → real)
- `.claude/commands/trade/portfolio.md` — thin trigger. Loads playbook, runs it.

### 4.3 Modify
- `tools/_lib/current_trade.py` — extend `Holding` dataclass with `details: str = ""` (backward-compat additive field). Update `_parse_list_item` equivalent parser if needed.
- `tests/_lib/test_current_trade.py` — add round-trip test for `holding.details`.
- `docs/revamp-progress.md` — fill `Used-by-layer` column with `L0` for `telegram_client.py` (already `live`, just tag consumer). Add note row for Carina MCP tools consumed by L0: `carina_cash_balance`, `carina_position_detail`, `carina_orders`.
- `playbooks/trader/CLAUDE.md` — replace stub with layer index row for L0.
- `skills/trader/CLAUDE.md` — note L0 playbook location.

### 4.4 Not created (deliberate)
- `skills/trader/portfolio-analysis.md` — collapsed into playbook.
- `tools/trader/l0_*.py` — no new Python helper.
- `tools/manual/carina.md` — deferred to Spec #7 (L5 Execute) when Carina usage grows.

## 5. Aggressiveness Logic

Opus synthesizes tier from full snapshot. No rule-based code. Playbook gives Opus guardrails for consistent output.

**Inputs Opus considers:**
- Cash ratio (cash / total AUM).
- MtD PnL direction and magnitude.
- Number of open positions vs. typical load.
- Recent consecutive losing days.
- Count of holdings with `redflag:` notes.
- Yesterday's L0 posture (stability — avoid daily flips without cause).

**Output contract:**
- Tier string in `trader_status.aggressiveness` — MUST be one of the 5 literals. Anything else → treat as error, status=error, keep previous tier.
- One-sentence reason in daily note parenthetical only. Not in JSON.

**Consumers:**
- L1 uses tier to tune sector-bias weighting.
- L4 uses tier for position sizing (defensive → smaller size, aggressive → larger).

## 6. Thesis Drift + Redflag Heuristics

### 6.1 Thesis drift per holding

1. Check `vault/thesis/<TICKER>.md`. Missing → `holding.details = "no thesis: …"`, continue.
2. If present, pass to Opus alongside current price, PnL%, and last 3 days of daily-note mentions for this ticker.
3. Opus classifies as `thesis-on-track` or `thesis-drift` with ≤1 sentence reason.

### 6.2 Redflag triggers

Opus decides. Playbook lists hints:
- PnL ≤ −8% from avg_price.
- Invalidation level breached (price < stated cutloss in thesis).
- Hold age > 30d without thesis progress note.
- Daily-note mentions of `defensive` / `reduce` / `invalidation` ≥3 times in last 3 days.

Redflag note format:
```
redflag: pnl -9.2% + stuck under 1985 supply 5d; hold_age 24d
```

### 6.3 Bounds

L0 only writes notes. Never writes to `exitlist`, never cancels orders, never changes position size. L2 reads `holding.details` when scoring redflag dimension; L4/L5 act on exit decisions.

## 7. Error Handling + Idempotence

| Failure | Behavior |
|---------|----------|
| Carina MCP 5xx / timeout | Playbook retries 3× with 2s backoff (inline try/except — `ratelimit.py` is throttling only, not retry). Still fail → `save(layer="l0", status="error", note="carina unreachable")`, Telegram alert, exit. No partial `trader_status` write. |
| Opus + openclaude both fail | `claude_model.run()` raises `ModelError` → catch, status=error, note, Telegram, exit. |
| `vault/thesis/<T>.md` missing | `holding.details = "no thesis: ..."`. Not fatal. |
| `vault/daily/YYYY-MM-DD.md` missing | Create with `# YYYY-MM-DD\n\n## Auto-Appended\n\n` header, then append L0 section. |
| `current_trade.json` corrupt / schema mismatch | `load()` raises ValueError → Telegram alert, exit. Manual repair. No auto-recover. |
| Invalid aggressiveness tier from Opus | Treat as error, keep previous tier value from loaded `trader_status`, status=error, note. |
| Duplicate run (2× CRON same day) | Idempotent: `save()` bumps version + overwrites `trader_status` with fresh snapshot; history snapshot becomes new `l0-HHMM.json`; daily note appends new `### L0 — HH:MM` section. |

**Atomicity:** `current_trade.save()` already atomic (spec #1 T5). Daily-note append uses `open(path, "a")` — not atomic but single-writer at 03:00 = no race.

## 8. Testing

Stdlib `unittest`. No new deps. Mocks via `unittest.mock.patch`.

### 8.1 Fixtures (`tests/trader/fixtures/l0/`)

- `carina_cash.json`, `carina_positions.json`, `carina_orders.json` — canned MCP responses.
- `thesis_ADMR.md`, `thesis_IMPC.md` — sample thesis files.
- `daily_2026-04-17.md` — prior-day note.

### 8.2 Unit tests (`tests/trader/test_l0_*.py`)

| Test | Assertion |
|------|-----------|
| `test_snapshot_merges_carina_into_holdings` | holdings list has ticker/lot/avg/current/pnl_pct for each position |
| `test_pnl_rollup_from_carina_orders` | mtd/ytd summed correctly from filled sell orders window |
| `test_missing_thesis_file_yields_no_thesis_note` | `holding.details` starts with `"no thesis:"` |
| `test_aggressiveness_tier_written_verbatim` | Opus response parsed into 5-tier literal |
| `test_redflag_holding_triggers_telegram` | `telegram.send` called iff ≥1 redflag; silent otherwise |
| `test_daily_note_append_creates_file_if_missing` | file created with `### L0 — HH:MM` section |
| `test_current_trade_save_called_with_layer_l0` | `save(ct, layer="l0", status="ok", note=...)` |
| `test_model_error_sets_status_error_and_alerts` | status=error, Telegram alert, no partial state |

### 8.3 Integration test (optional)

`tests/trader/test_l0_e2e.py`: runs whole playbook with all I/O mocked, asserts final `current_trade.json` + daily-note output match golden fixture.

## 9. Out-of-Scope Reminders

- **Does NOT manage `vault/thesis/*`.** L4 creates/updates these on entry (per master design).
- **Does NOT write regime/sectors/narratives.** L1 owns those.
- **Does NOT touch watchlist/superlist/exitlist.** L1/L2 own list promotion.
- **Does NOT execute orders.** L5 is the only executor.
- **No `tools/manual/carina.md` yet.** Deferred to Spec #7.
- **No post-trade trigger.** Only CRON 03:00. Realtime holding updates happen via L5 success confirmations.

## 10. Dependencies

- Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`. (`ratelimit.py` unused by L0 — single-shot cron, no polling.)
- Existing tools: `tools/trader/telegram_client.py`.
- MCP: `mcp__lazytools__carina_cash_balance`, `mcp__lazytools__carina_position_detail`, `mcp__lazytools__carina_orders`.
- Vault: `vault/thesis/<TICKER>.md` (convention introduced by L4; L0 reads only, missing → graceful), `vault/daily/YYYY-MM-DD.md`.
