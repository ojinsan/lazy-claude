# Mission 1 — Layer Integration Audit & Fix

**Goal:** Turn L0–L5 from six parallel layers into one tightly coupled fund-manager pipeline. Each layer must (a) consume a named output from the previous layer, (b) write a named output consumed by a downstream layer, (c) feed information back into L0's next-day review.

**Why this matters:** today layers run but information leaks. L3 sees a distribution signal, updates a thesis, but L0 tomorrow may still carry a stale "intact" flag because the state isn't recomputed. The screener hasn't widened the universe, so we never see opportunity outside the existing Superlist. Weekly reviews don't run. Calibration never feeds back into sizing. We trade on what we already know and miss the rest.

---

## Phase M1.1 — Produce the Audit Report

### Goal
A single document describing every layer's inputs, outputs, and the concrete file paths / scripts / JSON keys through which they travel. Also list gaps.

### Steps

1. Create output folder:
   ```bash
   mkdir -p /home/lazywork/workspace/docs/fund-manager-plan/output
   ```

2. For each layer (L0, L1, L2, L3, L4, L5), read its playbook at `/home/lazywork/workspace/playbooks/trader/layer-N-*.md`. For each, extract:
   - **Reads:** explicit inputs (file paths, API calls, Airtable tables, env vars).
   - **Writes:** explicit outputs (file paths, JSON keys, MD sections, Airtable tables).
   - **Skills loaded:** from the "Skills To Load" block.
   - **Cron trigger:** from `tools/trader/cron-dispatcher.sh` + `runtime/crontab-updated.txt`.

3. Build a matrix in `docs/fund-manager-plan/output/m1-audit.md`:

   ```markdown
   | Producer | Artifact | Consumer | Current state |
   |----------|----------|----------|---------------|
   | L0 | vault/data/portfolio-state.json | L2 Gate 2/3, L4 sizing | OK |
   | L1 | aggression posture | L2, L4, L5 | OK (verbal in daily note) |
   | L2 | Airtable Superlist | L3 track, L4 plan | OK |
   | L3 | runtime/monitoring/YYYY-MM-DD.md | L4 Mode B | OK |
   | L4 | runtime/tradeplans/YYYY-MM-DD.md | L5 entry | OK |
   | L5 | runtime/orders/YYYY-MM-DD.jsonl | L0 next day | GAP — L0 doesn't read it |
   | L3 | append_thesis_review() | L0 Step 4 | GAP — L0 reads thesis file but not flagged-for-exit state |
   | L5 close | journal.log_trade → transactions.json | weekly review | OK |
   | — | IDX universe beyond Superlist | L2 | GAP — no universe expansion |
   | — | earnings calendar | L1/L2 | GAP — no calendar |
   | — | calibration bucket drift | L4/L5 sizing | GAP — computed but not enforced |
   ```

4. Below the matrix, list **every gap** with this format:

   ```markdown
   ### Gap: <name>
   - **Symptom:** what Claude does wrong today because of it.
   - **Root cause:** which script / skill / playbook is missing the wiring.
   - **Fix owner:** which phase in this plan addresses it.
   ```

### Verify
- [ ] Matrix has at least 12 rows.
- [ ] Every layer appears as both Producer and Consumer at least once.
- [ ] At least 10 gaps listed below the matrix.
- [ ] Every "GAP" entry is referenced by a later phase in this plan.

### Commit
`[M1.1] Audit L0-L5 integration and enumerate gaps`

---

## Phase M1.2 — Close Inter-Layer Gaps

### Goal
Every gap flagged in M1.1 that is about layer-to-layer wiring gets fixed by editing playbooks and/or writing a tiny helper.

### Gaps to Fix in This Phase

#### Gap 1 — L5 → L0 feedback loop missing

- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-0-portfolio.md`, "## Inputs" section. Add:
  > - Yesterday's orders from `runtime/orders/YYYY-MM-DD.jsonl` (last trading day)
- Add a new Step between Step 1 and Step 2:
  > ### Step 1.5 — Yesterday's Execution Review
  > Read `runtime/orders/<prev-trading-day>.jsonl`. For each BUY: did it fill? Is the position still open? Is it aligned with a current-day hold?  For each SELL: was it a planned exit or stop-out? Record outcome in the self-review at Step 6.
- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add a helper:
  ```python
  def load_previous_orders(days_back: int = 1) -> list[dict]:
      """Return all order rows from the last N trading days (reverse chronological)."""
  ```

#### Gap 2 — Thesis-action state not promoted to Superlist

- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add:
  ```python
  def set_thesis_action(ticker: str, action: str) -> None:
      """action in {hold, add-to, reduce, exit-candidate, stale}. Writes to vault/data/thesis-actions.json."""
  ```
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-0-portfolio.md` Step 4: after `Mark intact | watch | reduce | exit-candidate | needs refresh`, add:
  > Call `journal.set_thesis_action(ticker, action)` for each hold.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-2-stock-screening.md` "## Portfolio Health (Run First)". Add:
  > Before screening, call `journal.get_thesis_actions()`. If a ticker is marked `exit-candidate` today, never promote a same-day add for that name. Screening may still find substitution candidates in the same sector.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-4-trade-plan.md` "## Inputs": add `vault/data/thesis-actions.json`.

#### Gap 3 — L1 regime flips mid-day not propagated to L3/L4

- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-3-stock-monitoring.md`. Add a new section after "## What To Monitor":
  > ### Mid-Day Regime Check
  > At 11:30 WIB and again at 14:00 WIB, re-evaluate IHSG posture:
  > - If IHSG down >1% AND foreign outflow accelerating → flip posture down by 1 notch.
  > - Write the flip to `vault/data/regime-intraday.json` via `journal.set_intraday_posture(posture, reason)`.
  > - Flag all open tradeplans for size review in the next cycle.
- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add `set_intraday_posture(posture: int, reason: str)`.

#### Gap 4 — Calibration doesn't feed sizing

- **Edit** `/home/lazywork/workspace/skills/trader/execution.md` "## Sizing Formula". Before the `capital_at_risk = total_capital × risk_pct` line, add:
  > Pre-check calibration: call `journal.confidence_calibration(days=90)`. If the conviction bucket you plan to use is over-optimistic by more than 0.2 (actual win-rate < declared), **cap risk_pct at 1%** regardless of conviction label. Record the cap reason in the tradeplan notes.
- **Edit** `/home/lazywork/workspace/tools/trader/tradeplan.py` — when building a plan, call `confidence_calibration` and attach the result as a `calibration` field in the output dict.

#### Gap 5 — Stale-thesis enforcement not scripted

- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add a CLI entry point:
  ```python
  if __name__ == "__main__" and sys.argv[1:2] == ["stale"]:
      print(json.dumps(thesis_status_summary()["stale"], indent=2))
  ```
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-0-portfolio.md` Step 4. Add at the top:
  > Run `python tools/trader/journal.py stale` first. Any ticker returned MUST have a drift-check this morning even if otherwise intact.

### Verify
- [ ] All five edits above applied.
- [ ] `python tools/trader/journal.py stale` runs and prints JSON.
- [ ] `load_previous_orders()`, `set_thesis_action()`, `get_thesis_actions()`, `set_intraday_posture()` all have a unit-style smoke test (just import and call with a stub ticker — confirm no exception).
- [ ] Open L0 playbook and trace: every Step now has a named input AND a named output.

### Commit
`[M1.2] Wire L5→L0 feedback, thesis-action state, intraday regime, calibration-to-sizing, stale enforcement`

---

## Phase M1.3 — Expand Universe Exploration

### Goal
Stop starting L2 from a pre-built Superlist. Scan a broader universe each morning and let L2 narrow it down. Add a catalyst / event calendar so we don't miss earnings-driven moves.

### Deliverables

#### 3.1 — Daily universe scan

- **Create** `/home/lazywork/workspace/tools/trader/universe_scan.py`:
  - Calls `api.run_screener_template(template_id)` for Boss O's saved liquidity template (fall back to `run_screener_custom` with: `avg_volume > 1M shares`, `last_price between 100 and 50000`, `market_cap > 500B`).
  - Outputs `vault/data/universe-YYYY-MM-DD.json` — list of `{ticker, last, vol_ratio, sector}`.
  - Idempotent: re-running same day overwrites.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-2-stock-screening.md` "## Input". Insert before existing lines:
  > - Today's universe: `vault/data/universe-YYYY-MM-DD.json` (run `tools/trader/universe_scan.py` first if missing).
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-2-stock-screening.md` "## Portfolio Health (Run First)". After the hold loop, add:
  > ### Universe Sweep
  > Walk the universe JSON. For any non-Superlist ticker where vol_ratio > 1.5× AND sector matches L1 theme → add to a "watch candidates" list. Run the 5-criteria screen on each candidate. High-conviction candidates promote to Superlist.

