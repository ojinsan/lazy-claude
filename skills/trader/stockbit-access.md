# Stockbit Access

## Purpose

Handle Stockbit API access for trading operations: data retrieval, screener, and order execution.

## Safety Rules

- Tokens, cookies, and credentials are sensitive — never reveal in output.
- **Order execution (buy/sell/cancel/amend) requires explicit confirmation from Boss O before calling.**
- Always read back the order params (symbol, price, shares, side) and wait for "confirm" before placing.
- Never place orders speculatively or as part of analysis flow — only when explicitly instructed.
- Use minimum access needed. If Boss O has not authorized an action, stop and ask.

## Carina Token Flow

Carina token (for portfolio/orders) is separate from the main Stockbit data token.
**No PIN is sent at order placement time** — the Bearer token is sufficient for buy/sell/cancel/amend.
PIN is required only to OBTAIN the Carina token.

**How it works:**
```
POST carina.stockbit.com/auth/v2/login
Body: {"login_token": <main_stockbit_token>, "pin": "589123"}
Response: {"data": {"access_token": "eyJ..."}}
```

**Auto-refresh (fully automated):**
```python
from api import refresh_carina_token
token = refresh_carina_token()
# reads STOCKBIT_TRADING_PIN + CARINA_ACCOUNT_NUMBER from .env.local
# saves to runtime/tokens/carina_token.json
```

`_carina_get` and `_carina_post` call `refresh_carina_token()` automatically on 401.

**Manual refresh (if auto fails):**
1. Log into stockbit.com in browser
2. DevTools → Network → any carina request → copy Authorization Bearer value
3. `from api import save_carina_token; save_carina_token("eyJ...")`

**When to refresh:** Automatically triggered on 401. Manual only if `get_stockbit_token()` itself is expired.

## API Layers

| Layer | Domain | Auth | Use for |
|-------|--------|------|---------|
| exodus | exodus.stockbit.com | stockbit token | screener, emitten, watchlist, orderbook, broker |
| carina | carina.stockbit.com | carina token | portfolio, orders, balance |

## Available Operations

### Screener (via MCP or api.py)
- `stockbit_screener_templates()` — list saved templates
- `stockbit_screener_presets()` — Guru/Value/Growth preset categories
- `stockbit_screener_metrics(search)` — search filterable metrics (fitem_ids)
- `stockbit_run_template(template_id)` — run a preset/saved screener
- `stockbit_run_custom_screener(filters_json, universe_scope)` — custom filter screener

### Market Data
- `stockbit_emitten_info(symbol)` — company snapshot (price, change, avg vol, market cap)
- `get_stockbit_orderbook(symbol)` — live orderbook
- `get_stockbit_running_trade(symbol)` — running trades with broker codes
- `get_emitten_info(symbol)` — company info from exodus

### Watchlist (Stockbit native)
- `stockbit_watchlists()` — list user's watchlists
- `stockbit_watchlist_items(watchlist_id)` — stocks in a watchlist

### Portfolio & Balance (Carina)
- `get_portfolio()` — full portfolio summary + positions
- `carina_position_detail(stock_code)` — per-stock P/L detail
- `carina_cash_balance()` — available cash + trade limit

### Orders (Carina) — REQUIRES EXPLICIT CONFIRMATION
- `carina_orders(stock_code)` — list open/today orders (safe, read-only)
- `carina_place_buy(symbol, price, shares)` — **REAL BUY ORDER**
- `carina_place_sell(symbol, price, shares)` — **REAL SELL ORDER**
- `carina_cancel_order(order_id)` — cancel open order
- `carina_amend_order(order_id, price, shares)` — amend price/qty

## Order Execution Flow

1. Boss O says: "buy X lot BBCA at 9000"
2. Read back: "Confirm: BUY BBCA 10 lot (1000 shares) @ Rp 9,000 RG day order?"
3. Wait for explicit "yes" / "confirm"
4. Call `carina_place_buy` or `api.place_buy_order`
5. Report back order_id and status

Never skip step 2-3.
