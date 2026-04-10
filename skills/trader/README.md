# Trader Skills

These skills are the structured operating lenses for trader role.

## Core Skill POVs

- `technical-analysis.md` - price, volume, structure, and trend quality
- `bid-offer-analysis.md` - orderbook pressure, wall behavior, and fake liquidity
- `whale-retail-analysis.md` - broker flow, SID, and player behavior
- `fundamental-narrative-analysis.md` - story, macro, catalyst, and why it matters now
- `swing-trade-plan.md` - basic swing plan with clean risk framing
- `pro-orderbook-trade-plan.md` - execution-sensitive plan using orderbook and tape

## Existing Supporting Skills

- `airtable-trading.md`
- `broker-flow.md`
- `journal-review.md`
- `macro-context.md`
- `market-sentiment.md`
- `market-structure.md`
- `narrative-building.md`
- `orderbook-reading.md`
- `realtime-monitoring.md`
- `risk-rules.md`
- `sid-tracker.md`
- `stockbit-access.md`
- `thesis-evaluation.md`
- `trade-planning.md`
- `watchlist-4group.md`
- `wyckoff-lens.md`

Load only the skills the current job actually needs.

## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`
