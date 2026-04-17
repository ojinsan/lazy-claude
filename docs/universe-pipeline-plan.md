# Universe Pipeline Rebuild — Execution Plan

**For:** cheaper AI (Sonnet) executing end-to-end.
**Goal:** Replace the narrow L2 universe with a wider, signal-driven candidate pool from local services.

---

## Ground Rules

1. Work phase by phase. Commit each phase.
2. Do NOT touch `~/bitstock/backend/` (cloud) — we are replacing it, not modifying it.
3. The local backend is `code/fund-manager/backend/` (Go, chi, SQLite, Redis, port 8787).
4. All new Python connectors go in `tools/trader/`.
5. New skills/playbook changes follow MECE: playbook = workflow, skill = rules + tools.
6. Test each endpoint before wiring into the screening pipeline.

---

## Architecture After This Plan

```
Sources (scrapers)                    Local Backend (Go, :8787)           Trader Pipeline
─────────────────                    ──────────────────────────           ───────────────
Telegram scraper (Python)   ──POST──►  /feed/telegram/insight             
  ~/workspace/services/                  ↓ stores in SQLite                L1: Threads + RAG
  telegram-scraper/                      insights table                    L2: candidate_universe()
                                                                             ├── holds (GET /watchlist)
Threads scraper (Playwright) ─────────────────────────────────────────────►  ├── L1 today (live)
  tools/general/playwright/                                                  ├── telegram positives
  threads-scraper.js                 GET /insights/positive-candidates       │   (GET /insights/positive-candidates)
                                       → high-confidence tickers             ├── RAG search hits
                                                                             │   (POST /rag/search)
Lark watchlist ────────────►         GET /watchlist                           └── (NO alphabetical fill)
  (manual curation,                    → active watchlist from Lark
   synced to local DB)
```

---

## Current State

| Source | Now | Problem |
|--------|-----|---------|
| Holds (Superlist) | Airtable `Superlist` via `airtable_client.py` | External dependency, slow, costs money |
| L1 candidates | Yesterday's L1 output file | Stale by definition; should use today's L1 |
| Backend watchlist | Cloud `~/bitstock/backend` API or missing `vault/data/watchlist.json` | Cloud = latency + dependency; local file = empty |
| Alphabetical fill | `stocklist.csv` sorted A-Z up to 120 | Pure noise, no edge |

---

## Phase 1 — Local Telegram Scraper Service

### 1.1 Copy + adapt telegram scraper

```bash
cp -r ~/bitstock/scrapper_client/telegram ~/workspace/services/telegram-scraper
```

Edit `~/workspace/services/telegram-scraper/api/client.py`:
- Change `backend_url` from cloud URL to `http://127.0.0.1:8787`
- POST endpoint: `/feed/telegram/insight` (same schema as cloud backend)

**Key:** the telegram scraper POSTs insights with fields:
```json
{
  "time": "ISO8601",
  "content": "message text",
  "participant_type": "admin|member",
  "address_text": "BBRI BMRI",
  "source": "group/channel name",
  "topic": "...",
  "confidence": -100..+100
}
```

### 1.2 Add insight ingestion to fund-manager backend

The fund-manager backend needs a new handler group to receive + store telegram insights.

**Migration `0008_insights.sql`:**
```sql
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    ticker TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    participant_type TEXT NOT NULL DEFAULT '',
    ai_recap TEXT DEFAULT '',
    confidence INTEGER DEFAULT 0,
    address_text TEXT DEFAULT '',
    source TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_insights_ticker_date ON insights(ticker, occurred_at DESC);
CREATE INDEX idx_insights_confidence ON insights(confidence DESC);
```

**New handler file** `internal/api/handlers/insights.go`:
```go
// Routes:
r.Post("/feed/telegram/insight", ingestInsights(s))
r.Get("/insights/positive-candidates", positiveCandidates(s))
r.Post("/rag/search", ragSearch(s))
```

**Endpoint details:**

| Route | Method | Purpose | Query |
|-------|--------|---------|-------|
| `/feed/telegram/insight` | POST | Receive telegram scraper batch | INSERT INTO insights |
| `/insights/positive-candidates` | GET | Return high-confidence tickers from recent insights | `SELECT DISTINCT ticker FROM insights WHERE confidence >= 60 AND occurred_at >= date('now', '-3 days') ORDER BY confidence DESC LIMIT 50` |
| `/rag/search` | POST | Search insights by query string (simple LIKE for now, semantic later) | `SELECT * FROM insights WHERE content LIKE '%query%' OR ai_recap LIKE '%query%' ORDER BY occurred_at DESC LIMIT 20` |

