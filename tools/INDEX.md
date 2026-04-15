# tools/ — Script Index

## trader/ — Business Logic

| Script                    | Purpose                                                      | Layer |
|---------------------------|--------------------------------------------------------------|-------|
| `api.py`                  | Core Stockbit + backend API — price, orderbook, broker, SID  | All   |
| `config.py`               | Env/path/token loader                                        | All   |
| `broker_profile.py`       | Player intent: smart money vs retail, trap detection          | L2, L3 |
| `sid_tracker.py`          | SID accumulation/distribution signal                         | L2    |
| `market_structure.py`     | Support/resistance, trend, BOS/CHoCH                         | L2, L4 |
| `indicators.py`           | RSI, EMA, ATR, golden cross, cycle signal                    | L2, L4 |
| `wyckoff.py`              | Wyckoff phase detection                                      | L2    |
| `psychology.py`           | Behavior at key price levels — WHO is doing WHAT at S/R      | L2, L3 |
| `tick_walls.py`           | Orderbook wall analysis                                      | L3, L4 |
| `screener.py`             | Full screener pipeline (calls all analysis modules)          | L2    |
| `eval_pipeline.py`        | Full eval pipeline: L1→screen→health→shortlist→top picks     | L2    |
| `tradeplan.py`            | Trade plan generator                                         | L4    |
| `narrative.py`            | Narrative generation helper                                  | L1, L2 |
| `macro.py`                | Macro context — regime, sector rotation                      | L1    |
| `journal.py`              | Trade journal read/write and lesson search                   | L4    |
| `airtable_client.py`      | Airtable read/write for trader tables                        | Any   |
| `stockbit_screener.py`    | Stockbit native screener wrapper with pre-built filter sets  | L2    |
| `telegram_client.py`      | Telegram alert sender for L0–L4 + execution + intent events | Any   |
| `portfolio_health.py`     | L0 portfolio state: equity, MTD, drawdown, exposure, flags   | L0    |
| `watchlist_4group_scan.py`| 4-group universe scanner                                     | L2    |
| `stockbit_auth.py`        | Stockbit auth — token ensure + refresh                       | Infra |
| `stockbit_login.py`       | Auto-login to Stockbit mobile API, saves token               | Infra |
| `stockbit_headers.py`     | Stockbit browser header constants                            | Infra |

## trader/ — Runtime Jobs (cron-driven)

| Script                      | Job                                            |
|-----------------------------|------------------------------------------------|
| `runtime_layer1_context.py` | Automated L1 macro context collection          |
| `runtime_layer2_screening.py` | Automated L2 screening pipeline             |
| `runtime_monitoring.py`     | Periodic L3 monitoring loop                    |
| `runtime_summary_30m.py`    | 30-min market summary                          |
| `runtime_eod_publish.py`    | EOD Airtable publish                           |
| `cron-dispatcher.sh`        | WIB-schedule dispatcher → runs Claude commands |

## trader/ — Live Data (on-demand)

| Script                    | Purpose |
|---------------------------|---------|
| `orderbook_poller.py`     | Live orderbook polling loop |
| `orderbook_ws.py`         | WebSocket orderbook stream |
| `realtime_listener.py`    | Running trade patterns + orderbook deltas, writes to `runtime/monitoring/realtime/` |
| `running_trade_poller.py` | Live tape / running trades |

## trader/ — Import Shim

`trader/_lib/` — makes `trader/*.py` importable as `_lib.<module>` inside scripts that run from the `tools/trader/` working directory. Do NOT add logic here — add it to the corresponding `trader/*.py` file.

## trader/ — Legacy

`think.py` — older pipeline using `remoratrader` (external). Not in current cron. May be stale.

## general/ — Structure

| Dir                       | Purpose |
|---------------------------|---------|
| `general/browser/`        | Python Playwright-based automation (Instagram, Shopee, Tokopedia, Slack, web) |
| `general/playwright/`     | Node.js Playwright with persistent Firefox profile (Threads, FB, Instagram) |
| `general/scripts/`        | Utility scripts (Google Sheets, Maps) |
| `general/references/`     | Reference docs for browser tooling decisions |
| `mcp-server/`             | Self-hosted SSE server exposing workspace tools to remote Claudes |
| `data-persistence/`       | Static data files (stocklist.csv, etc.) |

### general/playwright/ — Key Scripts

| Script                    | Purpose |
|---------------------------|---------|
| `threads-scraper.js`      | Threads scraper — requires `.firefox-profile-threads/` |
| `facebook-scraper.js`     | Facebook scraper — requires `.firefox-profile-facebook/` |
| `instagram-scraper.js`    | Instagram scraper — requires `.firefox-profile-instagram/` |

Use `general/playwright/` when the site requires JS rendering or a logged-in Firefox session.
