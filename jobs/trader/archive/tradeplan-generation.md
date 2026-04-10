# Tradeplan Generation

## Use When

- after deep-dive analysis
- when Boss O wants a basic swing plan or a more advanced execution plan
- when a Superlist name looks close to actionable

## Load First

- `~/workspace/roles/trader.md`
- `~/.claude/skills/trader/trade-planning.md`
- `~/.claude/skills/trader/technical-analysis.md`
- `~/.claude/skills/trader/bid-offer-analysis.md`
- `~/.claude/skills/trader/whale-retail-analysis.md`

## Workflow

1. Decide whether the setup is a basic swing plan or a pro orderbook-sensitive plan.
2. Build entry, invalidation, target, and size logic.
3. If orderbook/tape is relevant, check for suspicious thick offer walls, fake walls, or disappearing supply.
4. Write the resulting plan back into local notes and, if appropriate, into Airtable `Superlist` fields.

## Deliverable

Produce a trade plan with:
- setup type
- entry/trigger
- invalidation
- target / reduce zone
- size logic
- execution warnings

## Safety

- No plan without risk.
- If the tape is suspicious, say so clearly.


## Layer alignment

Layer 4 trade-plan execution job for converting high-conviction names into actionable plans.
