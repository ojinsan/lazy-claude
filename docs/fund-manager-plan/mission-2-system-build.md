# Mission 2 — Fund Manager System Build

**Goal:** A local dashboard + API that stores every artifact the trader produces — signals, journals, theses, tradeplans, charts, watchlist, trade history, performance, evaluation — and lets the workspace scripts read/write via HTTP.

**Stack:** Go backend + SQLite + Redis + Next.js frontend. All local, no auth. Bind loopback only.

**Do not start Mission 2 until Mission 1 is complete and committed.** M1 closes the data-flow gaps; M2 productises them.

---

## Locations

```
/home/lazywork/workspace/code/fund-manager/
├── backend/
│   ├── cmd/server/main.go
│   ├── internal/
│   │   ├── api/          # chi routes + handlers
│   │   ├── store/        # SQLite repository
│   │   ├── cache/        # Redis client
│   │   ├── model/        # shared structs
│   │   └── config/       # env loader
│   ├── migrations/       # NNNN_name.sql
│   ├── go.mod
│   └── Makefile
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── components/
│   ├── lib/api.ts        # typed fetch wrapper
│   ├── package.json
│   └── tailwind.config.ts
├── data/
│   └── fund.db           # created at first boot
└── README.md
```

Python client goes into `/home/lazywork/workspace/tools/fund_api.py`.

---

## Phase M2.1 — Scaffold

### Goal
Empty-but-runnable backend on `:8787` and Next.js on `:3000`.

### Steps

1. Create directories:
   ```bash
   mkdir -p /home/lazywork/workspace/code/fund-manager/{backend/{cmd/server,internal/{api,store,cache,model,config},migrations},frontend,data}
   ```

2. **Backend scaffold** (`code/fund-manager/backend/`):
   - `go.mod`: module `fund-manager`, go 1.22.
   - Pull deps: `go get github.com/go-chi/chi/v5 modernc.org/sqlite github.com/redis/go-redis/v9 github.com/joho/godotenv`.
   - `cmd/server/main.go` — loads `.env.local` two dirs up, opens SQLite at `../data/fund.db`, connects Redis, mounts `/healthz` and `/api/v1/*`, listens on `127.0.0.1:8787`.
   - `internal/config/config.go` — `Load() (*Config, error)` with fields: `DBPath, RedisAddr, RedisDB, Port`.
   - `internal/store/store.go` — `New(dbPath string) (*Store, error)`; runs any `.sql` in `migrations/` in lexical order; stores `applied_migrations(name TEXT PRIMARY KEY, applied_at TIMESTAMP)`.
   - `internal/cache/cache.go` — thin wrapper: `Set(key, value, ttl)`, `Get(key)`, `Push(queue, value)`, `Pop(queue)`.
   - `internal/api/api.go` — `Mount(r chi.Router, s *store.Store, c *cache.Cache)` — only mounts `/healthz` returning `{"status":"ok"}`.
   - `Makefile`:
     ```makefile
     run: ; go run ./cmd/server
     build: ; go build -o ../data/fund-server ./cmd/server
     test: ; go test ./...
     ```

3. **Frontend scaffold** (`code/fund-manager/frontend/`):
   ```bash
   cd /home/lazywork/workspace/code/fund-manager/frontend
   npx create-next-app@latest . --ts --tailwind --app --no-eslint --no-src-dir --import-alias "@/*" --use-npm
   npx shadcn@latest init -d
   npx shadcn@latest add button card table tabs badge sheet dialog
   npm install recharts
   ```
   Edit `next.config.ts` — set `rewrites()` so `/api/*` proxies to `http://127.0.0.1:8787/api/*` during dev.

4. Create `code/fund-manager/README.md`:
   ```markdown
   # Fund Manager
   ## Dev
   - Backend: `cd backend && make run`
   - Frontend: `cd frontend && npm run dev`
   - Dashboard: http://127.0.0.1:3000
   ## Env
   Reads `/home/lazywork/workspace/.env.local`. Required: `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`.
   ## Data
   SQLite at `data/fund.db`. Migrations auto-apply on boot.
   ```