RAG v3 in cloud backend uses embeddings. For local MVP: use SQLite FTS5 (full-text search) instead. Upgrade to embeddings later if needed.

**If using FTS5, add to migration:**
```sql
CREATE VIRTUAL TABLE insights_fts USING fts5(ticker, content, ai_recap, source);
-- Trigger to keep FTS in sync
CREATE TRIGGER insights_fts_insert AFTER INSERT ON insights BEGIN
    INSERT INTO insights_fts(rowid, ticker, content, ai_recap, source)
    VALUES (new.id, new.ticker, new.content, new.ai_recap, new.source);
END;
```

Then RAG search becomes:
```sql
SELECT i.* FROM insights i
JOIN insights_fts f ON i.id = f.rowid
WHERE insights_fts MATCH ?
ORDER BY rank
LIMIT 20
```

### 1.3 Systemd service for telegram scraper

Create `~/workspace/services/telegram-scraper/telegram-scraper.service`:
```ini
[Unit]
Description=Telegram insight scraper
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/lazywork/workspace/services/telegram-scraper
ExecStart=/home/lazywork/workspace/services/telegram-scraper/.venv/bin/python main.py
Restart=on-failure
RestartSec=30
Environment=BACKEND_URL=http://127.0.0.1:8787

[Install]
WantedBy=default.target
```

```bash
systemctl --user link ~/workspace/services/telegram-scraper/telegram-scraper.service
systemctl --user enable --now telegram-scraper
```

### 1.4 Test

```bash
# Start fund-manager if not running
cd code/fund-manager/backend && make run &

# Check insight ingestion
curl -X POST http://127.0.0.1:8787/feed/telegram/insight \
  -H 'Content-Type: application/json' \
  -d '{"insights":[{"time":"2026-04-17T10:00:00+07:00","content":"BBRI strong accumulation","participant_type":"admin","address_text":"BBRI","source":"test","confidence":80}]}'

# Check positive candidates
curl http://127.0.0.1:8787/insights/positive-candidates

# Check RAG search
curl -X POST http://127.0.0.1:8787/rag/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"accumulation banking"}'
```

### 1.5 Commit
`[Universe 1] Local telegram scraper + fund-manager insight ingestion (POST /feed/telegram/insight, GET /insights/positive-candidates, POST /rag/search)`

---

## Phase 2 — Migrate Watchlist + Holds to Local Backend

### 2.1 Watchlist source

Fund-manager already has `GET /watchlist`, `POST /watchlist`, `DELETE /watchlist/{ticker}`. Currently wired to Lark in `~/bitstock/backend`.

Two options:
- **(a)** Wire Lark client into fund-manager (copy `~/bitstock/backend/lark/client.go` → `code/fund-manager/backend/internal/lark/`)
- **(b)** Manage watchlist directly in SQLite via `POST /watchlist` — no Lark dependency

**Recommendation: (b)** for now. Boss O curates watchlist via Claude or a quick script. Lark sync can be added later as a background job.

The fund-manager already has a `watchlist` table (check `0002_planning.sql`). Verify schema:
```bash
sqlite3 code/fund-manager/backend/fund.db ".schema watchlist"
```

### 2.2 Migrate Superlist holds

Replace Airtable `Superlist` reads in the trader pipeline with local backend calls.

**New Python connector** `tools/trader/fund_manager_client.py`:
```python
"""
Local fund-manager backend client.
Base URL: http://127.0.0.1:8787
"""
import requests

BASE = "http://127.0.0.1:8787"

def get_watchlist() -> list[dict]:
    return requests.get(f"{BASE}/watchlist").json()

def upsert_watchlist(ticker: str, data: dict) -> dict:
    return requests.post(f"{BASE}/watchlist", json={"ticker": ticker, **data}).json()

def archive_watchlist(ticker: str) -> dict:
    return requests.delete(f"{BASE}/watchlist/{ticker}").json()

def get_positive_candidates(min_confidence: int = 60, days: int = 3) -> list[dict]:
    return requests.get(f"{BASE}/insights/positive-candidates",
                        params={"min_confidence": min_confidence, "days": days}).json()

def rag_search(query: str, limit: int = 20) -> list[dict]:
    return requests.post(f"{BASE}/rag/search", json={"query": query, "limit": limit}).json()

def get_thesis(ticker: str) -> dict:
    return requests.get(f"{BASE}/thesis/{ticker}").json()

def upsert_thesis(ticker: str, data: dict) -> dict:
    return requests.put(f"{BASE}/thesis/{ticker}", json=data).json()

def get_holds() -> list[dict]:
    """Get active watchlist entries where status = 'hold'."""
    wl = get_watchlist()
    return [w for w in wl if (w.get("status") or "").lower() == "hold"]
```

