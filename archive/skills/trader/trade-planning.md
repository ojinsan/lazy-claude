# Trade Planning

## Purpose

Translate analysis into a structured plan Boss O can act on.

## Every Plan Must Include

- setup type
- entry or trigger
- invalidation
- target or reduce area
- position-sizing logic
- what to do if price does not confirm

## Rule

No plan is complete without risk. Entry without invalidation is not a plan.
## Tools

- `~/workspace/tools/trader/tradeplan.py` — trade plan generator (entry, SL, targets, sizing)
- `~/workspace/tools/trader/market_structure.py` — key levels and invalidation points
- `~/workspace/tools/trader/indicators.py` — ATR for stop sizing, RSI/EMA for entry context
- `~/workspace/tools/trader/api.py` — live price and cash info for sizing calculations
- `~/workspace/tools/trader/telegram_client.py` — send L4 trade plan alert (`layer4` template)