### Verify
- [ ] `cd backend && make run` starts and `curl 127.0.0.1:8787/healthz` returns `{"status":"ok"}`.
- [ ] `cd frontend && npm run dev` starts and http://127.0.0.1:3000 renders the default page.
- [ ] SQLite file `data/fund.db` is created on first boot.
- [ ] Redis ping succeeds (backend logs `redis: connected`).

### Commit
`[M2.1] Scaffold Go backend + Next.js frontend + SQLite/Redis plumbing`

---

## Phase M2.2 — SQLite Schema

### Goal
Every fund-manager entity has a table. Schemas match the JSON structures in `vault/data/` so the seed is trivial.

### Migrations

Create files in `backend/migrations/`. Order matters.

#### `0001_core.sql`

```sql
CREATE TABLE portfolio_snapshot (
  date          TEXT PRIMARY KEY,     -- YYYY-MM-DD
  equity        REAL NOT NULL,
  cash          REAL NOT NULL,
  deployed      REAL NOT NULL,
  utilization   REAL NOT NULL,        -- pct 0–100
  drawdown      REAL NOT NULL,        -- pct 0–100
  hwm           REAL NOT NULL,
  posture       TEXT NOT NULL,        -- press | balanced | defensive
  top_exposure  TEXT,
  raw_json      TEXT NOT NULL         -- full compute output
);

CREATE TABLE holding (
  date          TEXT NOT NULL,
  ticker        TEXT NOT NULL,
  shares        INTEGER NOT NULL,
  avg_cost      REAL NOT NULL,
  last_price    REAL,
  market_value  REAL,
  unrealized_pnl REAL,
  unrealized_pct REAL,
  sector        TEXT,
  action        TEXT,                  -- hold | add-to | reduce | exit-candidate
  thesis_status TEXT,                  -- intact | watch | stale
  PRIMARY KEY (date, ticker)
);

CREATE TABLE transaction_log (
  id            INTEGER PRIMARY KEY,
  ts            TEXT NOT NULL,         -- ISO8601
  ticker        TEXT NOT NULL,
  side          TEXT NOT NULL,         -- BUY | SELL | CUT
  shares        INTEGER NOT NULL,
  price         REAL NOT NULL,
  value         REAL NOT NULL,
  order_id      TEXT,
  thesis        TEXT,
  conviction    TEXT,
  pnl           REAL,                  -- null if open
  pnl_pct       REAL,
  layer_origin  TEXT,                  -- L2 | L3 | L4 | L5
  notes         TEXT
);
CREATE INDEX ix_tx_ticker_ts ON transaction_log(ticker, ts);
```

#### `0002_planning.sql`

```sql
CREATE TABLE watchlist (
  ticker         TEXT PRIMARY KEY,
  first_added    TEXT NOT NULL,
  status         TEXT NOT NULL,        -- active | hold | sold | archived
  conviction     TEXT,                 -- low | med | high
  themes         TEXT,                 -- comma-separated theme slugs
  notes          TEXT,
  updated_at     TEXT NOT NULL
);

CREATE TABLE thesis (
  ticker         TEXT PRIMARY KEY,
  created        TEXT NOT NULL,
  layer_origin   TEXT NOT NULL,
  status         TEXT NOT NULL,        -- active | closed | archived
  setup          TEXT,
  related_themes TEXT,
  body_md        TEXT NOT NULL,        -- full MD
  last_review    TEXT,
  updated_at     TEXT NOT NULL
);

CREATE TABLE thesis_review (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker         TEXT NOT NULL,
  review_date    TEXT NOT NULL,
  layer          TEXT NOT NULL,
  note           TEXT NOT NULL,
  FOREIGN KEY(ticker) REFERENCES thesis(ticker)
);
CREATE INDEX ix_review_ticker_date ON thesis_review(ticker, review_date);

CREATE TABLE theme (
  slug           TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  created        TEXT NOT NULL,
  status         TEXT NOT NULL,        -- active | retired
  sector         TEXT,
  related_tickers TEXT,                -- comma-separated
  body_md        TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);

CREATE TABLE tradeplan (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_date      TEXT NOT NULL,
  ticker         TEXT NOT NULL,
  mode           TEXT NOT NULL,        -- full | sizing_only
  setup_type     TEXT,
  thesis         TEXT,
  entry_low      REAL,
  entry_high     REAL,
  stop           REAL,
  target_1       REAL,
  target_2       REAL,
  size_shares    INTEGER,
  size_value     REAL,
  risk_pct       REAL,
  conviction     TEXT,
  calibration_json TEXT,                -- {"bucket":"high","drift":0.05,...}
  priority       INTEGER,
  level          TEXT NOT NULL,         -- local | superlist | alert
  status         TEXT NOT NULL,         -- draft | queued | executed | expired
  raw_md         TEXT NOT NULL,         -- full plan block as markdown
  created_at     TEXT NOT NULL
);
CREATE INDEX ix_plan_date_ticker ON tradeplan(plan_date, ticker);
```

