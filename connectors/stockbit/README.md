# Connector: Stockbit

Type: REST API (direct + backend proxy)
Script: `tools/trader/api.py`
Config: `tools/trader/config.py`

## Architecture
Two-layer API access:
- **Stockbit direct** — index/regime data, realtime orderbook, tick data
- **Backend proxy** (`BACKEND_BASE_URL`) — cached stock data, broker analysis, RAG queries

## Auth
Token priority: Backend `/token-store/stockbit` → local cache file (`ORDERBOOK_STATE_DIR`)
Env vars: `BACKEND_URL`, `BACKEND_TOKEN`, `STOCKBIT_TOKEN` (fallback)

## Key Operations
- `get_index_data()` — IHSG, LQ45, sectoral indices
- `get_orderbook(sid)` — live orderbook for a stock
- `get_broker_flow(sid)` — broker buy/sell aggregates
- `query_rag(question)` — backend RAG for context
- `get_watchlist()` — backend watchlist fetch
