# Market Sentiment

## Purpose

Decide what kind of tape Scarlett is dealing with before diving into ticker detail.

## Read

- index behavior
- sector rotation
- news or catalyst tone
- liquidity appetite
- whether moves are broad or isolated

## Labels

- risk-on
- risk-off
- rotational
- choppy
- headline-driven

## Output

State:

- the tone
- what supports it
- what could invalidate it

Do not oversell weak evidence.
## Tools

- `~/workspace/tools/trader/api.py` — index OHLCV, foreign flow, market stats
- `~/workspace/tools/trader/narrative.py` — sentiment narrative generation
- `~/workspace/tools/general/browser/web_browse.py` — news tone and catalyst scanning

