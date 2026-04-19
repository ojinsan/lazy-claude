# Trading Agents Revamp — Progress Tracker

Updated as each detail spec (L0–L5) consumes or improves tools.

Legend for `status`:
- `live` — used by new system, unchanged
- `improved` — used by new system, rewritten/extended
- `unused` — not referenced by new system, candidate for archive
- `deprecate-candidate` — scheduled for removal in future cleanup

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
| `journal.py` |   | live |   |
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
| `telegram_client.py` |   | live |   |
| `think.py` |   | live |   |
| `tick_walls.py` |   | live |   |
| `tradeplan.py` |   | live |   |
| `universe_scan.py` |   | live |   |
| `vault_sync.py` |   | live |   |
| `vp_analyzer.py` |   | live |   |
| `watchlist_4group_scan.py` |   | live |   |
| `wyckoff.py` |   | live |   |

## Archived references

To be populated in Task 13 — grep of archived skills/playbooks for `tools/trader/<X>` references.

## Spec status

| Spec | Scope | Status |
|------|-------|--------|
| #0 | Master | draft pushed |
| #1 | Core + Archive/Scaffold | in progress |
| #2 | L0 Portfolio | not started |
| #3 | L1 + L1-A + L1-B | not started |
| #4 | L2 Screening | not started |
| #5 | L3 Monitoring | not started |
| #6 | L4 Trade Plan | not started |
| #7 | L5 Execute | not started |
| #8 | Orchestration / CRON | not started |
