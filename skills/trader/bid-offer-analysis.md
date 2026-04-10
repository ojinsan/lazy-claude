# Bid Offer Analysis

## Purpose

Read orderbook, bid-offer pressure, wall behavior, fake liquidity, and suspicious supply/demand changes around actionable names.

## Focus

- thick bid / thick offer behavior
- fake walls
- disappearing walls
- absorption
- pressure imbalance
- whether displayed liquidity is trustworthy

## Tool Resolution

Primary tools:
- `~/.claude/tools/trader/orderbook_poller.py`
- `~/.claude/tools/trader/orderbook_ws.py`
- `~/.claude/tools/trader/read_alerts.py`
- `~/.claude/tools/trader/api.py`

## Rule

A thick wall is not the conclusion. The conclusion comes from how the wall behaves: holds, gets absorbed, steps up, gets pulled, or repeatedly reappears.
