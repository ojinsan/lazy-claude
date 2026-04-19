# Alert Triage

## Use When

- an alert queue exists
- realtime monitoring produces a notable signal
- Boss O asks for a fast read on urgency

## Load First

- `skills/trader/CLAUDE.md`
- `~/.claude/skills/trader/realtime-monitoring.md`
- `~/.claude/skills/trader/risk-rules.md`
- `~/.claude/skills/trader/trade-planning.md`

## Workflow

1. Classify the alert as `high`, `medium`, `low`, or `noise`.
2. Check whether the alert matches the existing thesis or breaks it.
3. Reduce the alert into one action-oriented sentence.
4. If needed, prepare a short escalation draft for Boss O.

## High Priority Examples

- stop loss trigger
- emergency cut
- breakout confirmed with meaningful volume
- target or reduce level hit

## Deliverable

Produce a triage note with:

- priority
- what changed
- why it matters
- proposed next action

## Safety

- Never send the alert without permission.
- Never turn an alert into an automatic order.