#### `0003_signals.sql`

```sql
CREATE TABLE signal (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ts             TEXT NOT NULL,          -- ISO8601
  ticker         TEXT NOT NULL,
  layer          TEXT NOT NULL,          -- L2 | L3 | L4
  kind           TEXT NOT NULL,          -- accumulation_setup | distribution_setup | wick_shakeout | shakeout_trap | regime_flip | sector_rotation | catalyst
  severity       TEXT NOT NULL,          -- low | medium | high
  price          REAL,
  payload_json   TEXT NOT NULL,          -- raw detection context
  promoted_to    TEXT                    -- plan | alert | null
);
CREATE INDEX ix_signal_ticker_ts ON signal(ticker, ts);
CREATE INDEX ix_signal_kind_ts ON signal(kind, ts);

CREATE TABLE layer_output (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  run_date       TEXT NOT NULL,
  layer          TEXT NOT NULL,          -- L0..L5
  ts             TEXT NOT NULL,
  summary        TEXT NOT NULL,          -- the one-liner that lands in daily note
  body_md        TEXT,                   -- full output if saved
  severity       TEXT,                   -- info | medium | high
  tickers        TEXT                    -- comma-separated if any
);
CREATE INDEX ix_layer_date ON layer_output(run_date, layer);

CREATE TABLE daily_note (
  date           TEXT PRIMARY KEY,
  body_md        TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
```

#### `0004_learning.sql`

```sql
CREATE TABLE lesson (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  date           TEXT NOT NULL,
  category       TEXT NOT NULL,           -- entry_timing | exit_timing | thesis_quality | sizing | psychology | missed_trade | portfolio
  severity       TEXT NOT NULL,           -- low | medium | high
  pattern_tag    TEXT,
  tickers        TEXT,
  related_thesis TEXT,
  lesson_text    TEXT NOT NULL,
  source_trade_id INTEGER,                -- nullable FK to transaction_log
  FOREIGN KEY(source_trade_id) REFERENCES transaction_log(id)
);
CREATE INDEX ix_lesson_date ON lesson(date);
CREATE INDEX ix_lesson_pattern ON lesson(pattern_tag);

CREATE TABLE calibration (
  run_date       TEXT NOT NULL,
  bucket         TEXT NOT NULL,           -- low | med | high
  declared_win_rate REAL,
  actual_win_rate   REAL,
  drift             REAL,                 -- actual - declared
  n_trades          INTEGER NOT NULL,
  window_days       INTEGER NOT NULL,
  PRIMARY KEY (run_date, bucket, window_days)
);

CREATE TABLE performance_daily (
  date           TEXT PRIMARY KEY,
  equity         REAL NOT NULL,
  ihsg_close     REAL,
  daily_return   REAL,
  ihsg_return    REAL,
  alpha          REAL,
  mtd_return     REAL,
  ytd_return     REAL,
  win_rate_90d   REAL,
  avg_r_90d      REAL,
  expectancy_90d REAL
);

CREATE TABLE evaluation (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  period         TEXT NOT NULL,           -- weekly | monthly
  period_key     TEXT NOT NULL,           -- 2026-W16 or 2026-04
  generated_at   TEXT NOT NULL,
  body_md        TEXT NOT NULL,
  kpi_json       TEXT NOT NULL            -- {"return":.., "alpha":.., "hit_rate":..}
);
CREATE UNIQUE INDEX ix_eval_period ON evaluation(period, period_key);
```

