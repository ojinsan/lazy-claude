# Trading Agents Revamp — Progress Tracker

Updated as each detail spec (L0–L5) consumes or improves tools.

Legend for `status`:
- `live` — used by new system, unchanged
- `improved` — used by new system, rewritten/extended
- `unused` — not referenced by new system, candidate for archive
- `deprecate-candidate` — scheduled for removal in future cleanup

## `tools/_lib/*.py` — Used By

| Tool | Used-by-layer | Status | Notes |
|------|---------------|--------|-------|
| `current_trade.py` | L0, L1, L2, L3, L4, L5 | live | spec #1 — shared schema + save/load |
| `ratelimit.py` | L2, L3, L5 | live | spec #1 — token buckets |
| `claude_model.py` | L0, L1, L2, L4 | live | spec #1 — Opus↔openclaude fallback |
| `daily_note.py` | L0 (L1/L3/L5 later) | live | spec #2 — shared daily-note append |

## `tools/trader/*.py` — Used By

| Tool | Used-by-layer | Status | Notes |
|------|---------------|--------|-------|
| `airtable_client.py` |   | live |   |
| `api.py` |   | live |   |
| `auto_trigger.py` |   | live |   |
| `broker_profile.py` |   | live |   |
| `catalyst_calendar.py` |   | live |   |
| `config.py` |   | live |   |
| `confluence_score.py` |   | live |   |
| `fund_manager_client.py` |   | live |   |
| `imposter_detector.py` |   | live |   |
| `indicators.py` |   | live |   |
| `journal.py` | L0 | live | `load_previous_orders(365)` sources MtD/YtD rollup (Carina has no history endpoint) |
| `konglo_flow.py` |   | live |   |
| `konglo_loader.py` |   | live |   |
| `macro.py` |   | live |   |
| `market_structure.py` |   | live |   |
| `narrative.py` |   | live |   |
| `orderbook_poller.py` |   | live |   |
| `orderbook_ws.py` |   | live |   |
| `overnight_macro.py` |   | live |   |
| `portfolio_health.py` |   | live |   |
| `psychology.py` |   | live |   |
| `realtime_listener.py` |   | live |   |
| `relative_strength.py` |   | live |   |
| `running_trade_poller.py` |   | live |   |
| `runtime_eod_publish.py` |   | live |   |
| `runtime_layer1_context.py` |   | live |   |
| `runtime_layer2_screening.py` |   | live |   |
| `runtime_monitoring.py` |   | live |   |
| `runtime_summary_30m.py` |   | live |   |
| `sb_screener_create.py` |   | live |   |
| `sb_screener_hapcu_foreign_flow.py` |   | live |   |
| `screener.py` |   | live |   |
| `sid_tracker.py` |   | live |   |
| `spring_detector.py` |   | live |   |
| `stockbit_auth.py` |   | live |   |
| `stockbit_headers.py` |   | live |   |
| `stockbit_login.py` |   | live |   |
| `stockbit_screener.py` |   | live |   |
| `tape_runner.py` |   | live |   |
| `l0_synth.py` | L0 | live | mechanical data reshaping for L0 playbook (spec #2) |
| `telegram_client.py` | L0 | live |   |
| `think.py` |   | live |   |
| `tick_walls.py` |   | live |   |
| `tradeplan.py` |   | live |   |
| `universe_scan.py` |   | live |   |
| `vault_sync.py` |   | live |   |
| `vp_analyzer.py` |   | live |   |
| `watchlist_4group_scan.py` |   | live |   |
| `wyckoff.py` |   | live |   |

## Archived references

From grep of `archive/` for `tools/trader/<X>` mentions. Use this to know which scripts the old system actually invoked, when resurrecting logic for new specs. Items marked `(gone)` no longer exist in `tools/trader/` — pure historical references.

| Tool | Mentioned in archived files |
|------|-----------------------------|
| `tools/trader/airtable_client.py` | 9 |
| `tools/trader/api.py` | 38 |
| `tools/trader/auto_layer4_trigger.py` (gone) | 1 |
| `tools/trader/auto_trigger.py` | 3 |
| `tools/trader/broker_profile.py` | 8 |
| `tools/trader/catalyst_calendar.py` | 1 |
| `tools/trader/confluence_score.py` | 1 |
| `tools/trader/data.py` (gone) | 2 |
| `tools/trader/imposter_detector.py` | 1 |
| `tools/trader/indicators.py` | 5 |
| `tools/trader/journal.py` | 15 |
| `tools/trader/konglo_flow.py` | 2 |
| `tools/trader/macro.py` | 2 |
| `tools/trader/market_structure.py` | 4 |
| `tools/trader/narrative.py` | 3 |
| `tools/trader/notification_system.py` (gone) | 1 |
| `tools/trader/orderbook_poller.py` | 12 |
| `tools/trader/orderbook_ws.py` | 8 |
| `tools/trader/portfolio_health.py` | 7 |
| `tools/trader/psychology.py` | 2 |
| `tools/trader/realtime_listener.py` | 6 |
| `tools/trader/relative_strength.py` | 1 |
| `tools/trader/running_trade_poller.py` | 14 |
| `tools/trader/runtime_eod_publish.py` | 2 |
| `tools/trader/runtime_layer1_context.py` | 3 |
| `tools/trader/runtime_layer2_screening.py` | 2 |
| `tools/trader/runtime_monitoring.py` | 5 |
| `tools/trader/runtime_summary_30m.py` | 4 |
| `tools/trader/sb_screener_create.py` | 7 |
| `tools/trader/sb_screener_hapcu_foreign_flow.py` | 4 |
| `tools/trader/screener.py` | 1 |
| `tools/trader/sid_tracker.py` | 8 |
| `tools/trader/spring_detector.py` | 1 |
| `tools/trader/stockbit_screener.py` | 1 |
| `tools/trader/tape.py` (gone) | 1 |
| `tools/trader/tape_runner.py` | 2 |
| `tools/trader/telegram_client.py` | 13 |
| `tools/trader/tick_walls.py` | 4 |
| `tools/trader/tradeplan.py` | 3 |
| `tools/trader/universe_scan.py` | 1 |
| `tools/trader/vp_analyzer.py` | 1 |
| `tools/trader/watchlist_4group_scan.py` | 1 |
| `tools/trader/wyckoff.py` | 3 |

## External MCP tools (used-by-layer)

| MCP tool | Used-by-layer | Notes |
|----------|---------------|-------|
| `mcp__lazytools__carina_portfolio` | L0 | **new** — bulk summary + positions (one call) |
| `mcp__lazytools__carina_cash_balance` |   | kept for ad-hoc, not used by L0 |
| `mcp__lazytools__carina_position_detail` |   | kept for ad-hoc, not used by L0 |
| `mcp__lazytools__carina_orders` |   | today-only; Carina has no history endpoint. L0 uses `journal.load_previous_orders` instead |

## L0 — known gaps / follow-ups

Not blockers for spec #2 acceptance; revisit when the trigger appears.

| # | Gap | Trigger to fix |
|---|-----|----------------|
| 1 | Fractional-lot truncation. `api.get_portfolio()` returns float `lots` when shares<100; `Holding.lot:int` coerces to 0. GOTO dry-run: 77 residual shares → `lot=0`. Data loss for odd-lot tails. | First time a residual position matters (exit plan or reconciliation). Fix by changing `Holding.lot` to float OR tracking `shares` separately. |
| 2 | MtD/YtD realized is local-only. `journal.load_previous_orders` reads `runtime/orders/*.jsonl` which only exists from L5 go-live onward. Pre-system trades invisible until backfilled. | When Boss wants accurate YtD. Path: Playwright-scrape Stockbit web transaction history into runtime/orders/*.jsonl. Defer until L5 has run ≥1 month. |
| 3 | Opus→openclaude fallback paths in L0 steps 4 & 5 never exercised. Dry-run had no redflag/thesis-drift + Opus succeeded first try on aggressiveness. Untested on live-fail path. | First time Opus 429s or returns invalid tier. Monitor via `runtime/history/*/l0-*.json` `status=error` snapshots. |
| 4 | `vault/thesis/` dir missing. Every holding tagged `no thesis:` — correct per playbook §4.1 but Boss never told to maintain thesis files. | When Boss starts writing theses manually. No code change needed; playbook already reads on-demand. |
| 5 | Orphaned MCP tools `carina_cash_balance`, `carina_position_detail`, `carina_orders`. Kept live for ad-hoc use; not called by any layer. | Archive-sweep after all layers ship. Candidates for removal if still unused by spec #8 time. |
| 6 | Hardcoded `days_back=365` in playbook journal call. Picks up all history; fine until bot runs >1 yr then quietly stops covering full YtD when `Jan-01 > today-365d`. | Mid-January of year 2 of live operation. Fix: compute `days_back = (today - year_start).days + lookback_buffer`. |

## Live dependencies on slash-command dir

- `tools/trader/cron-dispatcher.sh` still references `.claude/commands/trade/`. Resolves to new stubs today. Revisit per spec #8 (orchestration).

## Spec status

| Spec | Scope | Status |
|------|-------|--------|
| #0 | Master | draft pushed |
| #1 | Core + Archive/Scaffold | in progress |
| #2 | L0 Portfolio | complete (dry-run passed 2026-04-20) |
| #3 | L1 + L1-A + L1-B | not started |
| #4 | L2 Screening | not started |
| #5 | L3 Monitoring | not started |
| #6 | L4 Trade Plan | not started |
| #7 | L5 Execute | not started |
| #8 | Orchestration / CRON | not started |
