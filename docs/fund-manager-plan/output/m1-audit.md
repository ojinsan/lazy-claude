# M1.1 — Layer Integration Audit

Generated: 2026-04-17. Based on direct read of all layer playbooks + skills + tools.

---

## Integration Matrix

| Producer | Artifact | Path / Call | Consumer | State |
|----------|----------|-------------|----------|-------|
| L0 | portfolio-state.json | `vault/data/portfolio-state.json` | L2 Gate 3, L4 sizing, L5 pre-check | OK |
| L0 | thesis-actions | `vault/data/thesis-actions.json` | L2 Gate 2, L4 substitution | **GAP** — file doesn't exist yet |
| L0 | Self-review note | `vault/journal/YYYY-MM-DD-review.md` | L0 next-day Step 1.5 | **GAP** — L0 never reads yesterday's orders |
| L0 | Stale list | `journal.thesis_status_summary()["stale"]` | L0 Step 4 | **GAP** — not enforced, no CLI |
| L1 | Market regime + posture | verbal in daily note | L2, L4, L5 | OK (daily-note section) |
| L1 | Sector themes | verbal in daily note | L2 screening, L4 catalyst | OK |
| L1 | Intraday regime flip | `vault/data/regime-intraday.json` | L3 sizing, L4 plan | **GAP** — file doesn't exist; no mid-day re-eval |
| L1 | Overnight macro | `vault/data/overnight-YYYY-MM-DD.json` | L1 05:00 run | **GAP** — not prefetched; fetched live at 05:00 |
| L2 | Airtable Superlist | MCP / `airtable_client` | L3 track, L4 plan | OK |
| L2 | Universe candidates | `vault/data/universe-YYYY-MM-DD.json` | L2 sweep | **GAP** — no universe scan script |
| L2 | Catalyst calendar | `vault/data/catalyst-YYYY-MM-DD.json` | L1/L2/L4 | **GAP** — not built |
| L2 | Relative strength | `relative_strength.py` | L2 criterion 3.5 | **GAP** — not built |
| L2 | Daily-note L2 section | `append_daily_layer_section('2',...)` | human review | OK |
| L3 | monitoring log | `runtime/monitoring/YYYY-MM-DD.md` | L4 Mode B | OK |
| L3 | Thesis review | `append_thesis_review(ticker, 'L3', note)` | L0 next-day Step 4 | OK |
| L3 | Tape state | `runtime/monitoring/` | L4 context | **GAP** — no tape_runner, no structured tape_state |
| L3 | Intraday regime | `set_intraday_posture()` | L4/L5 | **GAP** — function doesn't exist |
| L4 | Tradeplan file | `runtime/tradeplans/YYYY-MM-DD.md` | L5 entry | OK |
| L4 | Confluence score | tradeplan body | L5 gate | **GAP** — no structured confluence, no code |
| L4 | Calibration check | `confidence_calibration()` | L4 sizing | **GAP** — computed but not called at sizing |
| L5 | Orders log | `runtime/orders/YYYY-MM-DD.jsonl` | L0 next-day | **GAP** — L0 never reads it |
| L5 | journal.log_trade | `vault/data/transactions.json` | weekly review, calibration | OK |
| L5 | Airtable Superlist | status update | L0 thesis scan | OK |
| EOD | Daily note publish | `runtime_eod_publish.py` | weekly review | OK |
| weekly | `generate_weekly_review()` | `vault/reviews/weekly/` | monthly review | OK — but **no cron** triggers it |
| monthly | `generate_monthly_review()` | `vault/reviews/monthly/` | Boss O review | OK — but **no cron** triggers it |
| L0 | Kill-switch check | `kill_switch_state()` | L4/L5 entry block | **GAP** — function doesn't exist |
| L4 | hit_rate_by(pattern) | `journal.hit_rate_by()` | L4 sizing cap | **GAP** — function doesn't exist |
| L0/L5 | Close auto-lesson | `_draft_lesson_from_close()` | L5 post-trade | **GAP** — function doesn't exist |
| L0 | Portfolio history row | `vault/data/portfolio-state.json history[]` | performance tracking, M2 | **PARTIAL** — history array but not verified idempotent |

---

## Gaps (27 identified)

### Gap 1 — L5 → L0 feedback loop
- **Symptom:** Claude opens the next day with no programmatic read of what orders were placed yesterday.
- **Root cause:** L0 playbook doesn't reference `runtime/orders/*.jsonl`.
- **Fix:** M1.2 Gap 1.

### Gap 2 — Thesis-action state not promoted between layers
- **Symptom:** L0 flags a hold as `exit-candidate` but L2 still promotes an add for the same name.
- **Root cause:** `set_thesis_action` / `get_thesis_actions` don't exist; no `vault/data/thesis-actions.json`.
- **Fix:** M1.2 Gap 2.

### Gap 3 — Intraday regime never re-evaluated
- **Symptom:** L1 regime stays at 05:00 read all day. 11:30 IHSG breakdown isn't captured.
- **Root cause:** `set_intraday_posture` doesn't exist; no mid-day cron.
- **Fix:** M1.2 Gap 3 + M1.5 §5.4.

### Gap 4 — Calibration computed but not enforced at sizing
- **Symptom:** `confidence_calibration()` exists and returns drift, but execution.md sizing formula never calls it.
- **Root cause:** No connection between `D. Confidence Calibration` in journal.py and the execution skill.
- **Fix:** M1.2 Gap 4.