#### `0005_charts.sql`

```sql
CREATE TABLE chart_asset (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  ticker         TEXT NOT NULL,
  as_of          TEXT NOT NULL,          -- snapshot ts
  kind           TEXT NOT NULL,          -- price | volume | sid | broker_flow | orderbook_heatmap
  timeframe      TEXT,                   -- 1m | 5m | 30m | 1d
  payload_json   TEXT NOT NULL           -- raw series, client renders
);
CREATE INDEX ix_chart_ticker_kind ON chart_asset(ticker, kind, as_of);
```

### Verify
- [ ] `make run` applies all five migrations; `applied_migrations` table has 5 rows.
- [ ] `sqlite3 data/fund.db ".tables"` lists: `applied_migrations, calibration, chart_asset, daily_note, evaluation, holding, layer_output, lesson, performance_daily, portfolio_snapshot, signal, theme, thesis, thesis_review, tradeplan, transaction_log, watchlist`.

### Commit
`[M2.2] SQLite schema: 15 tables across core, planning, signals, learning, charts`

---

## Phase M2.3 — API Surface

### Goal
REST endpoints for every entity. Simple: GET (list+filter) / POST (create) / PUT (update) / DELETE (archive).

### Conventions
- Base path `/api/v1/`.
- JSON in, JSON out. Dates `YYYY-MM-DD`, timestamps ISO8601.
- Filter via query string: `?date=2026-04-17&ticker=ANTM&limit=50&offset=0`.
- Response envelope for lists: `{"items":[...],"count":N}`.
- Errors: `{"error":"...","code":"..."}` with proper HTTP status.

### Endpoints

| Path | Methods | Notes |
|------|---------|-------|
| `/healthz` | GET | already from M2.1 |
| `/portfolio/snapshot` | GET list (by date range), POST upsert | |
| `/portfolio/holdings` | GET list (filter by date, ticker), POST upsert batch | |
| `/portfolio/current` | GET | Convenience: latest snapshot + holdings |
| `/transactions` | GET list (filter: ticker, days, side), POST create, PUT update | |
| `/watchlist` | GET list (filter: status), POST upsert, DELETE archive | |
| `/thesis` | GET list (filter: status, ticker), GET one, POST upsert, PUT update | |
| `/thesis/{ticker}/review` | GET list (desc by date), POST append | |
| `/themes` | GET list (filter: status), POST upsert | |
| `/tradeplans` | GET list (filter: plan_date, ticker, status, level), POST create, PUT update | |
| `/signals` | GET list (filter: ticker, layer, kind, since), POST create | |
| `/signals/recent` | GET | Last 100 across all tickers |
| `/layer-outputs` | GET list (filter: run_date, layer, severity), POST create | |
| `/daily-notes/{date}` | GET, PUT (append under `## Auto-Appended`) | |
| `/lessons` | GET list (filter: category, severity, pattern_tag, days), POST create | |
| `/calibration` | GET list (latest per bucket+window), POST upsert | |
| `/performance/daily` | GET list (date range), POST upsert | |
| `/performance/summary` | GET | Returns {mtd, ytd, vs_ihsg, hit_rate_90d, kill_switch} |
| `/evaluations` | GET list (filter: period, period_key), POST create | |
| `/charts` | GET list (filter: ticker, kind, since), POST create | |

### Implementation Steps

