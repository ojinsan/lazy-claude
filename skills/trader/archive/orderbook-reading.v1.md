# Orderbook Reading

## Purpose

Read bid-offer pressure, absorption, and urgency without pretending the book is perfect truth.

## Focus

- bid stack quality
- offer pressure
- absorption at key levels
- crossing behavior
- signs of manipulation or spoofing

## Interpretation

- strong accumulation
- supply overhead
- absorption
- trap risk
- no clean read

## Output

Explain:

- what the book suggests
- how confident that read is
- what price behavior would confirm it
## Tools

- `~/workspace/tools/trader/orderbook_poller.py` — live orderbook polling loop
- `~/workspace/tools/trader/orderbook_ws.py` — WebSocket orderbook stream
- `~/workspace/tools/trader/tick_walls.py` — wall detection and analysis
- `~/workspace/tools/trader/api.py` — snapshot orderbook data (`get_orderbook`)

