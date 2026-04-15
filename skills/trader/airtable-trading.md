# Airtable Trading

Trading Airtable now supports:
- paginated `list-all`
- `bulk-delete`
- `bulk-create`
- `upsert`
- `cleanup` with keep-latest / keep-filter behavior


## Purpose

Use Airtable as the operating store for trading insights and the active execution watchlist.

## Tables

### `Insights`
Store raw and synthesized observations such as:
- fundamental
- narrative
- technical
- whale or broker flow
- orderbook / bid-offer
- running trade / transaction
- macro
- catalyst or event follow-up

Current fields:
- `Name`
- `Ticker`
- `Status` (`Low Confidence`, `Outdated`, `High Confidence`)
- `Content`
- `Attachment Summary`
- `Superlist`

### `Superlist`
Store the active execution-facing watchlist.

Current fields:
- `Ticker`
- `Content`
- `Status` (`Failed`, `Cutloss`, `Waiting for Entry`, `Entry Now`, `Hold`, `Take Profit`)
- `Insight Links`
- `Ticker (from Insight Links)`
- `Buy Price`
- `Target Price`
- `Buy Value`
- `Duration` (`Daily`, `1 Month`, `3 Month`, `1 Year`)

## Workflow

1. Put observations and analysis into `Insights`.
2. Promote only actionable names into `Superlist`.
3. When adding to `Superlist`, prefer filling the trade-facing fields if known: `Status`, `Buy Price`, `Target Price`, `Buy Value`, and `Duration`.
4. Link `Superlist` rows back to the relevant `Insights` rows through `Insight Links`.
5. Keep `Superlist` clean, active, and execution-focused.

## Rules

- Do not treat `Superlist` as a raw note dump.
- Use exact Airtable single-select values; do not invent new ones.
- If a field is unknown, leave it blank rather than guessing.
- Use `Attachment Summary` only as a derived/reference field, not as a primary manual note field.

## Tool Resolution

Use Airtable helpers from:

- `~/workspace/tools/trader/airtable_client.py`
