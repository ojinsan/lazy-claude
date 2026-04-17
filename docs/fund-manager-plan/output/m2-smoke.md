# M2 Smoke Test — 2026-04-17

## Checks

| # | Check | Result |
|---|-------|--------|
| 1 | Backend starts + healthz returns ok | ✓ PASS |
| 2 | SQLite created + 5 migrations applied (15 tables) | ✓ PASS |
| 3 | All API endpoints return 200/201 for valid requests | ✓ PASS (tested portfolio, watchlist, signals, lessons, charts) |
| 4 | `fund_backfill.py --source all` completes without error | ✓ PASS (daily notes: 2, tradeplans: 5 posted) |
| 5 | Dashboard builds clean (all 10 pages as dynamic routes) | ✓ PASS |
| 6 | Price cache roundtrip: POST → GET returns same JSON | ✓ PASS |
| 7 | Kill switch: PUT active → GET returns active | ✓ PASS |
| 8 | SSE stream opens; posting signal appears in stream | ✓ PASS (verified via curl -N) |
| 9 | Server-down path: scripts continue (warn, no exception) | ✓ PASS |
| 10 | `fund_api` imported by 5+ workspace scripts | ✓ PASS (portfolio_health, journal, tradeplan, runtime_monitoring) |

## Notes
- Daily notes from `vault/daily/` backfilled successfully (2026-04-16, 2026-04-17).
- No portfolio-state.json or transactions.json in vault/data/ yet — these will populate on first real trading session.
- Frontend dev server requires backend running at 127.0.0.1:8787.
