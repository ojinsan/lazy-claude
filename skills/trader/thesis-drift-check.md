# Thesis Drift Check

## Purpose

Review a live hold against its original thesis and decide whether it is still valid, weakening, or broken.
This is a hold-management skill, not a hope-management skill.

## Use When

- a live position needs review in Layer 0
- a held name is lagging while the rest of the book is healthy
- Boss O asks whether the original thesis still stands
- monitoring suggests the stock behavior has changed materially

## Load First

- `skills/trader/thesis-evaluation.md`
- `skills/trader/orderbook-reading.md`
- `skills/trader/market-structure.md`
- `skills/trader/risk-rules.md`
- `skills/trader/journal-review.md`

## Workflow

1. Restate the original thesis and invalidation.
2. Pull current evidence:
   - price / structure
   - broker flow
   - SID trend
   - orderbook quality
   - volume confirmation
3. Re-check the 6 screening criteria by name.
4. Compare current state with planned holding horizon.
5. Return one action: `hold`, `watch`, `reduce`, or `exit-candidate`.

## Drift Labels

| Label | Meaning | Action |
|-------|---------|--------|
| Intact | Thesis still supported | hold |
| Weakening | Some supports fading, thesis not broken | watch or reduce |
| Broken | Invalidation hit or clear contradiction | exit-candidate |
| Needs refresh | Original thesis note missing or stale | review before adding |

## Evidence Rules

A thesis is weakening when one or more core supports are fading:
- narrative still exists, but broker sponsorship is fading
- structure still intact, but orderbook quality worsens repeatedly
- time horizon is stretching without progress

A thesis is broken when one of these is true:
- price breaks clear invalidation
- SID turns clearly distributive and broker flow confirms it
- the narrative driver is gone
- the stock remains in the book only because of attachment, not evidence

## Output Standard

Produce a concise drift note with:
1. original thesis
2. current evidence
3. drift label
4. recommended response
5. what must improve for the thesis to become constructive again

## Example Prompts

- "Check whether ANTM is still an intact hold or already a reduce candidate."
- "Restate the original thesis, compare it with current broker flow and structure, then give me the drift label."
- "This hold still has profit, but does the thesis still deserve the size?"

## Tools To Call

- `tools/trader/api.py` → `get_position_detail()`, `get_broker_distribution()`, `get_stockbit_orderbook()`
- `tools/trader/api.py` → `get_emitten_info()`
- `tools/trader/journal.py`
- `tools/trader/airtable_client.py`
- `vault/thesis/<TICKER>.md` when available

## Rule

Never protect a hold just because it is already in the portfolio. A stale thesis is still risk.
