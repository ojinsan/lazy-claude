# Portfolio Management

## Purpose

Manage the book as a hedge-fund operator first, stock picker second.
The first question every morning is not "what can I buy?" — it is "is the portfolio healthy enough to add risk?"

## Hard Limits

| Check | Normal rule | Action if breached |
|------|-------------|--------------------|
| Single position | Max 20% of total equity | Reduce or stop adding |
| Sector exposure | Max 50% of total equity | Rebalance / avoid same-theme adds |
| Total deployed exposure | Max 80% of total equity | Keep cash buffer, stop forcing entries |
| Drawdown | >5% from HWM | Cut planned new exposure by 25% |
| Drawdown | >10% from HWM | Halt new entries until posture improves |

## Morning Sequence

1. Call `portfolio_health.compute_portfolio_state()`.
2. Review drawdown, utilization, top concentration, and exposure by sector.
3. Re-rate every active hold as `intact`, `watch`, `reduce`, or `exit-candidate`.
4. Only after that decide whether Layer 1 and Layer 2 should hunt new risk.

## Position Sizing Bias

Use the portfolio state to bias, not replace, per-trade sizing:
- Healthy book, DD ≤ 3%, exposure < 60% → normal sizing allowed
- DD 3–5% or exposure 60–80% → keep new risk smaller
- DD > 5% → size down automatically even if the setup looks good
- DD > 10% → no new entries; focus on repair and select exits

## Rebalance Triggers

Rebalance or reduce when any of these is true:
- a single name is >20% of equity
- a single theme or sector is >50% of equity
- 2 or more large positions are tightly correlated
- the book is still concentrated in yesterday's theme while Layer 1 already rotated away
- old winners remain large but thesis quality is weakening

## Concentration Rules

Concentration is acceptable only when both are true:
- the position still matches current narrative and flow
- the rest of the book is not already exposed to the same driver

Never justify concentration with P&L alone. A profitable oversized position is still oversized.

## Action Labels

Every morning Layer 0 should leave each hold with one action label:
- `hold` — thesis intact, no size change needed
- `add-to` — thesis intact and underweight relative to confidence
- `reduce` — still valid, but concentration or drift is too high
- `exit-candidate` — invalidation or clear thesis break risk

## Output Standard

Always produce:
1. portfolio health card
2. concentration flags
3. action list by ticker
4. one-line portfolio posture: `press`, `balanced`, or `defensive`

## Example Prompts

- "Run Layer 0. Tell me if the portfolio is healthy enough to add two new names today."
- "Which hold is overweight relative to its current thesis quality?"
- "If drawdown is 6.2%, how much should I cut planned new exposure?"

## Tools To Call

- `tools/trader/portfolio_health.py` → `compute_portfolio_state()`, `compute_concentration_flags()`
- `tools/trader/api.py` → `get_portfolio()`, `get_cash_info()`, `get_position_detail()`
- `tools/trader/api.py` → `get_emitten_info()` for sector mapping
- `tools/trader/journal.py` → `review_trades()` for recent hit-rate context

## Rule

Do not let a strong single-stock story hide a weak portfolio. Portfolio health has veto power over aggressive new risk.
