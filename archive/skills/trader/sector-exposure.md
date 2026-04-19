# Sector Exposure

## Purpose

Translate individual holdings into theme-level risk so the book does not unknowingly become one big bet.

## Theme Buckets

Map Stockbit sectors into Boss O's working buckets:

| Bucket | Typical sectors / labels |
|--------|---------------------------|
| Energy | coal, oil & gas, energy, utilities linked to energy |
| Banking | bank, financials, large-cap lenders |
| Property | property, real estate, construction when rate-driven |
| Nickel-EV | metals, mining, nickel, EV supply chain |
| Consumer | staples, discretionary, retail, domestic demand |
| Other | anything that does not fit the main buckets |

If a company sits between buckets, map it by the driver of the thesis, not the prettiest label.

## Exposure Rules

| Condition | Read | Action |
|-----------|------|--------|
| 0–25% in one bucket | normal | no issue |
| 25–35% in one bucket | warm | stay selective |
| 35–50% in one bucket | crowded | only add if conviction is exceptional |
| >50% in one bucket | overexposed | reduce or block same-theme adds |

## Rotation Logic

Sector rotation matters more than attachment to old winners.

Reduce same-bucket aggression when:
- Layer 1 narrative has already shifted away
- foreign / smart-money flow is fading across the bucket
- two or more holdings in the bucket are showing thesis drift together
- the bucket is carrying the whole book's P&L and risk

## Correlation Shortcut

Use a simple practical correlation read when formal correlation is unavailable:
- same bucket
- same broker flow direction
- same narrative driver

If all three line up, assume they are correlated enough to deserve portfolio-level caution.

## Orphan Hold Rule

A hold is orphaned when:
- it is still in the book
- but it no longer belongs to any active Layer 1 theme
- and the thesis note cannot justify an independent reason to stay

Orphan holds move to `watch` or `reduce`, not automatic `hold`.

## Output Standard

Layer 0 should always return:
- exposure by bucket
- top crowded bucket
- orphan holds
- whether new risk should rotate into another bucket instead

## Example Prompts

- "Map my current holds into theme buckets and tell me where the book is crowded."
- "Do I still have a valid Nickel-EV cluster, or is it now just legacy exposure?"
- "Which bucket should get new capital if I want to diversify without going fully defensive?"

## Tools To Call

- `tools/trader/portfolio_health.py` → `compute_exposure_breakdown()`
- `tools/trader/api.py` → `get_emitten_info()`
- `tools/trader/api.py` → `get_portfolio()`
- `playbooks/trader/layer-1-global-context.md` output for active themes

## Rule

Do not describe the book as diversified if multiple names are really the same macro bet wearing different tickers.
