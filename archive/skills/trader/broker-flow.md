# Broker Flow

## Purpose

Read who is accumulating, distributing, or fading a move.

## Look For

- recurring broker names
- persistent buying or selling
- aggressive participation near key levels
- whether smart money appears early or late

## Questions

- is the move being sponsored or faded
- are the same names supporting follow-through
- does broker behavior confirm the public story

## Output

Summarize the flow in plain language:

- accumulation
- distribution
- mixed
- unclear
## Tools

- `~/workspace/tools/trader/broker_profile.py` — player intent: smart money vs retail, accumulation/distribution detection
- `~/workspace/tools/trader/running_trade_poller.py` — live tape / running trades
- `~/workspace/tools/trader/api.py` — broker flow data (`get_broker_flow`, `get_broker_summary`)

