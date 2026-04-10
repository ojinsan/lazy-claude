# Superlist Screening

## Use When

- before market open
- before deep-dive analysis
- when Airtable `Superlist` needs to be cleaned or refreshed

## Load First

- `~/workspace/roles/trader.md`
- `~/.claude/skills/trader/airtable-trading.md`
- `~/.claude/skills/trader/trade-planning.md`
- `~/.claude/skills/trader/technical-analysis.md`

## Workflow

1. Pull current Airtable `Superlist` rows.
2. Check whether status, duration, and trade-facing fields are still valid.
3. Remove or downgrade names that no longer have edge.
4. Flag which names require fresh deep-dive analysis.

## Deliverable

Produce a refreshed execution-facing list with:
- ticker
- current status
- urgency
- what still needs confirmation

## Safety

- Keep the list clean.
- Do not preserve names out of habit if the edge is gone.


## Layer alignment

Layer 4 trade-plan support job focused on reviewing high-conviction names already promoted into Airtable Superlist.