1. Create `internal/model/*.go` — one struct per table with JSON tags matching the SQL columns.
2. Create `internal/store/*.go` — one file per entity group: `portfolio.go`, `planning.go`, `signals.go`, `learning.go`, `charts.go`. Each has: `Upsert`, `List(filter)`, `Get(id|key)`, `Delete` where relevant.
3. Create `internal/api/handlers/*.go` — one file per group, same split.
4. Wire in `internal/api/api.go`:
   ```go
   func Mount(r chi.Router, s *store.Store, c *cache.Cache) {
     r.Get("/healthz", Health)
     r.Route("/api/v1", func(r chi.Router) {
       handlers.PortfolioRoutes(r, s, c)
       handlers.PlanningRoutes(r, s)
       handlers.SignalsRoutes(r, s, c)
       handlers.LearningRoutes(r, s)
       handlers.ChartsRoutes(r, s)
     })
   }
   ```
5. Write table-driven unit tests for each `store.List` filter. Keep assertions minimal.

### Verify
- [ ] `curl 127.0.0.1:8787/api/v1/portfolio/current` returns `{}` (empty) with 200.
- [ ] `curl -XPOST -d '{"date":"2026-04-17","equity":53000000,...}' /api/v1/portfolio/snapshot` inserts and returns 201.
- [ ] Every endpoint in the table above returns 200/201/204 for a valid request and 400/404 for bad input.
- [ ] `go test ./...` passes.

### Commit
`[M2.3] CRUD API for 14 entities over /api/v1/*`

---

## Phase M2.4 — Redis Integration

### Goal
Use Redis for hot data that doesn't need to live in SQLite.

### Keys

| Key pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `price:{ticker}` | string (JSON) | 60s | latest price + bid/ask |
| `orderbook:{ticker}` | string (JSON) | 30s | snapshot from `get_orderbook_delta` |
| `broker_flow:{ticker}:1d` | string (JSON) | 5m | today's broker distribution |
| `signal_queue` | list | — | new signals pushed by scripts, consumed by dashboard WS |
| `kill_switch` | string (JSON) | — | `{"active":true,"reason":"..."}` — written by journal.kill_switch_state sync |
| `regime:intraday` | string (JSON) | — | mirrors `vault/data/regime-intraday.json` for fast read |

### Endpoints

- `GET /api/v1/cache/price/{ticker}` — returns cached price or 404.
- `POST /api/v1/cache/price/{ticker}` — sets value + TTL.
- `GET /api/v1/kill-switch` — returns current kill switch state.
- `GET /api/v1/signals/stream` — SSE endpoint; pops from `signal_queue` and emits JSON events. Fall back to long-poll if SSE isn't straightforward.

### Steps

1. Extend `internal/cache/cache.go`:
   ```go
   func (c *Cache) Price(ticker string) (*model.Price, error)
   func (c *Cache) SetPrice(ticker string, p *model.Price, ttl time.Duration) error
   func (c *Cache) PushSignal(s *model.Signal) error
   func (c *Cache) PopSignal(ctx context.Context) (*model.Signal, error)  // BLPOP 1s
   ```
2. Add an SSE handler in `internal/api/handlers/stream.go`. Keep it simple: while context is alive, `PopSignal`, write an SSE frame, flush.
3. In the `POST /api/v1/signals` handler, after DB insert, call `cache.PushSignal(s)`.

### Verify
- [ ] `curl -N 127.0.0.1:8787/api/v1/signals/stream` stays open; posting a signal via another curl produces a line in the stream.
- [ ] Price roundtrip: POST → GET returns the same JSON within TTL.

### Commit
`[M2.4] Redis cache for prices/orderbook + signal SSE stream`

---

## Phase M2.5 — Python Client + Dual-Write

### Goal
Make every workspace script post to the Go API in addition to writing the existing JSON/MD. Zero-breakage: JSON files keep being written; SQLite gets the same data.

### Steps