### 2.3 Update `runtime_layer2_screening.py`

Replace `extract_backend_watchlist()`:
- Old: reads `vault/data/watchlist.json` + calls cloud `/watchlist`
- New: calls `fund_manager_client.get_watchlist()` + `fund_manager_client.get_positive_candidates()`

Replace hold extraction:
- Old: reads from Airtable
- New: calls `fund_manager_client.get_holds()`

### 2.4 Commit
`[Universe 2] fund_manager_client.py + migrate watchlist/holds from Airtable to local Go backend`

---

## Phase 3 — Threads Username Scraping (Today's L1)

### 3.1 Add username-path scraping to threads-scraper.js

Current threads-scraper.js supports keyword search. Add a second mode: `--username <handle>` that:
1. Navigates to `https://www.threads.net/@{username}`
2. Scrolls and collects the last N posts (default 10)
3. Returns same JSON format as search results

```bash
node threads-scraper.js --username "ezpada_trader" --limit 10
node threads-scraper.js --username "stockbit_official" --limit 5
```

### 3.2 Create `skills/trader/threads-universe.md`

New skill (not search — universe discovery):
```markdown
# Threads Universe Discovery

## Purpose
Scrape specific Threads accounts for fresh stock ideas. Runs during L1
to produce today's narrative candidates — not yesterday's.

## Accounts To Scrape (Boss O maintains this list)
| Handle | Why |
|--------|-----|
| `ezpada_trader` | IDX flow analysis, sector rotation calls |
| (add more) | (Boss O adds over time) |

## How
For each account:
1. `node tools/general/playwright/threads-scraper.js --username "{handle}" --limit 10`
2. Extract ticker mentions from each post (regex: 4-char uppercase)
3. Deduplicate and return as candidate list

## Output
Return list of {ticker, source_handle, post_snippet, timestamp}.
Feed into L1 narrative candidates bucket.
```

### 3.3 Wire into L1 playbook

Add to `playbooks/trader/layer-1-global-context.md` Tools section:
```markdown
| Threads accounts | `node tools/general/playwright/threads-scraper.js --username "{handle}" --limit 10` — scrape today's posts from tracked accounts |
```

Add to Step logic: after RAG + keyword Threads search, also scrape tracked accounts. Merge ticker mentions into narrative candidate list.

### 3.4 Fix L2 to use today's L1 (not yesterday's)

In `runtime_layer2_screening.py`, change `extract_layer1_candidates()`:
- Old: reads `runtime/notes/layer_1_global_context/{yesterday}.jsonl`
- New: reads `runtime/notes/layer_1_global_context/{today}.jsonl`
- Fallback: if today's file doesn't exist yet (L2 ran before L1), use yesterday's

### 3.5 Commit
`[Universe 3] Threads username scraping + L1 uses today's results + threads-universe skill`

---

## Phase 4 — Rebuild candidate_universe()

### 4.1 New universe function

Replace `candidate_universe()` in `runtime_layer2_screening.py`:

```python
def candidate_universe() -> tuple[list[str], dict]:
    """
    Build L2 candidate pool from 4 sources (no alphabetical fill):
    1. Holds — fund_manager_client.get_holds()
    2. Today's L1 candidates — from today's L1 output (with yesterday fallback)
    3. Telegram positive candidates — fund_manager_client.get_positive_candidates()
    4. Watchlist — fund_manager_client.get_watchlist()

    No max cap. No alphabetical fill. Deduped by ticker, priority order above.
    """
    holds = [h["ticker"] for h in fund_manager_client.get_holds()]
    layer1 = extract_layer1_candidates_today()
    telegram = [c["ticker"] for c in fund_manager_client.get_positive_candidates()]
    watchlist = [w["ticker"] for w in fund_manager_client.get_watchlist()
                 if w.get("status", "").lower() != "hold"]

    ordered = []
    for bucket in (holds, layer1, telegram, watchlist):
        for ticker in bucket:
            t = ticker.upper().strip()
            if t and t not in ordered:
                ordered.append(t)

    return ordered, {
        "holds": len(holds),
        "layer1_today": len(layer1),
        "telegram_positives": len(telegram),
        "watchlist": len(watchlist),
        "total": len(ordered),
    }
```

### 4.2 Remove old sources

- Delete `extract_backend_watchlist()` (replaced by fund_manager_client)
- Delete the alphabetical fill block
- Delete `STOCKLIST` constant and `load_stock_universe()` if no other consumer

