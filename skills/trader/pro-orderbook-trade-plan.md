# Pro Orderbook Trade Plan

## Purpose

Upgrade a standard trade plan with orderbook and running-trade logic for execution-sensitive setups.

## Focus

- thick walls that matter
- fake walls
- disappearing supply
- absorption quality
- short-window transaction behavior
- whether displayed liquidity supports execution or is likely bait

## Tool Resolution

Primary tools:
- `~/workspace/tools/trader/tradeplan.py`
- `~/workspace/tools/trader/orderbook_poller.py`
- `~/workspace/tools/trader/orderbook_ws.py`
- `~/workspace/tools/trader/running_trade_poller.py`
- `~/workspace/tools/trader/api.py`

## Rule

Only call it a pro orderbook setup when the microstructure actually changes the execution decision.