### Gap 5 — Stale thesis not enforced
- **Symptom:** `thesis_status_summary()["stale"]` lists tickers with no 7-day review, but L0 Step 4 doesn't call it first.
- **Root cause:** No CLI entry point; L0 playbook doesn't reference the stale check.
- **Fix:** M1.2 Gap 5.

### Gap 6 — Kill-switch missing
- **Symptom:** 3 consecutive losing trades or DD > 10% don't block execution.
- **Root cause:** `kill_switch_state()` doesn't exist in journal.py.
- **Fix:** M1.4 §4.4.

### Gap 7 — No universe scan
- **Symptom:** L2 screens only from Airtable Superlist. New names not discovered.
- **Root cause:** `universe_scan.py` doesn't exist.
- **Fix:** M1.3 §3.1.

### Gap 8 — No catalyst calendar
- **Symptom:** Earnings, RUPS, dividends unknown until they happen.
- **Root cause:** `catalyst_calendar.py` doesn't exist.
- **Fix:** M1.3 §3.2.

### Gap 9 — No relative strength ranking
- **Symptom:** Sector candidates not ranked by RS; laggards selected alongside leaders.
- **Root cause:** `relative_strength.py` doesn't exist.
- **Fix:** M1.3 §3.3.

### Gap 10 — hit_rate_by() missing
- **Symptom:** L4 sizing can't check if the active pattern has < 40% win-rate.
- **Root cause:** function doesn't exist in journal.py.
- **Fix:** M1.4 §4.1.

### Gap 11 — Auto-lesson suggestion on close missing
- **Symptom:** Every trade close needs a manually entered lesson. Easy to skip.
- **Root cause:** `_draft_lesson_from_close` doesn't exist.
- **Fix:** M1.4 §4.2.

### Gap 12 — portfolio-state.json history not verified idempotent
- **Symptom:** Re-running same day may append duplicate rows.
- **Root cause:** `compute_portfolio_state()` save logic not audited.
- **Fix:** M1.4 §4.3.

### Gap 13 — Weekly review cron missing
- **Symptom:** `generate_weekly_review()` exists but never auto-runs.
- **Fix:** M1.5 §5.1.

### Gap 14 — Monthly review cron missing
- **Fix:** M1.5 §5.2.

### Gap 15 — Overnight macro not prefetched
- **Symptom:** L1 at 05:00 re-fetches live; risk of data unavailability.
- **Fix:** M1.5 §5.3.

### Gap 16 — No mid-day regime cron
- **Fix:** M1.5 §5.4.

### Gap 17 — No tape_runner (M3 dependency)
- **Fix:** M3.5.

### Gap 18 — No confluence score (M3 dependency)
- **Fix:** M3.6.

### Gap 19 — No konglo-mode (M3 dependency)
- **Fix:** M3.1.

### Gap 20 — No spring detector (M3 dependency)
- **Fix:** M3.3.

### Gap 21 — No imposter detector (M3 dependency)
- **Fix:** M3.4.

### Gap 22 — No volume-price classifier (M3 dependency)
- **Fix:** M3.2.

### Gap 23 — No auto-trigger (M3 dependency)
- **Fix:** M3.7.

### Gap 24 — No Go dashboard (M2 dependency)
- **Fix:** M2.

### Gap 25 — vault/data/*.json not dual-written to any DB
- **Fix:** M2.5.

### Gap 26 — L0 self-review not actionable (stale enforcement missing)
- **Symptom:** Self-review writes markdown but doesn't surface a programmatic list for next layer.
- **Root cause:** `thesis_status_summary()` returns the data but L0 doesn't read stale list first.
- **Fix:** M1.2 Gap 5 (already listed).

### Gap 27 — No kill-switch enforcement in execution inline gates
- **Symptom:** Even if `kill_switch_state()` existed, execution.md doesn't call it.
- **Fix:** M1.4 §4.4 adds the function + M1.2 Gap 5 wires it.

---

## What Already Works Well

- L0 playbook exists with 6 steps; `portfolio_health.py` computes equity, MTD, drawdown, exposure.
- L5 inline Confidence Gate documented with per-layer thresholds + hard overrides.
- `journal.py` has 6 upgraded capabilities: `log_lesson_v2`, `detect_recurring_mistakes`, `attribute_trade`, `confidence_calibration`, weekly/monthly generators, thesis-aware queries, `append_daily_layer_section`.
- `vault_sync.py` idempotent-upserts to Airtable.
- 360-portfolio: 3 gates at L2, BUY NOW at L3, Mode A/B at L4 — clean decision tree.
- `--settings` fallback pattern in cron dispatcher.
- MECE: each skill owns one concept, no duplication.
- Coverage matrix exists (`docs/coverage-matrix.md`).

---

## Priority Order for M1.2

1. Gap 5 (stale enforcement) — unblocks L0 drift check
2. Gap 2 (thesis-action state) — inter-layer state bus
3. Gap 1 (L5→L0 feedback) — closes the daily feedback loop
4. Gap 4 (calibration→sizing) — prevents over-confident sizing
5. Gap 3 (intraday regime) — mid-day risk adjustment (partial — function only; cron in M1.5)
6. Gap 6 (kill-switch) — moved to M1.4 since it depends on new helpers
