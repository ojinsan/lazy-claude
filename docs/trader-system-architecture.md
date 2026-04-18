# Trader System Architecture

Audience: new developer onboarding into trader stack.

Scope:
1. High-level system overview
2. Backend functions in main flow
3. L0–L5 layers, data flow, 3-layer architecture, triggers
4. Backend API reference

Verified against code on 2026-04-18.
Where docs and runtime differ, this document follows runtime code.

---

## 1. High level — how system works

At highest level, system is a scheduled trading assistant stack for IDX/Indonesia market.

Core rule from playbook:
- **Code collects and compresses data**
- **Claude reads outputs, reasons, and decides**
- **No script should make final market judgment or ranking**

Source: `playbooks/trader/CLAUDE.md:8`, `playbooks/trader/archive/trigger-map.md:9`

### Main building blocks

#### A. Trader runtimes and tools
Python scripts under `tools/trader/` do data collection, compression, local analysis, and broker execution plumbing.

Examples:
- `tools/trader/portfolio_health.py` — portfolio health snapshot
- `tools/trader/runtime_layer1_context.py` — pre-market context fetch
- `tools/trader/runtime_layer2_screening.py` — candidate generation + scoring
- `tools/trader/runtime_monitoring.py` — intraday orderbook/tape review
- `tools/trader/runtime_summary_30m.py` — compress monitoring into heartbeat summary
- `tools/trader/tradeplan.py` — generate trade plan block
- `tools/trader/api.py` — shared market/broker/Carina API layer

#### B. Claude command/playbook layer
Slash-command files under `.claude/commands/trade/` define autonomous jobs.
Each command points Claude at a layer playbook.

Examples:
- `.claude/commands/trade/portfolio.md` → L0
- `.claude/commands/trade/screening.md` → L1 + L2
- `.claude/commands/trade/monitoring.md` → L3 (+ conditional L4)
- `.claude/commands/trade/tradeplan.md` → L4
- `.claude/commands/trade/execute.md` → L5

#### C. Fund-manager backend
Go service in `code/fund-manager/backend/` provides:
- persistent storage in SQLite
- fast shared state/cache in Redis
- watchlist merge with Lark
- internal API for portfolio, watchlist, thesis, tradeplans, signals, learning, charts, strategy, and telegram insight ingestion

Entry: `code/fund-manager/backend/cmd/server/main.go:19`
Mount: `code/fund-manager/backend/internal/api/api.go:15`

