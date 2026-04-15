# Money Flow Analysis

## Purpose

Read whether capital is broadly flowing into the book or quietly leaving it.
Individual names can look fine while aggregate money flow is already deteriorating.

## What To Check

For each held ticker:
- smart-money participation
- foreign participation
- broker consistency over recent days
- whether flow still supports the thesis or only the last price move

Then aggregate across the portfolio:
- how many holds still show accumulation
- how many show mixed / unclear flow
- how many already show distribution

## Aggregate Read

Use a practical three-state model:

| State | Definition | Portfolio implication |
|-------|------------|-----------------------|
| Broad accumulation | Most holds still show smart-money support | normal to constructive posture |
| Mixed flow | Strong names exist, but the book is not aligned | selective only |
| Broad distribution | Flow deterioration across multiple holds | defensive posture |

## Contradiction Rules

Be careful when:
- one ticker has beautiful orderbook action but the rest of the book is weakening
- price is rising while smart money is no longer sponsoring the move
- retail participation is increasing across several names at once

When aggregate money flow contradicts a single-stock setup:
- keep size smaller
- require cleaner confirmation
- prefer adds to existing strong names over fresh speculative entries

## Foreign / Smart-Money Shortcut

A useful shortcut for Layer 0:
- count held names where foreign or smart-money brokers remain net supportive
- compare that with names where retail is increasingly dominant

If the supportive count is shrinking day by day, the portfolio is losing sponsorship.

## Output Standard

Always produce:
1. aggregate flow read — `accumulating`, `mixed`, or `distributing`
2. strongest supported hold
3. weakest sponsored hold
4. whether new capital should be added, held back, or rotated

## Example Prompts

- "Aggregate money flow across my current holds. Is the book still sponsored or already mixed?"
- "Which hold still has real smart-money support, and which one is now just floating on retail interest?"
- "If one ticker is strong but the rest are leaking sponsorship, how should that change sizing?"

## Tools To Call

- `tools/trader/api.py` → `get_broker_distribution()`
- `tools/trader/api.py` → `get_broker_info()`
- `tools/trader/api.py` → `get_portfolio()`
- `tools/trader/portfolio_health.py` → `compute_exposure_breakdown()`
- `skills/trader/broker-flow.md` for ambiguous broker reads

## Rule

Do not trust isolated strength when the rest of the portfolio is quietly losing sponsorship.
