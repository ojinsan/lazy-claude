# Whale Retail Analysis

## Purpose

Read broker flow, SID, running trade, and player behavior to judge whether a move is being driven
by stronger hands, crowded retail, or a distribution trap. Protect Boss O from retail FOMO setups.

## Smart Money vs Retail

```
Smart money:  AK, ZP, BK, YU, HP, RX, AI, ES, HD, MS, CS, DB, MG, SS, RF, BP
Foreign:      BK, MS, CS, DB, MG, RX, YU, CG, ML
Retail:       XL, XC, YP, CC, KK, PD, SQ, NI, AZ, CP
```

## Key Patterns to Identify

| Pattern | Verdict |
|---------|---------|
| Smart money consistent buyer, SID decreasing | Accumulation — operator is loading |
| Retail dominant buyer, smart money absent or selling | Distribution trap — do not enter |
| Same smart money broker across multiple days | Committed accumulation |
| Smart money tektok (buy+sell same broker) | Market making, not directional |
| Retail FOMO + smart money exits | Late distribution — dangerous, exit if holding |
| Smart money avg cost underwater + still buying | High conviction accumulation |

## SID Rule (Never Get This Wrong)

- SID DECREASING = accumulation = bullish
- SID INCREASING = distribution = bearish

Do not interpret SID increase as "more people interested." It means retail is absorbing supply.

## Broker Consistency Check

Look at `buy_days` and `sell_days` from `api.get_broker_distribution()`:
- High buy_days, low sell_days = committed accumulator
- Equal buy/sell days = tektok / market maker
- High sell_days = distribution in progress

## Trap Detection

A trap is: retail buying aggressively (XL, YP, CC high buy days) while smart money has
high sell_days. Price may still be rising — this is the exit window for smart money.
Entering here = buying from the operator.

## Output

State:
- Who is the dominant player and their intent
- Whether smart money is accumulating, distributing, or absent
- Whether retail is late/FOMO
- Trap detected? Yes/No + evidence
- One-line verdict: sponsored / distributed / unclear

## Tools

- `tools/trader/broker_profile.py` → full player analysis with intent, trap detection, P&L
- `tools/trader/sid_tracker.py` → SID accumulation/distribution signal
- `tools/trader/running_trade_poller.py` → live tape participation style
- `tools/trader/api.py` → `get_broker_distribution()`, `get_stockbit_sid_count()`

## Rule

Do not use whale language loosely. "Smart money buying" requires evidence of consistent
high buy_days from known smart money codes. A single day means nothing.
