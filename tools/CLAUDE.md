# tools/ — Index

Business logic scripts. Import from connectors/, called by playbooks/ or directly by the MCP server.

## Structure

| Dir / File               | Purpose                                                              |
|--------------------------|----------------------------------------------------------------------|
| `trader/`                | All trading logic — implementations live here                        |
| `trader/skills/`         | Shim package so `from skills.X import Y` resolves to `trader/X.py`  |
| `general/browser/`       | Python selenium/requests-based automation (Instagram, Shopee, etc.)  |
| `general/playwright/`    | Node.js Playwright scrapers with real Firefox sessions (Threads, FB) |
| `general/scripts/`       | One-off utility scripts (Google Sheets, Maps, car comparison)        |
| `general/references/`    | Reference docs for browser tooling decisions                         |
| `mcp-server/`            | Self-hosted SSE server exposing workspace tools to remote Claudes    |
| `data-persistence/`      | Static data files (stocklist.csv, etc.)                              |

## trader/ — File Index

| File                        | Purpose                                              |
|-----------------------------|------------------------------------------------------|
| `api.py`                    | Core API layer — Stockbit + backend, token, data     |
| `broker_profile.py`         | Broker flow analysis, smart/foreign/retail classify  |
| `wyckoff.py`                | Wyckoff phase detection                              |
| `market_structure.py`       | Support/resistance, trend, market structure          |
| `macro.py`                  | Macro context (index regime, sector rotation)        |
| `narrative.py`              | Narrative generation for trade context               |
| `psychology.py`             | Market psychology signals                            |
| `sid_tracker.py`            | SID (investor ID) trend tracking                     |
| `journal.py`                | Trade journal read/write and lesson search           |
| `screener.py`               | Full screener pipeline (calls all skill modules)     |
| `eval_pipeline.py`          | Evaluation pipeline for watchlist                    |
| `tradeplan.py`              | Trade plan generator                                 |
| `indicators.py`             | Technical indicators                                 |
| `tick_walls.py`             | Tick wall / orderbook depth analysis                 |
| `runtime_monitoring.py`     | Intraday monitoring runtime job                      |
| `config.py`                 | Config loader (env, paths, tokens)                   |
| `airtable_client.py`        | Airtable client for trader data                      |
| `stockbit_auth.py`          | Stockbit session auth                                |
| `stockbit_headers.py`       | Stockbit browser headers                             |
| `stockbit_screener.py`      | Stockbit-native screener                             |
| `runtime_*.py`              | Runtime jobs (EOD publish, layer1/2, monitoring, 30m)|
| `orderbook_*.py`            | Orderbook poller and WebSocket listener              |
| `realtime_listener.py`      | Realtime price/tick listener                         |
| `running_trade_poller.py`   | Active trade position poller                         |
| `watchlist_4group_scan.py`  | 4-group watchlist scanner                            |
| `think.py`                  | Reasoning/analysis helper                            |

## trader/skills/ — Shim Layer

Re-exports `trader/*.py` as `skills.*` so screener/tradeplan/eval can do:
```python
from skills.api import get_price
from skills.wyckoff import analyze_wyckoff
```
Do NOT add logic here — add it to the corresponding `trader/*.py` file.

## general/browser/ vs general/playwright/

- `browser/` — Python, uses selenium/requests + cookie-based sessions. For: Shopee, Tokopedia, Instagram.
- `playwright/` — Node.js, uses Playwright with a persistent Firefox profile. For: Threads, Facebook (login-walled, JS-heavy).

Use `playwright/` when the site requires JavaScript rendering or a logged-in Firefox session.
