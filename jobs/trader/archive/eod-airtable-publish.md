# EOD Airtable Publish

## Use When

- after market close
- when local monitoring and analysis notes should be preserved in Airtable `Insights`

## Load First

- `~/workspace/roles/trader.md`
- `~/.claude/skills/trader/airtable-trading.md`
- `~/.claude/skills/trader/journal-review.md`
- `~/.claude/skills/trader/thesis-evaluation.md`

## Workflow

1. Review local intraday notes and heartbeat summaries.
2. Select only the genuinely interesting observations.
3. Convert them into clean Airtable `Insights` rows.
4. Link them to `Superlist` names if relevant.

## Deliverable

Publish selected end-of-day insights with:
- ticker
- confidence
- observation summary
- why it mattered
- what to watch next

## Safety

- Do not spam Airtable with repetitive noise.
- Write only what is worth remembering.
