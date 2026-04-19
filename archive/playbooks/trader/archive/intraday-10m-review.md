# Intraday 10-Minute Review

## Use When

- during trading hours on active monitoring days
- after orderbook and running-trade listeners have gathered short-window data

## Load First

- `~/workspace/roles/trader.md`
- `~/.claude/skills/trader/realtime-monitoring.md`
- `~/.claude/skills/trader/bid-offer-analysis.md`
- `~/.claude/skills/trader/whale-retail-analysis.md`

## Workflow

1. Pull the latest 10-minute window from orderbook and running-trade monitoring.
2. Identify what changed: pressure, wall behavior, tape shifts, fake liquidity, absorption, or sudden aggression.
3. Summarize what happened in plain trading language.
4. Store the short-window insight into local storage for later heartbeat review.

## Deliverable

Produce a 10-minute microstructure note with:
- what happened
- who seemed to be in control
- whether it strengthens or weakens the current plan

## Safety

- Distinguish observation from conclusion.
- If the window is noisy, say `no edge`.


## Layer alignment

Layer 3 stock-overseeing support job for 10-minute microstructure review.