1. Create `/home/lazywork/workspace/tools/fund_api.py`:
   ```python
   """Thin HTTP client for the fund-manager backend.

   Usage:
       from fund_api import api
       api.post_portfolio_snapshot({...})
       api.get_holdings(date='2026-04-17')
   """
   import os, requests
   BASE = os.environ.get("FUND_API_URL", "http://127.0.0.1:8787/api/v1")
   TIMEOUT = 5
   class FundAPI:
       def _post(self, path, body): ...
       def _get(self, path, **params): ...
       # One method per endpoint from M2.3
   api = FundAPI()
   ```
   - Every method has a docstring listing expected keys.
   - On network error, log a warning and return `None` — NEVER raise. The dashboard is optional; scripts must keep working if the server is down.
   - All calls are idempotent (POST = upsert).

2. **Dual-write wiring** — edit these files to call `fund_api.api.*` after their existing write:
   - `tools/trader/portfolio_health.py` — in `compute_portfolio_state()`: after writing `portfolio-state.json`, call `api.post_portfolio_snapshot()` + `api.post_holdings(batch)`.
   - `tools/trader/journal.py`:
     - `log_trade()` → `api.post_transaction()`.
     - `close_trade()` → `api.put_transaction(id, pnl_fields)`.
     - `log_lesson_v2()` → `api.post_lesson()`.
     - `append_thesis_review()` → `api.post_thesis_review(ticker, ...)`.
     - `append_daily_layer_section()` → `api.put_daily_note(date, body)`.
     - `set_thesis_action()` (new in M1.2) → `api.put_holding_action(ticker, action)`.
     - `set_intraday_posture()` (new in M1.2) → `api.put_regime_intraday(...)` (goes via Redis endpoint).
     - `kill_switch_state()` result → when `active` turns True, push to `api.put_kill_switch(...)`.
     - `confidence_calibration()` → `api.post_calibration(row)`.
   - `tools/trader/tradeplan.py` — finalised plan → `api.post_tradeplan(plan)`.
   - `tools/trader/runtime_layer2_screening.py` — shortlist → `api.post_watchlist_batch(...)`, signals → `api.post_signal(...)`.
   - `tools/trader/runtime_monitoring.py` — detected setups → `api.post_signal(...)`.
   - `tools/trader/runtime_eod_publish.py` — EOD summary → `api.put_daily_note(date, ...)` + `api.post_performance_daily(row)`.

3. **One-time backfill script** `/home/lazywork/workspace/tools/fund_backfill.py`:
   - Walks `vault/data/*.json`, `vault/daily/*.md`, `vault/thesis/*.md`, `vault/lessons/*.md`, `vault/themes/*.md`, `runtime/orders/*.jsonl`, `runtime/tradeplans/*.md`.
   - Posts each to the API.
   - Idempotent (relies on upsert). Log skipped rows.
   - CLI: `python tools/fund_backfill.py --source all` or `--source lessons`.

### Verify
- [ ] With server running: `python tools/trader/portfolio_health.py` produces both the JSON file and a row in `portfolio_snapshot`.
- [ ] With server DOWN: same script still produces the JSON file (no exception, just a warning line).
- [ ] `python tools/fund_backfill.py --source all` completes; row counts in SQLite match file counts in vault.

### Commit
`[M2.5] Python client + dual-write for 8 modules; backfill script`

---

## Phase M2.6 — Dashboard Pages

### Goal
Boss O opens `http://127.0.0.1:3000` and sees everything the fund is doing, today and historically. Not pretty — functional. Priority: legibility > style.

### Pages

All pages server-render from `/api/v1/*`. Use shadcn `Card`, `Table`, `Tabs`, `Badge`.

#### `/` — Overview

Top row: 4 cards — Equity (current + Δ day/Δ MTD), Cash %, Drawdown %, Posture badge.
Middle: equity curve (recharts LineChart, 60d) next to IHSG overlay.
Below: `Today's Activity` — last 20 layer_output rows for today, grouped by layer.
Right column: live signals feed (SSE → top-10 signals, newest first, 5s pulse).

#### `/portfolio`

Holdings table: ticker, shares, avg cost, last, mkt value, %P&L, %of equity, sector, action, thesis status.
Row click → `/ticker/{ticker}`.
Below: concentration bar chart (by sector).

#### `/watchlist`