#### D. Storage
System uses multiple storage layers:
- **SQLite** — canonical app database for backend entities
- **Redis** — SSE queue, kill switch, intraday regime, cache
- **vault/data/** — local JSON/JSONL working state
- **runtime/** — generated daily artifacts/logs for Claude review

#### E. External services
System integrates with:
- Stockbit / Carina APIs for market, broker, portfolio, and order execution
- Telegram scraper feed for insights ingestion
- Lark sheet for watchlist source
- Threads scraper for narrative context

---

## 2. High level runtime flow

Daily system loop:

1. **03:00** overnight macro prefetched
2. **04:00** universe + catalyst data prefetched
3. **04:30** L0 portfolio health updates local state and backend
4. **05:00 / 05:30** L1+L2 build market context and shortlist
5. **06:00** L4 builds trade plans
6. **08:30** L5 checks portfolio + places orders if needed
7. **09:00–15:00 every 30m** L3 monitors live names; may promote back to L4/L5
8. **15:20** EOD publish tries to push summary
9. **Sunday 20:00 / month-end 20:00** weekly/monthly review jobs

Verified runtime schedule: `tools/trader/cron-dispatcher.sh:42`

---

## 3. Main backend role in this system

Backend is not market-intelligence engine. Backend is **shared state and workflow memory** for trader stack.

It stores and serves:
- portfolio snapshots and holdings
- transactions
- watchlist
- thesis and reviews
- themes
- trade plans
- signals and layer outputs
- daily note
- lessons/calibration/performance/evaluations
- charts
- tape state / confluence / auto-trigger log / konglo groups
- telegram insights and positive-candidate extraction

Backend server startup:
- loads env: `code/fund-manager/backend/cmd/server/main.go:20`
- opens SQLite: `code/fund-manager/backend/cmd/server/main.go:27`
- opens Redis: `code/fund-manager/backend/cmd/server/main.go:35`
- configures optional Lark client: `code/fund-manager/backend/cmd/server/main.go:41`
- mounts routes: `code/fund-manager/backend/cmd/server/main.go:58`

---

## 4. Backend functions in main flow

This section follows actual trader flow end-to-end.

### 4.1 L0 Portfolio → backend writes portfolio state

Main script: `tools/trader/portfolio_health.py`

Important functions:

#### `compute_portfolio_state()`
Source: `tools/trader/portfolio_health.py:230`

What it does:
- pulls live portfolio from Carina via `api.get_portfolio()`
- pulls cash via `api.get_cash_info()`
- computes equity, deployed capital, utilization, MTD return, drawdown, max DD, high-water mark
- computes exposure and flags
- updates local history in `vault/data/portfolio-state.json`

Sub-functions:
- `compute_exposure_breakdown()` — `tools/trader/portfolio_health.py:165`
- `compute_concentration_flags()` — `tools/trader/portfolio_health.py:209`
- `compute_drawdown()` — `tools/trader/portfolio_health.py:116`

#### `save_state(state)`
Source: `tools/trader/portfolio_health.py:54`

What it does:
- writes local JSON state file
- dual-writes portfolio snapshot to backend via `fund_api.post_portfolio_snapshot()`
- dual-writes holdings batch via `fund_api.post_holdings()`

Backend endpoints hit:
- `POST /api/v1/portfolio/snapshot`
- `POST /api/v1/portfolio/holdings`

### 4.2 L1 Global Context → backend stores layer outputs and narrative signals

Main script: `tools/trader/runtime_layer1_context.py`

Important functions:

#### `get_market_snapshot()`
Source: `tools/trader/runtime_layer1_context.py:144`

Fetches:
- IHSG and key proxy tickers from Stockbit direct
- uses `api.get_stockbit_index()`, `api.get_stockbit_orderbook()`, `api.get_stockbit_chart()`

#### `get_rag_items()`
Source: `tools/trader/runtime_layer1_context.py:199`

Fetches recent insight context via `api.rag_search()`.
Important note: Python wrapper expects richer `/rag/search` behavior than current Go handler exposes. Current Go backend only supports simple `{query, limit}` FTS search over insight table.

#### `run_threads()`
Source: `tools/trader/runtime_layer1_context.py:110`

Runs Threads scraper subprocesses in parallel to capture current narrative chatter.

#### `synthesize()`
Source: `tools/trader/runtime_layer1_context.py:216`

Combines market snapshot, RAG hits, Threads chatter into one L1 summary payload.

#### `publish_airtable(payload)``
Source: `tools/trader/runtime_layer1_context.py:301`

Despite name, current implementation writes to backend via `tools.fund_api`:
- posts one L1 layer output row
- posts a few narrative-capture signals

Backend endpoints hit:
- `POST /api/v1/layer-outputs`
- `POST /api/v1/signals`

### 4.3 L2 Screening → backend stores shortlist signals + watchlist state

Main script: `tools/trader/runtime_layer2_screening.py`

Important functions:

#### `candidate_universe()`
Source: `tools/trader/runtime_layer2_screening.py:190`

Builds candidate list from five sources in priority order:
1. current holdings
2. L1 outputs
3. telegram positive candidates from backend
4. Threads tracked accounts
5. merged watchlist from backend/Lark

Backend calls inside:
- `fund_manager_client.get_positive_candidates()` → `GET /api/v1/insights/positive-candidates`
- `fund_manager_client.get_watchlist()` → `GET /api/v1/watchlist`
- `fund_api.get_holdings()` → `GET /api/v1/portfolio/holdings`

#### `score_ticker(code)`
Source: `tools/trader/runtime_layer2_screening.py:238`

Scores each ticker using:
- price change
- liquidity / value
- running-trade buy/sell ratio
- absorption behavior

Uses market APIs only, not backend.

#### `score_holdings_vs_candidates()`
Source: `tools/trader/runtime_layer2_screening.py:275`

Compares existing holds vs new candidates and flags rotation opportunities.

#### `main()`
Source: `tools/trader/runtime_layer2_screening.py:307`

Writes local JSONL and posts backend records:
- one L2 layer output summary
- rotation signals
- top candidate screening signals
- watchlist entries for top non-held names

Backend endpoints hit:
- `POST /api/v1/layer-outputs`
- `POST /api/v1/signals`
- `POST /api/v1/watchlist`

### 4.4 L3 Monitoring → backend stores monitoring signals; may auto-trigger Claude

Main script: `tools/trader/runtime_monitoring.py`

Important functions:

#### `load_hold_tickers()`
Source: `tools/trader/runtime_monitoring.py:17`

Reads holdings from backend via `fund_api.get_holdings()`.

#### `load_watchlist_tickers()`
Source: `tools/trader/runtime_monitoring.py:31`

Reads watchlist from local file first, then backend `/watchlist` fallback.

#### `summarize_ticker()`
Source: `tools/trader/runtime_monitoring.py:67`

This is core intraday microstructure summary function.
It calls:
- `api.get_orderbook_delta()`
- `api.get_stockbit_running_trade()`

It then derives:
- pressure side
- dominance tier
- whale tick detection
- manipulation pattern (`accumulation_setup`, `distribution_setup`)
- shakeout / wick behavior
- strengthening vs weakening stance

#### `main()`
Source: `tools/trader/runtime_monitoring.py:192`

What it does:
- builds ticker set from holds + watchlist
- summarizes each ticker
- appends local monitoring note JSONL
- checks auto-trigger per ticker via tape snapshot + confluence gates

Auto-trigger path:
- `tools.trader.tape_runner.snapshot()`
- `tools.trader.auto_trigger.should_trigger()`
- `tools.trader.auto_trigger.trigger()`

Auto-trigger gates live in `tools/trader/auto_trigger.py:62`

### 4.5 L3 compression / EOD publish

#### `runtime_summary_30m.py`
Source: `tools/trader/runtime_summary_30m.py:30`

Function `summarize(rows)`:
- groups intraday records by ticker
- marks repeated strengthening / weakening / fresh changes
- writes compact heartbeat summary

#### `runtime_eod_publish.py`
Source: `tools/trader/runtime_eod_publish.py:29`

Function `publish(items)`:
- converts summary items into L3 `eod_heartbeat` signals
- posts one final L3 layer output summary

Backend endpoints hit:
- `POST /api/v1/signals`
- `POST /api/v1/layer-outputs`

Important note:
- `runtime_summary_30m.py` writes `heartbeat-YYYY-MM-DD.jsonl`
- `runtime_eod_publish.py` reads `summary-30m-YYYY-MM-DD.jsonl`
- current filenames do not match, so EOD publish path likely stale/broken unless another writer exists.

### 4.6 L4 Trade plan generation → backend stores plan records

Main script: `tools/trader/tradeplan.py`

Important function:

#### `generate_plan()`
Source: `tools/trader/tradeplan.py:40`

What it does:
- analyzes players, psychology, Wyckoff, narrative
- computes support/resistance, volume ratio
- derives entry, stop, target, R:R, size, conviction cap
- prints plan and checklist
- updates local watchlist state

Important helper:
- `_update_watchlist()` — `tools/trader/tradeplan.py:187`

What `_update_watchlist()` tries to do:
- update local watchlist JSON
- dual-write trade plan into backend via `fund_api.post_tradeplan()`

Backend endpoint hit:
- `POST /api/v1/tradeplans`

### 4.7 L5 Execution → backend records resulting state, not order execution itself

Actual order execution goes through Carina broker endpoints inside `tools/trader/api.py`, not through fund-manager backend.

Broker execution functions:
- `place_buy_order()` — `tools/trader/api.py:995`
- `place_sell_order()` — `tools/trader/api.py:1041`
- `cancel_order()` — `tools/trader/api.py:1087`
- `amend_orders()` — `tools/trader/api.py:1107`
- `get_orders()` — `tools/trader/api.py:966`
- `get_position_detail()` — `tools/trader/api.py:951`

Backend role in L5:
- store transactions
- store updated holdings/snapshots later
- store layer outputs / daily notes / lessons
- expose kill switch and regime state to gate execution

### 4.8 Telegram insight ingestion → backend turns chat feed into searchable signal memory

Root feed endpoint:
- `POST /feed/telegram/insight`
- mounted outside `/api/v1`
- source: `code/fund-manager/backend/internal/api/handlers/insights.go:15`

Store logic:
- `IngestInsights()` — `code/fund-manager/backend/internal/store/insights.go:45`
- `PositiveCandidates()` — `code/fund-manager/backend/internal/store/insights.go:72`
- `RAGSearch()` — `code/fund-manager/backend/internal/store/insights.go:106`

This turns raw telegram messages into:
- searchable insight store
- positive ticker candidate extraction for L2
- lightweight RAG/FTS for L1/L2 context

---

## 5. L0 until L5 — purpose and connection

Source overview: `playbooks/trader/CLAUDE.md:12`

## L0 — Portfolio

Time:
- scheduled 04:30 WIB

Purpose:
- hedge-fund style portfolio review before looking for new trades
- check DD, utilization, concentration, thesis drift, stale thesis, kill switch

Main output:
- `vault/data/portfolio-state.json`
- portfolio health card
- thesis actions for current holds

Downstream consumers:
- L1 uses hold tickers for dynamic context queries
- L2 uses thesis actions and portfolio risk state
- L4 uses equity, DD, posture, sector caps for sizing
- L5 uses hold state and invalidation context

## L1 — Global context

Time:
- scheduled 05:00 and 05:30 window via screening command

Purpose:
- define market regime, themes, sector leadership, aggression posture

Main output:
- local `runtime/notes/layer_1_global_context/YYYY-MM-DD.jsonl`
- backend `layer_outputs` + `signals`

Downstream consumers:
- L2 narrative-fit criterion
- L4 context and posture
- auto-trigger prompt re-checks L1 state before action

## L2 — Stock screening

Time:
- after L1 in same pre-market screening run

Purpose:
- turn broad universe into shortlist
- compare new candidates vs current holds
- reject names with poor fit or thesis-action conflicts

Main output:
- local screening JSONL
- shortlist / rotation signals / watchlist updates in backend

Downstream consumers:
- L4 full trade plans
- L3 watch/monitor names

## L3 — Monitoring

Time:
- 09:00–15:00 every 30 minutes
- extra emphasis at 11:30 and 14:00 for posture re-check

Purpose:
- monitor held and watched names intraday
- read whale intent, fake walls, shakeouts, tape state
- decide whether setup is now actionable

Main output:
- local 10m/30m monitoring notes
- optional signals and promotions
- optional auto-trigger into Claude

Downstream consumers:
- L4 sizing-only or refreshed plan
- L5 immediate execution when confidence gate met

## L4 — Trade plan

Time:
- 06:00 scheduled pre-market
- on-demand from L3 when setup matures

Purpose:
- turn L0+L1+L2+L3 evidence into precise plan

Two modes:
- **Mode A Full Plan** — from L2 shortlist path
- **Mode B Sizing-only** — from L3 “BUY NOW” path

Main output:
- trade plan blocks
- backend tradeplan rows
- priority ranking

Downstream consumers:
- L5 execution

## L5 — Execution

Time:
- 08:30 scheduled pre-open
- on-demand from L3/L4

Purpose:
- check current holdings and open orders
- execute exits/entries through Carina
- log order results

Main output:
- real broker orders
- order JSONL log
- transaction / state sync follow-ons

---

## 6. 3a — data flow between L0–L5

### End-to-end data flow

```text
Stockbit / Carina / Threads / Telegram / Lark
        ↓
tools/trader/*.py runtimes and shared api.py
        ↓
Local working state
- vault/data/*.json
- runtime/**/*.jsonl|md
        ↓