#### 3.2 — Catalyst calendar

- **Create** `/home/lazywork/workspace/tools/trader/catalyst_calendar.py`:
  - Pulls upcoming earnings, dividends, RUPS, rights issues for Superlist tickers via `api.get_emitten_info()` + scrape of IDX corporate action page if needed.
  - Outputs `vault/data/catalyst-YYYY-MM-DD.json` — `[{ticker, date, event_type, note}]`, forward 14 days.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-1-global-context.md` "## What To Gather" → "### Indonesia". Add:
  > - Upcoming catalysts this week from `vault/data/catalyst-<today>.json` — earnings, dividends, rights issues. Note any within 2 trading days.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-4-trade-plan.md` "## Inputs". Add:
  > - Catalyst calendar: `vault/data/catalyst-<today>.json`. If a catalyst falls within 3 trading days, either use it as the trigger OR explicitly state "avoid entry pre-catalyst".

#### 3.3 — Relative strength rank

- **Create** `/home/lazywork/workspace/tools/trader/relative_strength.py`:
  - Takes a sector (from L1 theme). Ranks all universe tickers in that sector by 5-day and 20-day relative return vs IHSG. Outputs top 10 to stdout.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-2-stock-screening.md` "## Screening Criteria". After criterion 3, insert:
  > 3.5. **Relative strength** — `python tools/trader/relative_strength.py --sector energy --days 20`. Prefer names in the top 5 of their sector; deprioritize bottom 5 unless clear accumulation signal overrides.

### Cron Updates

- **Edit** `/home/lazywork/workspace/tools/trader/cron-dispatcher.sh`. In the `04:30` block, before the L0 Claude call, add:
  ```bash
  python "$WORKSPACE/tools/trader/universe_scan.py" >> "$LOG" 2>&1 || log "⚠ universe_scan failed"
  python "$WORKSPACE/tools/trader/catalyst_calendar.py" >> "$LOG" 2>&1 || log "⚠ catalyst_calendar failed"
  ```

### Verify
- [ ] `python tools/trader/universe_scan.py` writes a JSON file with ≥50 tickers.
- [ ] `python tools/trader/catalyst_calendar.py` writes a JSON file (can be empty; should not error).
- [ ] `python tools/trader/relative_strength.py --sector energy --days 20` prints 10 lines.
- [ ] L2 playbook references all three new artifacts.

### Commit
`[M1.3] Add universe scan, catalyst calendar, relative strength; wire into L1/L2/L4`

---

## Phase M1.4 — Upgrade Journaling

### Goal
Make the journal genuinely useful: per-sector hit rate, per-pattern attribution, automatic lesson extraction for close events.

### Deliverables

#### 4.1 — Per-sector + per-pattern hit rate

- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add:
  ```python
  def hit_rate_by(dim: str, days: int = 90) -> list[dict]:
      """dim in {sector, pattern_tag, setup, conviction, layer_origin}.
      Returns [{key, trades, wins, win_rate, avg_r, expectancy}] sorted by trades desc."""
  ```
- **Edit** `/home/lazywork/workspace/skills/trader/journal-review.md` "## When To Call Each Capability". Add two rows:
  > | L4 plan, before sizing | `hit_rate_by('pattern_tag', 90)` | If the active pattern has <40% win-rate in the last 90d → force risk_pct = 1%. |
  > | L0 Step 5 | `hit_rate_by('sector', 90)` | Surfaces which sector bets actually pay. |

#### 4.2 — Automatic lesson extraction on close

- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. In `close_trade()`, after pnl is computed, add:
  ```python
  draft_lesson = _draft_lesson_from_close(trade_row, pnl_pct)
  # _draft_lesson_from_close returns {category, severity, pattern_tag, lesson_text}
  # based on simple rules: pnl_pct < -5 → exit_timing/high;
  # pnl_pct > +10 → thesis_quality/low (record what worked);
  # pnl within ±2% → psychology/low (indecision).
  return {..., "suggested_lesson": draft_lesson}
  ```
  This is a **suggestion** — the caller still confirms and calls `log_lesson_v2`.

#### 4.3 — Daily portfolio snapshot to vault/data

- **Edit** `/home/lazywork/workspace/tools/trader/portfolio_health.py`. In `compute_portfolio_state()`, after computing the state dict, append a row to `vault/data/portfolio-state.json` under `history[]`:
  ```json
  {"date":"2026-04-16","equity":53000000,"cash":10000000,"deployed":42000000,"utilization_pct":79.2,"drawdown_pct":0.0,"top_exposure":"IMPC 20.48%","posture":"DEFENSIVE"}
  ```
  Idempotent — replace same-date row, don't append duplicates.

#### 4.4 — Kill-switch detection

- **Edit** `/home/lazywork/workspace/tools/trader/journal.py`. Add:
  ```python
  def kill_switch_state(days: int = 5) -> dict:
      """Return {'active': bool, 'reason': str} if any of:
      - 3 consecutive losing trades
      - DD > 10% from HWM
      - Same pattern_tag lost 3 trades in last 5 sessions
      """
  ```
- **Edit** `/home/lazywork/workspace/skills/trader/execution.md` "## Hard Safety Rules". Add:
  > - Before any entry, call `journal.kill_switch_state()`. If `active` → no new entries today regardless of other checks.

### Verify
- [ ] `python -c "import sys; sys.path.insert(0,'tools/trader'); import journal; print(journal.hit_rate_by('sector'))"` runs.
- [ ] Closing a trade in dev returns `suggested_lesson`.
- [ ] Running `portfolio_health.compute_portfolio_state()` writes a `history[]` row.
- [ ] `journal.kill_switch_state()` returns a dict with `active` and `reason` keys.

### Commit
`[M1.4] Per-dim hit-rate, auto-lesson suggestion, portfolio history, kill-switch`

---

## Phase M1.5 — Upgrade Scheduling

### Goal
Close the scheduling gaps: weekly review, monthly review, overnight macro prep, mid-day regime check.

### Deliverables

#### 5.1 — Weekly review cron (Sunday 20:00 WIB)

- **Edit** `/home/lazywork/workspace/tools/trader/cron-dispatcher.sh`. Add a new branch before "Off-hours":
  ```bash
  # ── Weekly review: Sunday 20:00 WIB ─────────────────────────────────────
  elif [[ $(TZ='Asia/Jakarta' date +%u) -eq 7 && $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 ]]; then
      log "→ WEEKLY REVIEW start"
      run_claude_job "$COMMAND_DIR/weekly-review.md"
      log "← WEEKLY REVIEW done"
  ```
- **Create** `/home/lazywork/workspace/.claude/commands/trade/weekly-review.md` (a new slash command file). Content:
  ```markdown
  # Weekly Review
  1. Call `python -c "import sys; sys.path.insert(0,'tools/trader'); import journal; print(journal.generate_weekly_review())"`.
  2. Produce `vault/reviews/weekly/YYYY-Www.md` with: equity chg, trades, best/worst name, pattern hit-rates, lessons added, themes to retire, next-week focus.
  3. Append one-line summary to `vault/daily/<today>.md` under `## Auto-Appended`.
  4. Send `weekly` via `skills/trader/telegram-notify.md`.
  ```

#### 5.2 — Monthly review cron (last business day 20:00 WIB)

- **Edit** `cron-dispatcher.sh`. Add:
  ```bash
  # ── Monthly review: last business day 20:00 WIB ────────────────────────
  elif [[ $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 && $(TZ='Asia/Jakarta' date -d "+1 day" +%m) != $(TZ='Asia/Jakarta' date +%m) && $(TZ='Asia/Jakarta' date +%u) -le 5 ]]; then
      log "→ MONTHLY REVIEW start"
      run_claude_job "$COMMAND_DIR/monthly-review.md"
      log "← MONTHLY REVIEW done"
  ```
- **Create** `.claude/commands/trade/monthly-review.md` — mirrors weekly but calls `generate_monthly_review()`.

#### 5.3 — Overnight macro scrape (03:00 WIB)

- **Edit** `cron-dispatcher.sh`. Add:
  ```bash
  # ── Overnight macro scrape: 03:00 WIB ──────────────────────────────────
  elif [[ $WIB_HOUR -eq 3 && $WIB_MIN -eq 0 ]]; then
      log "→ OVERNIGHT MACRO start"
      python "$WORKSPACE/tools/trader/overnight_macro.py" >> "$LOG" 2>&1 || log "⚠ overnight_macro failed"
      log "← OVERNIGHT MACRO done"
  ```
- **Create** `/home/lazywork/workspace/tools/trader/overnight_macro.py`:
  - Fetches: US close S&P/Nasdaq/Dow, oil, gold, coal, HSI close, DXY, US10Y.
  - Sources: free endpoints (Yahoo Finance via `yfinance`, or TradingView JSON). Prefer `yfinance` — already in Python ecosystem.
  - Output `vault/data/overnight-YYYY-MM-DD.json`.
- **Edit** `/home/lazywork/workspace/playbooks/trader/layer-1-global-context.md` "## What To Gather" → "### Global Markets". Add:
  > - Read `vault/data/overnight-<today>.json` for last-night close. Do not re-fetch.

#### 5.4 — Mid-day regime check (11:30 and 14:00 WIB)

Already partially covered in M1.2 Gap 3. This phase wires the cron:

- **Edit** `cron-dispatcher.sh`. Add:
  ```bash
  # ── Mid-day regime check: 11:30 WIB ────────────────────────────────────
  elif [[ $WIB_HOUR -eq 11 && $WIB_MIN -eq 30 ]]; then
      log "→ MIDDAY REGIME start"
      run_claude_job "$COMMAND_DIR/midday-regime.md"
      log "← MIDDAY REGIME done"
  ```
  Same pattern for 14:00.
- **Create** `.claude/commands/trade/midday-regime.md`. Calls L1 posture re-eval + writes `regime-intraday.json`.

### Verify
- [ ] `cron-dispatcher.sh` has five new branches (weekly, monthly, overnight, midday x2).
- [ ] `python tools/trader/overnight_macro.py` writes a JSON with ≥8 tickers of data.
- [ ] All new command files exist under `.claude/commands/trade/`.
- [ ] Dry-run each cron branch by exporting `WIB_HOUR=20 WIB_MIN=0` and sourcing the script logic.

### Commit
`[M1.5] Add weekly/monthly review + overnight macro + mid-day regime crons`

---

## Phase M1.6 — Integration Smoke Test

### Goal
Simulate one trading day end-to-end, on paper, verify data flows layer-to-layer without gaps.

### Steps

1. Pick yesterday's date (or use a fixture date). Export `SIMULATED_DATE=2026-04-15` in the shell.
2. **L0** — Run `python tools/trader/portfolio_health.py` (or call from Claude). Verify:
   - `vault/data/portfolio-state.json` has a row for today.
   - Every hold has a row in `vault/data/thesis-actions.json`.
3. **L1** — Run overnight macro, then L1 playbook. Verify:
   - `vault/data/overnight-<date>.json` exists.
   - Daily note L1 section written.
4. **L2** — Run universe scan, catalyst calendar, then L2 playbook. Verify:
   - Universe JSON ≥50 tickers.
   - Shortlist references `thesis-actions.json` (excludes exit-candidates).
   - Relative-strength ran for the top L1 sector.
5. **L3** — Simulate a monitoring cycle with any open ticker. Verify:
   - `runtime/monitoring/<date>.md` has an entry.
   - If a signal fired, `append_thesis_review` was called.
6. **L4** — Run tradeplan script for one ticker from the shortlist. Verify:
   - Tradeplan file contains `calibration` field (from 1.2 Gap 4).
   - Tradeplan references today's catalyst calendar.
7. **L5** — Dry-run execute (log only, don't actually place). Verify:
   - `runtime/orders/<date>.jsonl` has a row (or is explicitly empty with a reason).
   - `journal.log_trade` called if order placed.
8. **Next morning L0** — re-run and verify:
   - It reads yesterday's orders (Gap 1 Step 1.5).
   - Self-review comments on the orders.
9. Write a summary into `vault/journal/simulated-<date>.md` describing what worked, what was noisy, what was missing.

### Verify
- [ ] All 9 steps ran without an uncaught exception.
- [ ] The smoke-test note `vault/journal/simulated-<date>.md` exists with one bullet per step.
- [ ] At least one end-to-end information flow is visibly traced (e.g., L1 posture → L4 sizing cap → L5 skip).

### Commit
`[M1.6] End-to-end smoke test; integration holes closed`

---

## Mission 1 Complete When

- [ ] `docs/fund-manager-plan/output/m1-audit.md` exists and is >150 lines.
- [ ] All five gap categories (feedback loop, thesis-action, intraday regime, calibration, stale) are wired.
- [ ] Universe scan + catalyst + relative strength run daily.
- [ ] Weekly/monthly/overnight/midday crons are live.
- [ ] Smoke-test note shows every layer producing AND consuming at least one named artifact.
- [ ] `skills/trader/CLAUDE.md`, `tools/CLAUDE.md`, `playbooks/trader/CLAUDE.md` all updated to reference the new skills/scripts/commands.

**Hand off to Mission 2.**
