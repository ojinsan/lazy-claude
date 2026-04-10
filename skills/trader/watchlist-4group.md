# Watchlist 4-Group

## Purpose

Maintain the 4-group watchlist as the default starting universe.

## The Four Groups

- local tracked names
- API backend watchlist
- RAG or search-discovered names
- stocklist or market-attractive names

## Method

1. Pull each group separately.
2. Merge and de-duplicate.
3. Tag each ticker with its source group.
4. Keep only names that still have a valid reason to stay.

## Output

For each kept ticker, record:

- source group
- why it matters
- urgency

## Rule

If a ticker is not justified, remove it. A shorter watchlist is better than a noisy one.
## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`