### 4.3 Update L2 playbook

In `playbooks/trader/layer-2-stock-screening.md`, update `## Universe Prep`:
```markdown
## Universe Prep

Candidate pool built from 4 sources (no alphabetical fill):

1. **Holds** — `fund_manager_client.get_holds()` (always included, always first)
2. **Today's L1** — ticker mentions from today's L1 output (yesterday fallback if L1 hasn't run)
3. **Telegram positives** — `fund_manager_client.get_positive_candidates(min_confidence=60, days=3)` — high-confidence tickers from local telegram insight DB
4. **Watchlist** — `fund_manager_client.get_watchlist()` (Boss O's curated names, non-hold)

No max cap. No alphabetical fill. If the pool is small today, that's signal — market may not have actionable names.
```

### 4.4 Commit
`[Universe 4] Rebuild candidate_universe() — 4 signal-driven sources, no alphabetical fill`

---

## Phase 5 — Fund-Manager Service Setup

### 5.1 Ensure fund-manager runs as a service

Create/update systemd unit:
```ini
[Unit]
Description=Fund Manager local backend
After=network.target redis.target

[Service]
Type=simple
WorkingDirectory=/home/lazywork/workspace/code/fund-manager/backend
ExecStart=/home/lazywork/workspace/code/fund-manager/backend/fund-manager
Restart=on-failure
RestartSec=10
Environment=FUND_API_PORT=8787
Environment=REDIS_HOST=127.0.0.1
Environment=REDIS_PORT=6379
Environment=DB_PATH=/home/lazywork/workspace/code/fund-manager/backend/fund.db

[Install]
WantedBy=default.target
```

### 5.2 Populate initial watchlist

Boss O provides 40-80 tickers. Script to seed:
```bash
for t in BBRI BMRI BBCA TLKM ANTM ADRO AKRA ...; do
  curl -X POST http://127.0.0.1:8787/watchlist \
    -H 'Content-Type: application/json' \
    -d "{\"ticker\":\"$t\",\"status\":\"active\",\"source\":\"manual\"}"
done
```

### 5.3 Verify full pipeline

```bash
# 1. Fund-manager running?
curl http://127.0.0.1:8787/watchlist

# 2. Telegram scraper posting?
journalctl --user -u telegram-scraper -f

# 3. Positive candidates available?
curl http://127.0.0.1:8787/insights/positive-candidates

# 4. L2 universe builds?
cd tools/trader && python3 -c "
from runtime_layer2_screening import candidate_universe
tickers, meta = candidate_universe()
print(f'Universe: {meta}')
print(f'Tickers: {tickers[:20]}...')
"
```

### 5.4 Commit
`[Universe 5] Systemd services + initial watchlist seed + full pipeline verification`

---

## Files That Should Exist When Plan Completes

### New
```
services/telegram-scraper/              (copied + adapted from ~/bitstock/scrapper_client/telegram)
services/telegram-scraper/telegram-scraper.service
tools/trader/fund_manager_client.py     (local backend Python client)
skills/trader/threads-universe.md       (username-path scraping skill)
code/fund-manager/backend/migrations/0008_insights.sql
code/fund-manager/backend/internal/api/handlers/insights.go
```

### Modified
```
code/fund-manager/backend/internal/api/router.go    (add insights routes)
tools/general/playwright/threads-scraper.js          (add --username mode)
tools/trader/runtime_layer2_screening.py             (new candidate_universe, today's L1, fund_manager_client)
playbooks/trader/layer-1-global-context.md           (Threads accounts tool)
playbooks/trader/layer-2-stock-screening.md          (new Universe Prep section)
tools/INDEX.md                                       (fund_manager_client row)
```

### Removed
```
(in runtime_layer2_screening.py)
- extract_backend_watchlist()           → replaced by fund_manager_client
- Alphabetical fill block              → removed entirely
- STOCKLIST constant                    → removed if no other consumer
```

---

## Dependency Order

```
Phase 1 (telegram + backend insights)
  → Phase 2 (watchlist + holds migration) — needs backend running
  → Phase 4 (rebuild candidate_universe) — needs all sources ready
Phase 3 (Threads username) — independent, can run in parallel with 1-2
Phase 5 (services + verification) — after 1-4, ensures persistence
```

---

## Out of Scope

- `~/bitstock/backend/` (cloud) — do not modify, we are migrating away from it
- Embedding-based RAG — FTS5 is the MVP; upgrade later
- Airtable removal — gradually reduce dependency, don't delete; some skills still use it
- Stockbit scraper (`~/bitstock/scrapper_client/stockbit/`) — separate concern, already works
