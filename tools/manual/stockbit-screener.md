# Connector: Stockbit Screener

Type: REST API
Primary domain: `https://exodus.stockbit.com/screener`
Scripts:
- `tools/trader/sb_screener_create.py`
- `tools/trader/sb_screener_hapcu_foreign_flow.py`
- low-level auth + HTTP helper: `tools/trader/api.py`

## Purpose

Build, run, inspect, and save Stockbit screener templates from verified API calls.
Use this manual when task is specifically about Stockbit Screener endpoints, payload shapes, or rule construction.

## Verified Live Endpoints

Browser-verified calls from `https://stockbit.com/screener`:

- `GET /screener/templates`
- `GET /screener/favorites`
- `GET /screener/universe`
- `GET /screener/preset`
- `GET /screener/metric`
- `GET /screener/templates/{id}?type=TEMPLATE_TYPE_GURU|TEMPLATE_TYPE_CUSTOM`
- `POST /screener/templates`

Base URL:
```text
https://exodus.stockbit.com
```

## Auth

Uses the normal Stockbit bearer token flow from `tools/trader/api.py`.

Primary login helper:
```bash
python3 tools/trader/stockbit_login.py --force
```

If token is valid, screener calls work through:
- `api._stockbit_get(...)`
- `api._stockbit_post(...)`

## Endpoint Map

### List saved templates
```text
GET /screener/templates
```

### List favorites
```text
GET /screener/favorites
```

### List universes
```text
GET /screener/universe
```

### List presets
```text
GET /screener/preset
```

### List all metrics
```text
GET /screener/metric
```

### Load one template/preset
```text
GET /screener/templates/{id}?type=TEMPLATE_TYPE_CUSTOM
GET /screener/templates/{id}?type=TEMPLATE_TYPE_GURU
```

### Run or save screener
```text
POST /screener/templates
```

`save="0"` = run only
`save="1"` = save template

## Payload Shape

Verified payload shape used by Stockbit web UI:

```json
{
  "name": "My Screener",
  "description": "",
  "save": "0",
  "ordertype": "asc",
  "ordercol": 2,
  "page": 1,
  "universe": "{\"scope\":\"IHSG\",\"scopeID\":\"\",\"name\":\"\"}",
  "filters": "[{...}]",
  "sequence": "12148,3194,13539",
  "screenerid": "0",
  "type": "TEMPLATE_TYPE_CUSTOM"
}
```

Notes:
- `universe` is JSON-encoded string, not nested object.
- `filters` is JSON-encoded string, not nested array.
- `sequence` is comma-separated unique metric IDs in rule order.
- `screenerid="0"` for new screener.

## Rule Shapes

### Basic rule
Compare metric vs constant.

```json
{
  "type": "basic",
  "item1": 12148,
  "item1name": "Current PE Ratio (Annualised)",
  "operator": "<",
  "item2": "40",
  "multiplier": ""
}
```

### Compare rule
Compare metric vs multiplier × metric.

```json
{
  "type": "compare",
  "item1": 3218,
  "item1name": "Foreign Flow",
  "operator": ">",
  "multiplier": "1",
  "item2": 13521,
  "item2name": "Foreign Flow MA 20"
}
```

Operators seen in UI:
- `>`
- `<`
- `<=`
- `=`
- `>=`

## Generic Helper

Script:
```text
tools/trader/sb_screener_create.py
```

### Supported commands

```bash
python3 tools/trader/sb_screener_create.py templates
python3 tools/trader/sb_screener_create.py favorites
python3 tools/trader/sb_screener_create.py universe
python3 tools/trader/sb_screener_create.py preset
python3 tools/trader/sb_screener_create.py metrics
python3 tools/trader/sb_screener_create.py metrics --search foreign
python3 tools/trader/sb_screener_create.py get-template --id 6 --type TEMPLATE_TYPE_GURU
python3 tools/trader/sb_screener_create.py payload --filters-file /tmp/filters.json --name "My Screener"
python3 tools/trader/sb_screener_create.py run --filters-file /tmp/filters.json --name "My Screener"
python3 tools/trader/sb_screener_create.py run --filters-file /tmp/filters.json --name "My Screener" --save
```

### Filter file example

```json
[
  {
    "type": "basic",
    "item1": 12148,
    "item1name": "Current PE Ratio (Annualised)",
    "operator": "<",
    "item2": "40",
    "multiplier": ""
  },
  {
    "type": "compare",
    "item1": 3218,
    "item1name": "Foreign Flow",
    "operator": ">",
    "multiplier": "1",
    "item2": 13521,
    "item2name": "Foreign Flow MA 20"
  }
]
```

## Example Screener Script

Script:
```text
tools/trader/sb_screener_hapcu_foreign_flow.py
```

Run examples:
```bash
python3 tools/trader/sb_screener_hapcu_foreign_flow.py
python3 tools/trader/sb_screener_hapcu_foreign_flow.py --save
python3 tools/trader/sb_screener_hapcu_foreign_flow.py --payload
```

Saved template:
- name: `Hapcu Foreign Flow`
- screenerid: `6402892`

Rules encoded:
- `Current PE Ratio (Annualised) < 40`
- `Net Foreign Buy / Sell > 1,000,000,000`
- `Net Foreign Buy / Sell MA10 > 1,000,000,000`
- `Net Foreign Buy Streak >= 2`
- `Foreign Flow > 1 x Foreign Flow MA 20`
- `Net Foreign Buy Streak > 2 x Net Foreign Sell Streak`
- `1 Day Volume Change > 1`
- `Near 52 Week High > 0.7`

## Known Metric IDs Used

| Metric | fitem_id |
|---|---:|
| Current PE Ratio (Annualised) | 12148 |
| Net Foreign Buy / Sell | 3194 |
| Net Foreign Buy / Sell MA10 | 13539 |
| Net Foreign Buy Streak | 13561 |
| Net Foreign Sell Streak | 13562 |
| Foreign Flow | 3218 |
| Foreign Flow MA 20 | 13521 |
| 1 Day Volume Change | 13650 |
| Near 52 Week High | 13412 |

## Failure Mode Seen

If UI sends empty/invalid metric selection, API can return:

```json
{"message":"Item Metrics Not Found","error_type":"NOT_FOUND"}
```

Cause:
- `item1` missing/null
- invalid filter structure
- empty `basic` rule posted

## Safety Rules

- Do not print bearer tokens or credentials.
- Use `--save` only when Boss O wants template persisted.
- Order/broker APIs live elsewhere; this manual is screener-only.
