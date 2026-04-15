# Probability Measurement

## Purpose

Use recent trading results to decide whether current sizing should stay normal, scale up, or scale down.
Do not confuse recent confidence with measured edge.

## Core Metrics

Start with the last 30 closed trades when available.

- **Win rate** = wins / closed trades
- **Average win** = mean P&L of winners
- **Average loss** = mean P&L of losers
- **Expectancy** = `(win_rate × avg_win) + ((1 - win_rate) × avg_loss)`
- **Risk-reward** = `avg_win / abs(avg_loss)`

If sample size is small:
- <10 closed trades → low confidence, no sizing up
- 10–20 trades → useful but still cautious
- 20+ trades → fair short-horizon operating read

## Sizing Bias Rules

| 30d read | Meaning | Action |
|----------|---------|--------|
| Win rate < 40% or expectancy < 0 | edge is weak | size down |
| Win rate 40–55% and expectancy > 0 | edge is usable | normal size |
| Win rate > 55% and risk-reward > 1.5 | edge is healthy | selective size-up allowed |

Never size up just because one ticker looks good. Size up only when both the setup and the recent process stats agree.

## Kelly Fraction (Capped)

Use Kelly only as a ceiling, not as the actual bet size.

`kelly = win_rate - ((1 - win_rate) / risk_reward)`

Apply these caps:
- if Kelly ≤ 0 → no size-up
- use at most 25% of Kelly in practice
- hard cap portfolio-level risk by existing portfolio rules anyway

## Drawdown Override

Recent stats do not override drawdown controls.

If portfolio drawdown > 5%:
- reduce planned new exposure even if the stats look strong

If portfolio drawdown > 10%:
- no new entries, regardless of Kelly or hit rate

## Output Standard

Return:
1. sample size
2. win rate
3. avg win / avg loss
4. expectancy read: `positive`, `flat`, or `negative`
5. current sizing bias: `size down`, `normal`, or `selective size-up`

## Example Prompts

- "Use the last 30 closed trades to tell me if current sizing should be normal or defensive."
- "Estimate the capped Kelly fraction from recent results, then tell me the practical implication."
- "If win rate is improving but drawdown is still 6%, what wins: the stats or the drawdown rule?"

## Tools To Call

- `tools/trader/journal.py` → `review_trades(days=30)`
- `tools/trader/portfolio_health.py` → `compute_portfolio_state()`
- `skills/trader/risk-rules.md` for the final cap on real sizing

## Rule

Probability is there to keep sizing honest. It is not a license to force risk when the book is already damaged.
