# Portfolio Self-Review

## Purpose

Force an honest daily review of portfolio decisions, not just per-trade emotions.
Layer 0 should end with what worked, what failed, and what should change tomorrow.

## Daily Questions

Every review should answer:
1. Which portfolio calls worked today?
2. Which calls were wrong or late?
3. Was the mistake thesis, timing, sizing, concentration, or psychology?
4. Did I add risk when the book was not healthy enough?
5. What one rule should be tighter tomorrow?

## Review Structure

Write the note in this order:

### 1. What happened
- equity move
- biggest winner / loser
- concentration changes
- whether the book got healthier or weaker

### 2. What was expected
- the main Layer 0 posture going into the day
- key sector/theme expectations
- expected adds, reductions, or exits

### 3. What was missed
- unexpected rotation
- missed invalidation
- overconfidence in old thesis
- concentration that should have been reduced earlier

### 4. What changes tomorrow
- one process fix
- one risk posture adjustment
- one watch item for the next Layer 0 run

## Categorize the Mistake

Use one of these when logging a lesson:
- `entry_timing`
- `exit_timing`
- `thesis_quality`
- `sizing`
- `psychology`
- `missed_trade`
- `portfolio`

## Severity Guide

- `low` — small process miss, low cost
- `medium` — repeated sloppiness or noticeable P&L drag
- `high` — clear avoidable loss, concentration damage, or thesis blindness

## Output Standard

Every Layer 0 self-review should produce:
1. one-paragraph day summary
2. 1–3 lessons
3. one concrete change for tomorrow
4. an explicit label: `improving`, `flat`, or `deteriorating`

## Example Prompts

- "Write today's Layer 0 self-review. Focus on whether the book got healthier or just busier."
- "What did I miss yesterday that a stricter portfolio lens would have caught?"
- "Was today's problem stock selection, or portfolio construction?"

## Tools To Call

- `tools/trader/journal.py` → `write_journal()`, `log_lesson()`
- `tools/trader/portfolio_health.py` → `compute_portfolio_state()`
- `tools/trader/api.py` → `get_portfolio()`

## Rule

The review is not there to defend prior decisions. It exists to tighten tomorrow's process.
