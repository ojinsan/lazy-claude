# Realtime Monitoring

## Purpose

Track incoming alerts and live changes without letting noise dominate the workflow.

## Sources

- alert queue
- realtime listener
- monitor loop
- read-alerts output
- live orderbook or running trade signals

## Priority Labels

- high
- medium
- low
- noise

## High Priority Examples

- stop loss trigger
- emergency cut
- target or reduce level hit
- breakout confirmed with meaningful follow-through

## Rule

Monitoring exists to surface changes, not to replace judgment.
## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`