Claude command/playbook layer
- .claude/commands/trade/*.md
- playbooks/trader/*.md
        ↓
Decisions / summaries / plans
        ↓
fund-manager backend (SQLite + Redis)
        ↓
frontend / API clients / later runs / SSE / watchlist merge
```

### Practical layer-to-layer flow

#### L0 → L1
- L0 writes `portfolio-state.json`
- L1 reads hold tickers from that state for dynamic market queries
- source: `tools/trader/runtime_layer1_context.py:29`, `tools/trader/runtime_layer1_context.py:36`

#### L1 → L2
- L1 writes context JSONL
- L2 reads latest L1 payload and extracts candidate tickers/themes
- source: `tools/trader/runtime_layer2_screening.py:33`, `tools/trader/runtime_layer2_screening.py:52`

#### L2 → L4
- L2 shortlist defines which names deserve full plans
- command file `tradeplan.md` explicitly depends on screening output
- source: `.claude/commands/trade/tradeplan.md:9`

#### L2 → L3
- shortlisted/watchlist names become names monitored intraday
- backend watchlist and local watchlist feed L3 input set

#### L3 → L4
- if monitoring detects promotion or structure shift, command runs L4 for affected names
- source: `.claude/commands/trade/monitoring.md:10`

#### L3/L4 → L5
- if confidence gate met, execution runs inline
- otherwise L5 executes at 08:30 schedule

#### Runtime tools → backend
- runtimes post snapshots, holdings, signals, layer outputs, watchlist, tradeplans
- backend becomes shared memory across frontend + later jobs

---

## 7. 3b — detail of 3-layer architecture

Project root defines 3-layer architecture:

```text
tools/       → service connectors + business logic scripts
skills/      → role playbooks and reasoning rules
playbooks/   → workflow guides for active tasks
```

Source: `CLAUDE.md:17`

### Layer A — `tools/`

Purpose:
- executable code
- connectors to services
- local data transforms
- runtime scripts used by cron and commands

Examples:
- `tools/trader/api.py` — shared market + broker + Carina API layer
- `tools/trader/portfolio_health.py` — L0 metrics
- `tools/trader/runtime_layer1_context.py` — L1 ingestion/synthesis prep
- `tools/trader/runtime_layer2_screening.py` — L2 candidate build
- `tools/trader/runtime_monitoring.py` — L3 live monitoring prep
- `tools/fund_api.py` — HTTP client to Go backend

Rule:
- tools should gather, normalize, store, or execute; not make final discretionary trade judgment.

### Layer B — `skills/`

Purpose:
- domain reasoning manuals
- pattern interpretation rules
- what Claude should care about when evaluating data

Examples:
- `skills/trader/CLAUDE.md` — trader philosophy and skill index
- `skills/trader/bid-offer-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/execution.md`
- `skills/trader/auto-trigger.md`

Rule:
- skills tell Claude **how to think** about signals.

### Layer C — `playbooks/`

Purpose:
- operational workflows per layer
- exact sequence, inputs, outputs, and escalation rules

Examples:
- `playbooks/trader/layer-0-portfolio.md`
- `playbooks/trader/layer-1-global-context.md`
- `playbooks/trader/layer-2-stock-screening.md`
- `playbooks/trader/layer-3-stock-monitoring.md`
- `playbooks/trader/layer-4-trade-plan.md`
- `playbooks/trader/layer-5-execution.md`

Rule:
- playbooks tell Claude **when and in what order** to apply skills and tools.

### Why this split matters

- `tools/` = capability
- `skills/` = judgment rules
- `playbooks/` = orchestration

That split is why cron can run same command every day, while reasoning remains layer-specific.

---

## 8. 3c — triggers: cron, slash commands, auto-trigger, feed triggers

## A. Cron dispatcher

Actual runtime dispatcher: `tools/trader/cron-dispatcher.sh:1`

### Verified schedule

| WIB time | Trigger | Action |
|---|---|---|
| 03:00 | cron | `overnight_macro.py` |
| 04:00 | cron | `universe_scan.py` + `catalyst_calendar.py` |
| 04:30 | cron | Claude `trade:portfolio` |
| 05:00 | cron | Claude `trade:screening` |
| 05:30 | cron | Claude `trade:screening` again |
| 06:00 | cron | Claude `trade:tradeplan` |
| 08:30 | cron | Claude `trade:execute` |
| 09:00–15:00 every 30m | cron | Claude `trade:monitoring`, then `trade:execute` |
| 11:30 | cron branch | monitoring run flagged as mid-day regime check |
| 14:00 | cron branch | monitoring run flagged as mid-day regime check |
| 15:20 | cron | tries `trade/eod.md` |
| Sunday 20:00 | cron | `journal.py weekly` |
| Last day month 20:00 | cron | `journal.py monthly` |

### Important trigger notes

1. Main system cron entry documented as every 30 minutes:
   - `tools/manual/cron-dispatcher.md:28`
2. Dispatcher itself contains minute-specific branches like 04:30, 08:30, 15:20, 03:00.
3. Dispatcher references `.claude/commands/trade/eod.md`, but file does not currently exist.
4. `tools/manual/cron-dispatcher.md` is stale: it omits 03:00, 04:00, 04:30, weekly/monthly, and 15:20 paths.

## B. Slash command triggers

Main trading entrypoint:
- `/trade` → `.claude/commands/trade.md:1`
- loads trader playbook + skill index first

Trader subcommands:
- `/trade:portfolio` → L0
- `/trade:screening` → L1 + L2
- `/trade:monitoring` → L3 (+ conditional L4)
- `/trade:tradeplan` → L4
- `/trade:execute` → L5

Files:
- `.claude/commands/trade/portfolio.md:1`
- `.claude/commands/trade/screening.md:1`
- `.claude/commands/trade/monitoring.md:1`
- `.claude/commands/trade/tradeplan.md:1`
- `.claude/commands/trade/execute.md:1`

## C. Auto-trigger from monitoring runtime

Source:
- `tools/trader/runtime_monitoring.py:214`
- `tools/trader/auto_trigger.py:62`
- `skills/trader/auto-trigger.md:5`

Trigger conditions:
- confluence score >= 80 (`execute` bucket)
- tape composite in `{ideal_markup, spring_ready, healthy_markup}`
- tape confidence == `high`
- kill switch inactive
- posture >= 2
- DD <= 5%
- no dedup hit in last 60 minutes
- daily budget < 5

Action sequence on pass:
1. telegram first
2. set dedup + budget markers in Redis
3. invoke Claude with re-check prompt
4. log to `vault/data/auto_trigger_log.jsonl`

## D. Feed trigger from telegram scraper

Root endpoint:
- `POST /feed/telegram/insight`

This is not cron-driven. It is push ingestion from telegram scraper service into backend.

Effect:
- insight rows stored
- later L1/L2 can query positive candidates and FTS/RAG results

## E. Inline execution gates inside layer playbooks

Not OS-level triggers, but workflow triggers:
- L2 inline gate → execute if 5/5 criteria + price in entry window + DD < 5% (`playbooks/trader/layer-2-stock-screening.md:104`)
- L3 inline gate → execute if accumulation setup + price in zone + thesis intact + DD < 5% (`playbooks/trader/layer-3-stock-monitoring.md:76`)
- L4 inline gate → execute if urgent + price in zone + DD < 5% (`playbooks/trader/layer-4-trade-plan.md:75`)

---

## 9. Backend API docs

Base URL from Python client:
- `http://127.0.0.1:8787/api/v1`
- source: `tools/fund_api.py:18`

Health endpoint sits at root, not under `/api/v1`.

Response helpers:
- most list endpoints return `{ "items": [...], "count": N }`
- most create endpoints return created object directly
- errors return `{ "error": "..." }`
- source: `code/fund-manager/backend/internal/api/handlers/helpers.go:9`

## 9.1 Health and feed

### `GET /healthz`
Status check.

Response:
```json
{"status":"ok"}
```

Source: `code/fund-manager/backend/internal/api/api.go:16`

### `POST /feed/telegram/insight`
Ingest telegram insight batch.

Request body:
```json
{
  "insights": [
    {
      "time": "2026-04-18T09:10:00+07:00",
      "content": "BBCA ada akumulasi ...",
      "participant_type": "foreign",
      "address_text": "BBCA from channel X",
      "source": "telegram",
      "topic": "banking",
      "confidence": 80
    }
  ]
}
```

Response:
```json
{"stored": 3}
```

Source: `code/fund-manager/backend/internal/api/handlers/insights.go:25`

---

## 9.2 Portfolio API

Routes source: `code/fund-manager/backend/internal/api/handlers/portfolio.go:14`

### `GET /api/v1/portfolio/snapshot`
Query params:
- `from`
- `to`
- `limit` default 60

Returns list of `PortfolioSnapshot`.

Fields:
- `date`, `equity`, `cash`, `deployed`, `utilization`, `drawdown`, `hwm`, `posture`, `top_exposure`, `raw_json`

### `POST /api/v1/portfolio/snapshot`
Upsert one portfolio snapshot by date.

Minimal body:
```json
{
  "date": "2026-04-18",
  "equity": 100000000,
  "cash": 25000000,
  "deployed": 75000000,
  "utilization": 75,
  "drawdown": 2.1,
  "hwm": 102000000,
  "posture": "balanced"
}
```

### `GET /api/v1/portfolio/holdings`
Query params:
- `date`
- `ticker`

Returns list of `Holding`.

Fields:
- `date`, `ticker`, `shares`, `avg_cost`, `last_price`, `market_value`, `unrealized_pnl`, `unrealized_pct`, `sector`, `action`, `thesis_status`

### `POST /api/v1/portfolio/holdings`
Batch upsert holdings.

Body:
```json
[
  {
    "date": "2026-04-18",
    "ticker": "BBCA",
    "shares": 1000,
    "avg_cost": 9100,
    "last_price": 9250
  }
]
```

### `GET /api/v1/portfolio/current`
Returns latest snapshot + holdings for that snapshot date.

Response shape:
```json
{
  "snapshot": { ... },
  "holdings": [ ... ]
}
```

### `GET /api/v1/transactions`
Query params:
- `ticker`
- `days`
- `side`
- `limit` default 100

Returns list of `Transaction`.

### `POST /api/v1/transactions`
Create transaction row.

Fields:
- `ts`, `ticker`, `side`, `shares`, `price`, `value`, `order_id`, `thesis`, `conviction`, `layer_origin`, `notes`

### `PUT /api/v1/transactions/{id}`
Update realized PnL fields.

Body:
```json
{"pnl": 2500000, "pnl_pct": 8.5}
```

### `GET /api/v1/cache/price/{ticker}`
Returns cached price object from Redis.

### `POST /api/v1/cache/price/{ticker}`
Stores cached price object in Redis with 60-second TTL.

Body:
```json
{"price": 9250, "bid": 9240, "ask": 9250, "ts": "2026-04-18T09:31:00+07:00"}
```

---

## 9.3 Planning API

Routes source: `code/fund-manager/backend/internal/api/handlers/planning.go:23`

### `GET /api/v1/watchlist`
Merged watchlist from:
1. Lark sheet if configured
2. local SQLite watchlist

Query params:
- `status` currently accepted by client; handler returns merged set without explicit status filtering logic

Response item shape:
```json
{"ticker":"BBCA","status":"active","source":"lark|local"}
```

### `POST /api/v1/watchlist`
Upsert local watchlist row.

Fields:
- `ticker`, `first_added`, `status`, `conviction`, `themes`, `notes`, `updated_at`

### `DELETE /api/v1/watchlist/{ticker}`
Archive/delete watchlist row.

### `GET /api/v1/thesis`
Query params:
- `status`

Returns list of `Thesis`.

Fields:
- `ticker`, `created`, `layer_origin`, `status`, `setup`, `related_themes`, `body_md`, `last_review`, `updated_at`

### `GET /api/v1/thesis/{ticker}`
Returns one thesis row.

### `POST /api/v1/thesis`
Upsert thesis from body ticker.

### `PUT /api/v1/thesis/{ticker}`
Upsert thesis and force ticker from path.

### `GET /api/v1/thesis/{ticker}/review`
Returns list of thesis review rows.

Fields:
- `id`, `ticker`, `review_date`, `layer`, `note`

### `POST /api/v1/thesis/{ticker}/review`
Append thesis review.

Body:
```json
{"review_date":"2026-04-18","layer":"L0","note":"thesis still intact"}
```

### `GET /api/v1/themes`
Query params:
- `status`

### `POST /api/v1/themes`
Upsert theme row.

Fields:
- `slug`, `name`, `created`, `status`, `sector`, `related_tickers`, `body_md`, `updated_at`

### `GET /api/v1/tradeplans`
Query params:
- `plan_date`
- `ticker`
- `status`
- `level`
- `limit` default 50

Returns list of `TradePlan`.

### `POST /api/v1/tradeplans`
Create trade plan.

Fields:
- `plan_date`, `ticker`, `mode`, `setup_type`, `thesis`, `entry_low`, `entry_high`, `stop`, `target_1`, `target_2`, `size_shares`, `size_value`, `risk_pct`, `conviction`, `calibration_json`, `priority`, `level`, `status`, `raw_md`, `created_at`

### `PUT /api/v1/tradeplans/{id}`
Only updates status.

Body:
```json
{"status":"ready"}
```

---

## 9.4 Signals API

Routes source: `code/fund-manager/backend/internal/api/handlers/signals.go:15`

### `GET /api/v1/signals`
Query params:
- `ticker`
- `layer`
- `kind`
- `since`
- `limit` default 100

Returns list of `Signal`.

Fields:
- `id`, `ts`, `ticker`, `layer`, `kind`, `severity`, `price`, `payload_json`, `promoted_to`

### `POST /api/v1/signals`
Create signal and push same object into Redis `signal_queue` for SSE.

Body example:
```json
{
  "ts": "2026-04-18T10:00:00+07:00",
  "ticker": "BBCA",
  "layer": "L3",
  "kind": "screening_hit",
  "severity": "high",
  "price": 9250,
  "payload_json": "{\"score\":85}"
}
```

### `GET /api/v1/signals/recent`
Convenience endpoint for latest 100 signals.

### `GET /api/v1/signals/stream`
SSE endpoint backed by Redis `signal_queue`.

Event format:
```text
data: {json-signal}
```

### `GET /api/v1/kill-switch`
Returns cached kill switch state from Redis; default `{ "active": false }`.

### `PUT /api/v1/kill-switch`
Stores arbitrary JSON body under Redis key `kill_switch` with no TTL.

Example body:
```json
{"active": true, "reason": "daily DD exceeded threshold"}
```

### `GET /api/v1/regime/intraday`
Returns cached intraday regime JSON from Redis.

### `PUT /api/v1/regime/intraday`
Stores arbitrary JSON body under Redis key `regime:intraday` with no TTL.

Example body:
```json
{"posture": 2, "reason": "IHSG weakened and flow deteriorated"}
```

### `GET /api/v1/layer-outputs`
Query params:
- `run_date`
- `layer`
- `severity`
- `limit`

Returns list of `LayerOutput`.

Fields:
- `id`, `run_date`, `layer`, `ts`, `summary`, `body_md`, `severity`, `tickers`

### `POST /api/v1/layer-outputs`
Create layer output row.

### `GET /api/v1/daily-notes/{date}`
Returns one daily note.

### `PUT /api/v1/daily-notes/{date}`
Upsert daily note.

Body:
```json
{"body_md":"## L1\nRisk-off today ..."}
```

---

## 9.5 Learning API

Routes source: `code/fund-manager/backend/internal/api/handlers/learning.go:12`

### `GET /api/v1/lessons`
Query params:
- `category`
- `severity`
- `pattern_tag`
- `days`
- `limit`

Returns list of `Lesson`.

Fields:
- `id`, `date`, `category`, `severity`, `pattern_tag`, `tickers`, `related_thesis`, `lesson_text`, `source_trade_id`

### `POST /api/v1/lessons`
Create lesson row.

### `GET /api/v1/calibration`
Returns all calibration rows.

### `POST /api/v1/calibration`
Upsert calibration.

Fields:
- `run_date`, `bucket`, `declared_win_rate`, `actual_win_rate`, `drift`, `n_trades`, `window_days`

### `GET /api/v1/performance/daily`
Query params:
- `from`
- `to`

Returns list of `PerformanceDaily`.

### `POST /api/v1/performance/daily`
Upsert daily performance row.

Fields:
- `date`, `equity`, `ihsg_close`, `daily_return`, `ihsg_return`, `alpha`, `mtd_return`, `ytd_return`, `win_rate_90d`, `avg_r_90d`, `expectancy_90d`

### `GET /api/v1/performance/summary`
Returns summary derived from latest `PerformanceDaily` row:
- `mtd_return`
- `ytd_return`
- `alpha`
- `win_rate_90d`
- `expectancy_90d`

### `GET /api/v1/evaluations`
Query params:
- `period`
- `period_key`

Returns list of `Evaluation`.

### `POST /api/v1/evaluations`
Create evaluation row.

Fields:
- `period`, `period_key`, `generated_at`, `body_md`, `kpi_json`

---

## 9.6 Charts API

Routes source: `code/fund-manager/backend/internal/api/handlers/charts.go:12`

### `GET /api/v1/charts`
Query params:
- `ticker`
- `kind`
- `since`
- `limit`

Returns list of `ChartAsset`.

Fields:
- `id`, `ticker`, `as_of`, `kind`, `timeframe`, `payload_json`

### `POST /api/v1/charts`
Create chart asset row.

---

## 9.7 Strategy API

Routes source: `code/fund-manager/backend/internal/api/handlers/strategy.go:11`

### `GET /api/v1/tape-states`
Query params:
- `ticker`
- `composite`
- `since`
- `limit`

Returns list of `TapeState`.

Fields:
- `id`, `ts`, `ticker`, `composite`, `confidence`, `wall_fate`, `payload_json`

### `POST /api/v1/tape-states`
Create tape-state row.

### `GET /api/v1/confluence`
Query params:
- `ticker`
- `bucket`
- `since`
- `limit`

Returns list of `ConfluenceScore`.

Fields:
- `id`, `ts`, `ticker`, `score`, `bucket`, `components_json`

### `POST /api/v1/confluence`
Create confluence row.

### `GET /api/v1/confluence/latest`
Returns latest confluence row per ticker.

### `GET /api/v1/auto-triggers`
Query params:
- `date`
- `outcome`
- `limit`

Returns list of `AutoTriggerLog`.

Fields:
- `id`, `ts`, `ticker`, `kind`, `confluence`, `outcome`, `reason`

### `POST /api/v1/auto-triggers`
Create auto-trigger log row.

### `GET /api/v1/konglo/groups`
Returns konglo group rows.

Fields:
- `id`, `name`, `owner`, `market_power`, `sectors`

### `POST /api/v1/konglo/groups`
Upsert konglo group.

### `GET /api/v1/konglo/tickers/{ticker}`
Returns konglo group(s) matching ticker.

---

## 9.8 Insights API

Routes source: `code/fund-manager/backend/internal/api/handlers/insights.go:20`

### `GET /api/v1/insights/positive-candidates`
Query params:
- `min_confidence`
- `days`

Returns grouped positive ticker candidates from telegram insight store.

Response item fields:
- `ticker`, `max_confidence`, `count`, `latest_at`, `source`

### `POST /api/v1/rag/search`
Current Go handler contract:

Request body:
```json
{"query":"BBCA accumulation", "limit":20}
```

Response:
- raw list of `Insight` rows, not wrapped in `{items:...}`

Fields per item:
- `id`, `occurred_at`, `ticker`, `content`, `participant_type`, `ai_recap`, `confidence`, `address_text`, `source`, `topic`, `created_at`

Important compatibility note:
- `tools/trader/api.py:1840` expects richer filters/top_n/source semantics and fallback endpoints.
- current Go backend does **not** implement those richer semantics.
- if L1 RAG usage matters, this mismatch should be fixed first.

---

## 10. Known mismatches / stale docs worth knowing

For new developer, these are important:

1. `playbooks/trader/CLAUDE.md` says “No live WebSocket by default” and gives broad schedule. Good high-level summary, but real schedule is in `tools/trader/cron-dispatcher.sh`.
2. `tools/manual/cron-dispatcher.md` is stale versus real dispatcher.
3. `runtime_eod_publish.py` expects `summary-30m-*.jsonl`, but `runtime_summary_30m.py` writes `heartbeat-*.jsonl`.
4. Dispatcher calls `.claude/commands/trade/eod.md`, but that file does not exist now.
5. `tools/trader/api.py` RAG client expects a richer backend API than current Go `POST /api/v1/rag/search` implements.

---

## 11. New developer mental model

If you need one sentence per subsystem:

- **`tools/trader/api.py`** = market/broker execution plumbing
- **runtime scripts** = scheduled collectors/compressors
- **playbooks** = layer workflows
- **skills** = reasoning rules for Claude
- **fund-manager backend** = shared state + search + storage + SSE
- **frontend** = dashboard over backend state
- **cron dispatcher** = time-based orchestrator for whole stack

If you need one sentence for whole system:

**This is a cron-driven trading workflow where Python scripts gather market/portfolio evidence, Claude reasons across layered playbooks, Go backend stores shared state, and Carina executes real orders when gates pass.**
