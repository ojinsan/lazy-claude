# Tool ↔ Skill Coverage Matrix

Generated: 2026-04-16 (Phase 4 audit).

Counts of references per `tools/trader/*.py`. Numbers are file counts (not occurrence counts), produced by `grep -l` against `playbooks/trader/*.md`, `skills/trader/*.md`, and `tools/INDEX.md`.

## Business Logic

| Script | Playbook | Skill | Index | Status |
|--------|---------:|------:|------:|--------|
| `api.py` | 7 | 28 | 1 | ok |
| `airtable_client.py` | 1 | 7 | 1 | ok |
| `broker_profile.py` | 0 | 4 | 1 | ok — covered via `broker-flow.md`, `whale-retail-analysis.md`, `thesis-evaluation.md` |
| `indicators.py` | 0 | 6 | 1 | ok — covered via TA / Wyckoff skills |
| `journal.py` | 2 | 8 | 1 | ok |
| `macro.py` | 2 | 7 | 2 | ok |
| `market_structure.py` | 0 | 5 | 1 | ok — covered via `market-structure.md`, `technical-analysis.md` |
| `narrative.py` | 3 | 11 | 1 | ok |
| `portfolio_health.py` | 2 | 5 | 1 | ok (added Phase 1) |
| `psychology.py` | 2 | 1 | 1 | ok |
| `screener.py` | 2 | 2 | 2 | ok |
| `sid_tracker.py` | 0 | 3 | 1 | ok — covered via `sid-tracker.md`, `whale-retail-analysis.md` |
| `stockbit_screener.py` | 1 | 0 | 1 | ok — placeholder, API credentials pending (noted in L2 playbook) |
| `telegram_client.py` | 0 | 3 | 1 | ok — covered via `telegram-notify.md` (Phase 2.5) |
| `tradeplan.py` | 3 | 5 | 1 | ok |
| `watchlist_4group_scan.py` | 0 | 1 | 1 | ok — covered via `watchlist-4group.md` |
| `wyckoff.py` | 2 | 3 | 1 | ok |
| ~~`eval_pipeline.py`~~ | — | — | — | **archived** to `tools/trader/archive/eval_pipeline.py.v1` — superseded by `runtime_layer1_context.py` + `runtime_layer2_screening.py` split. |

## Live Data (on-demand)

| Script | Playbook | Skill | Index | Status |
|--------|---------:|------:|------:|--------|
| `orderbook_poller.py` | 1 | 4 | 1 | ok |
| `orderbook_ws.py` | 2 | 3 | 1 | ok |
| `realtime_listener.py` | 1 | 2 | 1 | ok |
| `running_trade_poller.py` | 1 | 5 | 1 | ok |
| `tick_walls.py` | 1 | 1 | 1 | ok |

## Runtime Jobs (cron-driven)

| Script | Playbook | Skill | Index | Status |
|--------|---------:|------:|------:|--------|
| `runtime_layer1_context.py` | 2 | 1 | 1 | ok |
| `runtime_layer2_screening.py` | 2 | 0 | 1 | ok — cron entry, not a skill target |
| `runtime_monitoring.py` | 2 | 1 | 1 | ok |
| `runtime_summary_30m.py` | 2 | 1 | 1 | ok |
| `runtime_eod_publish.py` | 1 | 0 | 1 | ok — cron entry |
| `cron-dispatcher.sh` | n/a | n/a | 1 | ok |

## Infra (no skill expected)

| Script | Status |
|--------|--------|
| `config.py` | infra — env / path / token loader |
| `stockbit_auth.py` | infra — token ensure + refresh |
| `stockbit_login.py` | infra — auto-login |
| `stockbit_headers.py` | infra — header constants |
| `__init__.py` | package marker |

## Legacy

| Script | Status |
|--------|--------|
| `think.py` | legacy — flagged in `tools/CLAUDE.md`, do not extend |

## Action Items

All coverage gaps resolved. `eval_pipeline.py` archived (Boss O decision 2026-04-16). Every remaining business logic / live data / runtime / infra script is referenced or correctly classified.

## Findings (out of Phase 4 scope, surfaced for follow-up)

- ~~**Import bug — `from . import api`.**~~ **Fixed in Phase 4.5.** Six files (`broker_profile.py`, `macro.py`, `market_structure.py`, `narrative.py`, `psychology.py`, `sid_tracker.py`) now use plain `import api` / `from broker_profile import …` etc. Both direct imports and `_lib/<name>.py` shim consumers verified working.
- **Stale path — `/home/lazywork/lazyboy/trade/data`.** `broker_profile.py:30` references the old data path. Phase 5 vault migration should sweep this kind of reference at the same time as `journal.py`.
