# Whale Retail Analysis

## Purpose

Read broker flow, SID, running trade, and player behavior to judge whether a move is being driven by stronger hands, crowded retail, or mixed participation.

## Focus

- smart money vs retail behavior
- broker consistency
- accumulation / distribution
- SID drift
- running-trade participation style
- hidden weakness behind visible strength

## Tool Resolution

Primary tools:
- `~/.claude/tools/trader/broker_profile.py`
- `~/.claude/tools/trader/sid_tracker.py`
- `~/.claude/tools/trader/running_trade_poller.py`
- `~/.claude/tools/trader/api.py`

## Rule

Do not use whale language loosely. Distinguish actual evidence of strong-hand behavior from ordinary turnover and retail excitement.
