# Pre-Audit Observations

Notes written by Opus 4.7 during plan drafting on 2026-04-17. Use these as the starting seed for M1.1's audit matrix. You may find more gaps — add them. Do not remove these.

---

## What's already good

- Layer playbooks are numbered L0–L5, each with consistent structure (Inputs / Steps / Tools / Output / Telegram / Skills).
- Every layer appends to `vault/daily/<date>.md` via `journal.append_daily_layer_section()`. One file = one day of context.
- Cron dispatcher routes by WIB hour/min to one command file per window — no ambiguous schedules.
- Tool surface `api.py` is broad and well-labeled (portfolio, orderbook, broker, SID, screener, indicators, running trades).
- Execution has inline gates at L2/L3/L4 with hard overrides on DD and posture — good.
- `vault_sync.py` already idempotent-upserts to Airtable — model for SQLite sync.

## What limits fund-manager behaviour today

### Information flow gaps

1. **L5 → L0 feedback absent.** Orders land in `runtime/orders/YYYY-MM-DD.jsonl`, but L0 playbook never reads that file. Next day Claude doesn't review whether yesterday's fills matched plan. Fix: M1.2 Gap 1.

2. **Thesis action not promoted.** L0 Step 4 produces `intact | watch | reduce | exit-candidate` in Claude's head, but only records it into a free-form journal line. L2/L4 don't see it programmatically and may still re-promote a name flagged for exit. Fix: M1.2 Gap 2 (new `thesis-actions.json`).

3. **Intraday regime never rechecks.** L1 runs at 05:00 once. If IHSG breaks down at 11:00 with accelerating foreign outflow, L3 has no mechanism to flip posture for L4/L5. Fix: M1.2 Gap 3 + M1.5 midday cron.

4. **Calibration is computed but not enforced.** `journal.confidence_calibration()` exists; nothing calls it before sizing. An over-optimistic bucket will keep sizing at 3% risk even when win-rate has collapsed. Fix: M1.2 Gap 4.

5. **Stale thesis detection not enforced.** `thesis_status_summary()["stale"]` exists; nothing walks the list. Holds decay in plain sight. Fix: M1.2 Gap 5.

6. **No kill switch.** 3 consecutive losers, or drawdown > 10%, or a recurring pattern failing → nothing stops the next entry. Fix: M1.4 §4.4.

### Exploration gaps (these limit opportunity breadth)

7. **Screening is Superlist-first.** L2 playbook starts from Airtable `Superlist`. If an opportunity outside the Superlist shows up in daily flow (e.g. a new sector leader), nothing surfaces it. Fix: M1.3 §3.1 universe scan.

8. **No catalyst calendar.** Earnings, dividends, RUPS, rights issues drive moves. We have `api.get_emitten_info()` per ticker, but no forward calendar. We react to catalysts after the tape already knows. Fix: M1.3 §3.2.

9. **Relative strength not computed.** Given L1 picks a sector, we pick tickers by narrative fit + structure. We never rank RS within the sector — so we may hold the sector's laggards instead of its leaders. Fix: M1.3 §3.3.

10. **Pattern hit-rate not available.** `log_lesson_v2` collects `pattern_tag`, but no function aggregates hit-rate / expectancy per pattern. We can't tell if `shakeout-recovery` is actually paying vs `early-breakout`. Fix: M1.4 §4.1.

11. **Sector hit-rate not available.** Same structural gap as pattern — trades by sector aren't attributed. Fix: M1.4 §4.1 (same function, different dim).

12. **No performance_daily table.** Today's equity curve lives only in `portfolio-state.json` `history[]`. Weekly review is manual each time. Fix: M2.2 `performance_daily` table.

### Scheduling gaps

13. **Weekly review cron missing.** Script exists (`generate_weekly_review`), no cron entry. Fix: M1.5 §5.1.

14. **Monthly review cron missing.** Same. Fix: M1.5 §5.2.

15. **Overnight macro not prefetched.** L1 at 05:00 must re-fetch live — risks missing data if source is down. Fix: M1.5 §5.3 via 03:00 scrape.

### Journaling gaps

16. **`_draft_lesson_from_close` doesn't exist.** Every close should at minimum surface a candidate lesson; Claude confirms/refines. Today Claude must volunteer it, easy to skip. Fix: M1.4 §4.2.

17. **`portfolio-state.json` is overwritten, not appended.** Only the latest state survives unless code explicitly appends to `history[]`. `compute_portfolio_state()` current behaviour must be audited during M1.4 §4.3.

### Observability gaps

18. **No dashboard.** Everything is MD + JSON + Airtable. Fund manager can't glance at equity curve + current plans + today's signals in one place. This is the core of Mission 2.

19. **No signal stream.** L3 writes to monitoring log. If Boss O wants to watch live signals, he has to `tail -f` a file. Fix: M2.4 SSE stream.

