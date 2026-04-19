# Stockbit Screener

## Purpose

Build, run, and save Stockbit screener templates from verified Stockbit screener API endpoints.

## Primary Tooling

- Manual: `tools/manual/stockbit.md`
- API helper: `tools/trader/sb_screener_create.py`
- Example screener: `tools/trader/sb_screener_hapcu_foreign_flow.py`

## Verified API Endpoints

- `GET https://exodus.stockbit.com/screener/templates`
- `GET https://exodus.stockbit.com/screener/favorites`
- `GET https://exodus.stockbit.com/screener/universe`
- `GET https://exodus.stockbit.com/screener/preset`
- `GET https://exodus.stockbit.com/screener/metric`
- `GET https://exodus.stockbit.com/screener/templates/{id}?type=TEMPLATE_TYPE_GURU|TEMPLATE_TYPE_CUSTOM`
- `POST https://exodus.stockbit.com/screener/templates`

## Rule Shapes

Basic ratio:
```python
{
  "type": "basic",
  "item1": 12148,
  "item1name": "Current PE Ratio (Annualised)",
  "operator": "<",
  "item2": "40",
  "multiplier": "",
}
```

Ratio vs ratio:
```python
{
  "type": "compare",
  "item1": 3218,
  "item1name": "Foreign Flow",
  "operator": ">",
  "multiplier": "1",
  "item2": 13521,
  "item2name": "Foreign Flow MA 20",
}
```

## Run examples

```bash
python3 tools/trader/sb_screener_hapcu_foreign_flow.py
python3 tools/trader/sb_screener_hapcu_foreign_flow.py --save
python3 tools/trader/sb_screener_hapcu_foreign_flow.py --payload
```

## Generic helper examples

```bash
python3 tools/trader/sb_screener_create.py metrics --search foreign
python3 tools/trader/sb_screener_create.py templates
python3 tools/trader/sb_screener_create.py get-template --id 6 --type TEMPLATE_TYPE_GURU
python3 tools/trader/sb_screener_create.py payload --filters-file /tmp/filters.json --name "My Screener"
python3 tools/trader/sb_screener_create.py run --filters-file /tmp/filters.json --name "My Screener"
python3 tools/trader/sb_screener_create.py run --filters-file /tmp/filters.json --name "My Screener" --save
```

## Notes

- Read `tools/manual/stockbit.md` first for auth flow.
- Use `--save` only when Boss O explicitly wants template persisted.
- `sequence` should include unique metric IDs used in the filter set, in rule order.