Columns: ticker, added, status, conviction, themes, last screen hit, 5 criteria bar.
Filter: status, conviction, theme.
Add manually via dialog.

#### `/tradeplans`

Tabs: Today | Queue | Executed | Expired.
Table: ticker, mode, setup, entry range, stop, target1/2, size, risk%, level, priority, calibration drift badge.
Expandable row shows `raw_md`.

#### `/signals`

Full table + filter panel. Filters: ticker, layer, kind, severity, days.
Sparkline of signal count by day in header.

#### `/journal`

Tabs: Daily | Weekly | Monthly | Lessons.
Daily: timeline per date, grouped by layer, collapsible.
Lessons: filter by category, severity, pattern_tag. Click → shows `lesson_text` + source trade.

#### `/thesis`

Left column: list of tickers with status (active/closed/archived).
Right: selected thesis body + review log (desc by date).
Edit textarea + Save button → PUT `/thesis`.

#### `/themes`

Cards grid. Each card: name, sector, status, related tickers (chips that link to ticker page).
Click theme → modal with `body_md`.

#### `/performance`

Equity curve (full history).
KPI row: MTD, YTD, vs IHSG, alpha, hit rate 90d, avg R, expectancy, max DD.
Pattern table: hit rate per pattern_tag (from lessons + trades).
Sector table: hit rate per sector.
Kill-switch banner (red) if active.

#### `/evaluation`

Tabs: Weekly | Monthly. List of evaluations, click to read full body. Newest first.

#### `/ticker/[ticker]`

Header: ticker, sector, current price, broker-flow snapshot.
Tabs:
- **Thesis** — body + review log
- **Tradeplans** — all plans for this ticker (chronological)
- **Signals** — all signals for this ticker
- **Transactions** — open + closed
- **Charts** — price, SID, broker_flow (from `chart_asset`)

### Implementation Notes

- `lib/api.ts` exports typed fetchers per endpoint.
- Each page is a server component; interactive parts (filters, streams) are client components wrapping.
- No global state library — just URL params for filters. Use `useRouter` for updates.
- For SSE signals, a small `<SignalsFeed />` client component connects to `/api/v1/signals/stream`.

### Verify
- [ ] Every page renders with seeded data and returns within 1s on localhost.
- [ ] Navigate `/` → `/portfolio` → click holding → `/ticker/{t}`. Breadcrumb back works.
- [ ] Post a signal via curl → appears in the signals feed within ~5s.
- [ ] Filters preserve via URL (reload keeps them).

### Commit
`[M2.6] Dashboard — 10 pages + typed client`

---

## Phase M2.7 — End-to-End Test

### Goal
Run one full simulated trading day (like M1.6) with the Go backend live. Verify every artifact lands in both the vault and the dashboard.

### Checklist

1. Start backend + frontend.
2. Run `python tools/fund_backfill.py --source all`. Open dashboard — data should be populated.
3. Run M1.6 smoke test flow.
4. After each layer, open the relevant dashboard page and verify the new record appears.
5. Close one simulated trade, confirm:
   - `transactions` table row has pnl.
   - `lessons` table has suggested lesson.
   - `/performance` updates hit rate.
