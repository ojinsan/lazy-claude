# Connector: Stockbit

Type: REST API (direct + backend proxy)
Script: `tools/trader/api.py`
Config: `tools/trader/config.py`

## Architecture

Three API layers:
- **exodus.stockbit.com** — main Stockbit API (screener, emitten, watchlist, orderbook, broker)
- **carina.stockbit.com** — broker/portfolio API (orders, balance, positions)
- **Backend proxy** (`BACKEND_BASE_URL`) — cached stock data, broker analysis, RAG queries

## Auth

| Layer    | Token Source                                    | Helper                |
|----------|-------------------------------------------------|-----------------------|
| exodus   | Backend `/token-store/stockbit` → in-memory     | `get_stockbit_token()`|
| carina   | Manual `carina_token.json` → fallback to exodus | `save_carina_token()` |
| backend  | `BACKEND_TOKEN` env var                         | `BACKEND_HEADERS`     |

Env vars: `BACKEND_URL`, `BACKEND_TOKEN`, `STOCKBIT_TOKEN` (fallback)

## HTTP Helpers (internal)

| Helper            | Domain                    | Auth         |
|-------------------|---------------------------|--------------|
| `_stockbit_get`   | exodus.stockbit.com       | exodus token |
| `_stockbit_post`  | exodus.stockbit.com       | exodus token |
| `_carina_get`     | carina.stockbit.com       | carina token |
| `_carina_post`    | carina.stockbit.com       | carina token |
| `_carina_delete`  | carina.stockbit.com       | carina token |
| `_backend_get`    | BACKEND_BASE_URL          | backend token|
| `_backend_post`   | BACKEND_BASE_URL          | backend token|

## Key Operations

### Price & Market Data
- `get_price(ticker)` — latest price
- `get_candles(ticker, timeframe, limit)` — OHLCV candles
- `get_stockbit_index(symbol)` — IHSG/index snapshot
- `get_stockbit_orderbook(symbol)` — live orderbook
- `get_orderbook_delta(ticker)` — orderbook change detection (whale/retail)
- `get_stockbit_running_trade(symbol)` — running trades with broker codes
- `get_emitten_info(symbol)` — company snapshot (price, change, avg volume, market cap)

### Screener
- `get_screener_templates()` — list saved templates
- `get_screener_presets()` — Guru/Value/Growth preset categories
- `get_screener_metrics()` — all filterable metrics with fitem_ids
- `get_screener_universe()` — available universes (IHSG, LQ45, IDX30, sectors)
- `get_screener_favorites()` — user's favorites
- `run_screener_template(template_id)` — run a preset/saved screener
- `run_screener_custom(filters, universe)` — run custom screener with filter rules

### Watchlist (Stockbit native)
- `get_stockbit_watchlists()` — list user's watchlists
- `get_stockbit_watchlist(watchlist_id)` — items in a watchlist
- `get_stockbit_watchlist_metrics()` — available financial columns

### Broker Analysis
- `get_broker_info(ticker)` — bandar detector + top buyers/sellers
- `get_broker_distribution(ticker)` — 30-day broker accumulation (backend)
- `get_broker_movement(ticker, period)` — broker position history

### SID & Emitten
- `get_stockbit_sid_count(symbol)` — SID count + accumulation/distribution signal
- `get_emitten_info(symbol)` — company info snapshot

### Portfolio & Balance (Carina)
- `get_portfolio()` — full portfolio with summary + positions
- `get_position_detail(stock_code)` — per-stock position detail
- `get_cash_balance()` — available cash on hand
- `get_cash_info(stock_code, order_id)` — trade limit, day trade buying power

### Orders (Carina)
- `get_orders(stock_code)` — list open/today orders
- `get_order_detail(order_id)` — single order detail
- `place_buy_order(symbol, price, shares)` — **REAL order** — confirm before calling
- `cancel_order(order_id)` — cancel open order
- `amend_orders(amend_requests)` — bulk amend prices/shares
- `cancel_stop_order(order_id)` — cancel smart/stop order

### Backend
- `rag_search(question, ticker)` — RAG query for stock context
- `get_market_context()` — market regime context
- `get_watchlist()` — backend watchlist (strategy state)
