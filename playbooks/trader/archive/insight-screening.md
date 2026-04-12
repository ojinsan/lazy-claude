# Insight Screening

## Use When

- before market open
- when Airtable `Insights` has fresh entries to review
- when Boss O wants the strongest fresh evidence surfaced first

## Load First

- `~/workspace/roles/trader.md`
- `~/.claude/skills/trader/airtable-trading.md`
- `~/.claude/skills/trader/fundamental-narrative-analysis.md`
- `~/.claude/skills/trader/technical-analysis.md`
- `~/.claude/skills/trader/whale-retail-analysis.md`

## Workflow

1. Pull newly created or recently updated Airtable `Insights` rows.
2. Classify each row by POV: fundamental, narrative, technical, whale/retail, bid-offer, transaction, macro.
3. Separate high-signal rows from stale or weak rows.
4. Mark what deserves promotion into deeper analysis.
5. Record the strongest findings into local daily storage.

## Deliverable

Produce a concise screening note with:
- strongest fresh insights
- tickers that deserve follow-up
- stale or downgraded ideas
- missing evidence that blocks conviction

## Safety

- Do not invent confidence levels.
- If an Airtable field is unclear, inspect the actual schema before writing.


## Layer alignment

This job is now primarily a Layer 2 stock-screening support job. Use it to screen new and updated Airtable insights after Layer 1 has set the context.