20. **No per-ticker drill.** To review ANTM history, we must `grep` vault + runtime + airtable. Fix: M2.6 `/ticker/[ticker]` page.

---

## Confirmed structure facts (don't reconfirm, just use)

- Vault: `/home/lazywork/workspace/vault/` with folders `daily, thesis, journal, lessons, themes, reviews/{weekly,monthly}, layer-output/{l0..l5}, data, .templates`.
- JSON source of truth: `vault/data/` (gitignored).
- Env: `/home/lazywork/workspace/.env.local` holds `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `AIRTABLE_*`, `TELEGRAM_*`, broker creds.
- Cron dispatcher: `/home/lazywork/workspace/tools/trader/cron-dispatcher.sh` — add new branches here.
- Claude slash-commands for cron: `/home/lazywork/workspace/.claude/commands/trade/*.md`.
- Existing Airtable tables: `Superlist`, `Insights`, `Journal`, `Lessons`, `PortfolioLog` (some may not exist yet — `vault_sync._table_exists` silently skips).
- `journal.py` (`tools/trader/journal.py`) already has: `write_journal`, `log_trade`, `close_trade`, `log_lesson_v2`, `get_thesis`, `append_thesis_review`, `append_daily_layer_section`, `confidence_calibration`, `detect_recurring_mistakes`, `thesis_status_summary`, `attribute_trade`, `generate_weekly_review`, `generate_monthly_review`. Add the new helpers in M1.2 and M1.4.

---

## Ordering advice

Do M1 before M2. The M1 gaps fill `journal.py` and `portfolio_health.py` with the exact helpers M2.5 will POST. If M2 runs first, the client will have nothing to send.

Within M1, do 1.2 before 1.3 — 1.3 references `thesis-actions.json` created in 1.2.

Within M2, never start M2.3 (API) before M2.2 (schema). Never start M2.6 (dashboard) before M2.3 (API).

---

## M3 (Strategy Depth) — Pre-Found Observations

21. **No konglo-group awareness.** Thesis/screening treat every ticker as independent. A rotation from BREN to TPIA inside the Prajogo group reads as two separate moves. Fix: M3.1. Reference file already at `tools/trader/data/konglo_list.json` (12 groups, 59 tickers).

22. **Volume-price rules implicit, not codified.** `wyckoff.py` has some logic but no simple 4-quadrant classifier. Analysts keep re-deriving "volume up or down?" by hand. Fix: M3.2.

23. **Spring setup not distinct.** Today a sub-support wick with recovery is classed as `wick_shakeout`. That's too vague — a true spring has 4 specific conditions. Fix: M3.3.

24. **No imposter heuristic.** Retail-coded trades of 50K+ lots or automated same-second clusters get logged as retail flow. That's wrong; it's how operators hide. Fix: M3.4.

25. **Tape reading is tribal knowledge.** The 9-case pattern (HAKA/HAKI, walls eaten vs pulled, ganjelan, crossing, spam) lives only in prose. Not reproducible, not auditable. Fix: M3.5 — each case becomes a module with a standalone CLI.

26. **No single confluence number.** L2 says "5/5 criteria" but the criteria aren't weighted, aren't numeric, and don't include newer signals (imposter, spring, konglo, tape). Different cycles end up with different mental math. Fix: M3.6 — one score 0–100, four buckets.

27. **No auto-trigger path.** High-conviction live signals wait for the next scheduled cron. A well-formed ideal-markup pattern that fires at 10:07 doesn't reach Claude until 10:30. Fix: M3.7 — but keep strict budget + dedup; cost is real.

## Answer To "Is This Helpful?" (user question)

Yes. Specifically:

- **Volume-price rules** — correct Wyckoff framing, matches how real operators read tape. Worth adopting as-is.
- **Spring detection** — the 4-condition definition is tight. Our current `wick_shakeout` is looser; spring is a strict subset and deserves its own signal type.
- **Imposter score** — genuinely additive. We lose edge by assuming retail codes always mean retail.
- **Broker flow score / confluence** — our system already has all the data, just not the aggregation. Wrap it.
- **Tape reading 9 cases** — this is the most tactical. Each case is testable from `api.get_stockbit_orderbook` + `get_stockbit_running_trade` + `get_orderbook_delta` outputs. The separation between "eaten" and "pulled" walls is the most valuable distinction we are currently blind to.
- **Auto-trigger** — correct idea, but needs cost guards. The plan implements dedup (1-hour TTL per ticker+kind) and a daily budget (5 triggers max). Telegram-first always, Claude invocation second.

What to skip:
- "Relatives bragging about profits" as an exit trigger — not codifiable, leave as journal anecdote.
- Subjective "psikologi ritel" commentary — keep in skill files as color, not as decision rules.
