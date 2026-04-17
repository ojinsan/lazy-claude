# Stockbit Access

## Purpose

Handle Stockbit API access for trading operations: data retrieval, screener, and order execution.

## Primary Tooling

- Manual: `tools/manual/stockbit.md` — auth layers, token flow, all available functions
- Script: `tools/trader/api.py`

## Usage Path

Read `tools/manual/stockbit.md` before using. It covers exodus/carina API layers, token refresh logic, and the full function reference.

## Safety Rules

- Tokens, cookies, and credentials are sensitive — never reveal in output.
- **Order execution (buy/sell/cancel/amend) requires explicit confirmation from Boss O before calling.**
- Always read back the order params (symbol, price, shares, side) and wait for "confirm" before placing.
- Never place orders speculatively or as part of analysis flow — only when explicitly instructed.
- Use minimum access needed. If Boss O has not authorized an action, stop and ask.

## Order Execution Flow

1. Boss O says: "buy X lot BBCA at 9000"
2. Read back: "Confirm: BUY BBCA 10 lot (1000 shares) @ Rp 9,000 RG day order?"
3. Wait for explicit "yes" / "confirm"
4. Call `api.place_buy_order(symbol, price, shares)`
5. Report back order_id and status

Never skip step 2-3.
