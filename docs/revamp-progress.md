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
| `current_trade.py` | L0, L1, L2, L3, L4, L5 | improved | spec #1 — shared schema + save/load; spec #5 added `trader_status.intraday_notch:int`; spec #6 added `ListItem.plan:TradePlan`; spec #7 added `ExecutionState`+`FillEvent`+`ListItem.execution` |
| `ratelimit.py` | L2, L3, L5 | live | spec #1 — token buckets |
| `claude_model.py` | L0, L1, L2, L3, L4 | live | spec #1 — Opus↔openclaude fallback; spec #5 uses both paths (openclaude judge + Opus BUY-NOW confirm); spec #6 L4 Opus plan synth |
| `daily_note.py` | L0, L1, L2, L3, L4 | live | spec #2 — shared daily-note append; spec #5 event-driven L3 entries; spec #6 L4 plan block |

## `tools/trader/*.py` — Used By

| Tool | Used-by-layer | Status | Notes |
|------|---------------|--------|-------|
| `airtable_client.py` |   | live |   |
| `api.py` | L1, L2, L3, L4 | live | `rag_search` via `fund_manager_client`; `_stockbit_get` used by retail-avoider; `get_price_history(60d)` for L2 dim-1; `get_price` + `get_stockbit_index('IHSG')` for L3; `compute_indicators_from_price_data` for L4 ATR |
| `auto_trigger.py` |   | live |   |
| `broker_profile.py` | L2 | live | `analyze_players(ticker)` — L2 dim-2 smart-money read |
| `catalyst_calendar.py` | L1 | live | `build()` populates today's events for L1 Opus prompt |
| `config.py` |   | live |   |
| `confluence_score.py` |   | live |   |
| `fund_manager_client.py` | L1 | live | `rag_search` + `get_watchlist` (Lark seed merge) |
| `imposter_detector.py` |   | live |   |
| `indicators.py` |   | live |   |
| `journal.py` | L0 | live | `load_previous_orders(365)` sources MtD/YtD rollup (Carina has no history endpoint) |
| `konglo_flow.py` |   | live |   |
| `konglo_loader.py` | L2 | live | `group_for(ticker)` — feeds `konglo_in_l1_sectors` flag in L2 dim-2 |
| `l1a_healthcheck.py` | L1 | live | GET /api/v1/insights/last; fresh/stale gate for L1 playbook |
| `l1_synth.py` | L1 | live | pure validators + pool union + telegram recap format (spec #3) |
| `macro.py` | L1 | live | `assess_regime()` live probe into L1 Opus prompt |
| `market_structure.py` | L4 | live | spec #6 — `analyze_market_structure` provides S/R + wyckoff + swing points for L4 entry/stop placement |
| `narrative.py` | L1 | live | seeds narrative source tagging convention |
| `orderbook_poller.py` | L3 | live | live orderbook polling → `runtime/monitoring/orderbook_state/{t}.json` (consumed by L3) |
| `orderbook_ws.py` |   | live |   |
| `overnight_macro.py` | L1 | live | `vault/data/overnight-YYYY-MM-DD.json` cache; `fetch_all()` fallback |
| `portfolio_health.py` |   | live |   |
| `psychology.py` |   | live |   |
| `realtime_listener.py` |   | live |   |
| `relative_strength.py` | L2 | live | `rank([ticker], days=20)` for RS value + `_rs_rank` sector rank in L2 dim-1 |
| `running_trade_poller.py` | L3 | live | last-10m running trades → `runtime/monitoring/realtime/{t}-run.jsonl` (consumed by L3) |
| `runtime_eod_publish.py` |   | live |   |
| `runtime_layer1_context.py` |   | live |   |
| `runtime_layer2_screening.py` |   | live |   |
| `runtime_monitoring.py` | L3 | live | 10m cron producer: writes orderbook_state + running-trade JSONL files for L3 gather |
| `runtime_summary_30m.py` |   | live |   |
| `sb_screener_create.py` |   | live |   |
| `sb_screener_hapcu_foreign_flow.py` | L1, L2, L3 | live | `post_screener(save=False)` probes smart-money HAPCU flow; L2 caches yesterday's snapshot; L3 uses `foreign_net_flow_today()` for 12:00 intraday-notch check |
| `sb_screener_retail_avoider.py` | L1, L2 | live | fetch retail + smart broker codes; L2 caches yesterday's snapshot for dim-2 |
| `screener.py` |   | live |   |
| `sid_tracker.py` | L2 | live | `check_sid(ticker)` — direction/streak/change-% fed into L2 dim-2 |
| `spring_detector.py` | L2, L3 | live | `detect(ticker)` — L2 sets `judge_floor=strong` on hit; L3 uses as intraday BUY-NOW gate alternative to thick-wall |
| `stockbit_auth.py` |   | live |   |
| `stockbit_headers.py` |   | live |   |
| `stockbit_login.py` |   | live |   |
| `stockbit_screener.py` |   | live |   |
| `tape_runner.py` | L3 | live | `snapshot(t)` — composite tape state (ideal_markup/healthy_markup/spring_ready/fake_support/distribution_trap/...) + confidence, per-cycle L3 input |
| `l0_synth.py` | L0 | live | mechanical data reshaping for L0 playbook (spec #2) |
| `telegram_client.py` | L0, L1, L2, L3, L4 | live | `send_message()` for redflag alerts (L0) + L1 recap + L2 abort/recap + L3 event-driven (BUY-NOW / thesis-break / notch) + L4 plan event per finalized ticker |
| `think.py` |   | live |   |
| `tick_walls.py` |   | live |   |
| `tradeplan.py` |   | live |   |
| `universe_scan.py` |   | live |   |
| `vault_sync.py` |   | live |   |
| `vp_analyzer.py` | L2 | live | `classify(ticker, "1d")` — `vp_state` sets `vp_redflag` when weak_rally/distribution w/o spring |
| `watchlist_4group_scan.py` |   | live |   |
| `wyckoff.py` | L2 | live | `analyze_wyckoff(ticker)` — phase/structure/volume_pattern/confidence/signals for L2 dim-1 |
| `l2_healthcheck.py` | L2 | live | spec #4 — pre-run gate (empty universe / stale L1 / both caches missing) |
| `l2_dim_gather.py` | L2 | live | spec #4 — 4-dim gatherers (price/broker/book/narrative) for per-ticker judge prompt |
| `l2_synth.py` | L2 | live | spec #4 — pure helpers (promotion truth table, prompt builders, response parsers, telegram recap) |
| `bid_offer_patterns.py` | L3 | live | spec #5 — PRD port: `analyze_near_book` + `wall_withdrawn` pattern analysis |
| `l3_buy_now_ledger.py` | L3, L4 | live | spec #5 — daily idempotency ledger for `/trade:tradeplan` invocation; spec #6 L4 reads ledger to detect Mode B (L3 BUY-NOW recent) |
| `l3_dim_gather.py` | L3 | live | spec #5 — per-ticker tape + thick-wall + spring + orderbook + running-trade gather |
| `l3_healthcheck.py` | L3 | live | spec #5 — pre-run gate: market-hours / non-empty universe / orderbook_state dir |
| `l3_synth.py` | L3 | live | spec #5 — pure helpers: judge prompt/parse, buy_now_gate, merge_plan_update, telegram/daily-note, opus confirm |
| `l4_synth.py` | L4 | live | spec #6 — IDX tick math + size_plan + prompt builders (Mode A/B) + parser + struct builder + telegram/daily-note formatters |
| `l4_dim_gather.py` | L4 | live | spec #6 — structure + indicators (Mode A) + orderbook snapshot + last tape note (Mode B); graceful-degrade on gather failures |
| `l4_healthcheck.py` | L4 | live | spec #6 — pre-run gate: aggressiveness=off / BP / duplicate-guard / wait_bid_offer / ticker regex / empty queue |
| `l5_synth.py` | L5 | live | spec #7 — validators, payload builders, circuit-breaker, reconcile decision tree (classify_order_state/is_order_stale/append_fill), telegram/daily-note formatters |
| `l5_dim_gather.py` | L5 | live | spec #7 — cash, open orders, position detail from Carina; graceful-degrade |
| `l5_healthcheck.py` | L5 | live | spec #7 — pre-run gate: aggressiveness=off / Carina token age / WIB window (pre_open 08:00–08:45, reconcile 09:00–15:15) / intraday ticker+plan+stale-plan guard |
| `l5_executor.py` | L5 | live | spec #7 — place/cancel/stop/TP wrappers with exponential-backoff retry (3 attempts) + idempotency key `(ticker, leg, plan_updated_at)` |
| `l5_run.py` | L5 | live | spec #7 — CLI entrypoint for intraday fire: `python -m tools.trader.l5_run --ticker T` |

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

## External services (used-by-layer)

| Service | Used-by-layer | Notes |
|---------|---------------|-------|
| `services/telegram-scraper/` (L1-A) | L1 | systemd user unit; posts to `:8787/feed/telegram/insight`; L1 gates on `MAX(occurred_at)` via `/api/v1/insights/last` |
| fund-manager Go backend `:8787` | L0, L1 | SQLite-backed insight store + watchlist merge; new spec #3 endpoint `/api/v1/insights/last` |

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
| #1 | Core + Archive/Scaffold | complete |
| #2 | L0 Portfolio | complete (dry-run passed 2026-04-20) |
| #3 | L1 + L1-A + L1-B | complete (dry-run passed 2026-04-21) |
| #4 | L2 Screening | in progress (plan-complete, pre-dry-run) |
| #5 | L3 Monitoring | in progress (plan-complete, pre-dry-run) |
| #6 | L4 Trade Plan | in progress (plan-complete, pre-dry-run) |
| #7 | L5 Execute | in progress (plan-complete, pre-dry-run) |
| #8 | Orchestration / CRON | not started |
