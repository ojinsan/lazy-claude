# Realtime Monitoring

## Purpose

Track incoming alerts and live changes without letting noise dominate the workflow.

## Sources

- alert queue
- realtime listener
- monitor loop
- read-alerts output
- live orderbook or running trade signals

## Priority Labels

- high
- medium
- low
- noise

## High Priority Examples

- stop loss trigger
- emergency cut
- target or reduce level hit
- breakout confirmed with meaningful follow-through

## Rule

Monitoring exists to surface changes, not to replace judgment.
## Tools

- `~/workspace/tools/trader/realtime_listener.py` — running trade patterns + orderbook deltas
- `~/workspace/tools/trader/runtime_monitoring.py` — periodic L3 monitoring loop (cron-driven)
- `~/workspace/tools/trader/orderbook_poller.py` — live orderbook polling loop
- `~/workspace/tools/trader/running_trade_poller.py` — live tape / running trades
- `~/workspace/tools/trader/api.py` — price, orderbook, position data