6. Flip kill-switch by manually inserting 3 losing trades into `transactions`, run `journal.kill_switch_state()`. Dashboard banner should turn red.
7. Kill the backend mid-run — confirm scripts continue (they should warn, not error).
8. Restart backend — confirm no data loss (vault/data/*.json still has today's state; next script run re-pushes).
9. Write a short note `docs/fund-manager-plan/output/m2-smoke.md` documenting pass/fail for each check.

### Verify
- [ ] Every dashboard page has data.
- [ ] Kill-switch banner triggers and clears correctly.
- [ ] Backend-down path doesn't break any script.

### Commit
`[M2.7] End-to-end smoke test — dashboard live, kill-switch verified`

---

## Mission 2 Complete When

- [ ] Backend on 127.0.0.1:8787 with 15 tables, 20+ endpoints, Redis cache + SSE.
- [ ] Frontend on 127.0.0.1:3000 with 10 pages, all server-rendered.
- [ ] `tools/fund_api.py` is imported by at least 5 workspace scripts.
- [ ] Vault JSON/MD and SQLite stay in sync on every write.
- [ ] Kill-switch, calibration drift, posture, and stale thesis are all visible in the dashboard.
- [ ] `code/fund-manager/README.md` has accurate setup steps.
- [ ] `tools/CLAUDE.md` lists `fund_api.py` + `fund_backfill.py`.

---

## Appendix A — Minimum Viable Go Skeleton

If the executor stalls on Go, here's a tight starter for `backend/cmd/server/main.go`:

```go
package main

import (
    "context"
    "database/sql"
    "log"
    "net/http"
    "os"
    "path/filepath"
    "time"

    "github.com/go-chi/chi/v5"
    "github.com/go-chi/chi/v5/middleware"
    "github.com/joho/godotenv"
    "github.com/redis/go-redis/v9"
    _ "modernc.org/sqlite"
)

func main() {
    _ = godotenv.Load("../../.env.local")

    db, err := sql.Open("sqlite", "../data/fund.db")
    must(err)
    must(runMigrations(db, "migrations"))

    rdb := redis.NewClient(&redis.Options{
        Addr: os.Getenv("REDIS_HOST") + ":" + os.Getenv("REDIS_PORT"),
    })
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()
    must(rdb.Ping(ctx).Err())

    r := chi.NewRouter()
    r.Use(middleware.Logger, middleware.Recoverer)
    r.Get("/healthz", func(w http.ResponseWriter, _ *http.Request) { w.Write([]byte(`{"status":"ok"}`)) })
    // mount /api/v1 routes here once handlers exist

    addr := "127.0.0.1:8787"
    log.Printf("fund-manager listening on %s", addr)
    must(http.ListenAndServe(addr, r))
}

func runMigrations(db *sql.DB, dir string) error {
    _, err := db.Exec(`CREATE TABLE IF NOT EXISTS applied_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`)
    if err != nil { return err }
    entries, err := os.ReadDir(dir)
    if err != nil { return err }
    for _, e := range entries {
        if filepath.Ext(e.Name()) != ".sql" { continue }
        var exists int
        _ = db.QueryRow(`SELECT COUNT(1) FROM applied_migrations WHERE name=?`, e.Name()).Scan(&exists)
        if exists == 1 { continue }
        b, err := os.ReadFile(filepath.Join(dir, e.Name()))
        if err != nil { return err }
        if _, err := db.Exec(string(b)); err != nil { return err }
        if _, err := db.Exec(`INSERT INTO applied_migrations(name) VALUES(?)`, e.Name()); err != nil { return err }
    }
    return nil
}

func must(err error) { if err != nil { log.Fatal(err) } }
```

## Appendix B — Dashboard Folder Conventions

```
frontend/app/
├── layout.tsx          # shared nav
├── page.tsx            # / overview
├── portfolio/page.tsx
├── watchlist/page.tsx
├── tradeplans/page.tsx
├── signals/page.tsx
├── journal/
│   ├── page.tsx
│   ├── lessons/page.tsx
│   └── [date]/page.tsx
├── thesis/page.tsx
├── themes/page.tsx
├── performance/page.tsx
├── evaluation/page.tsx
└── ticker/[ticker]/page.tsx

frontend/components/
├── nav.tsx
├── signals-feed.tsx    # client component, SSE
├── equity-curve.tsx
├── kill-switch-banner.tsx
└── kpi-card.tsx
```

## Appendix C — Env Vars Used

Already in `.env.local`:
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `AIRTABLE_PAT`, `AIRTABLE_BASE_ID` (M2 does not need these; workspace scripts keep using them)
- `TELEGRAM_*` (untouched)
- Trading creds (untouched)

New (optional, defaults baked in):
- `FUND_API_URL` — default `http://127.0.0.1:8787/api/v1`
- `FUND_API_PORT` — default `8787`
- `FUND_DB_PATH` — default `../data/fund.db`
