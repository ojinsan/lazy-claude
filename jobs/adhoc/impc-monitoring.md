# IMPC Monitoring

status: open
role: trader
created: 2026-04-02
owner: Claude
requested-by: Boss O

## Intent
Monitor IMPC tightly as an ad hoc trader task.
Do not move this into generic heartbeat market workflow unless Boss O explicitly asks.

## Current posture
- Boss O sold IMPC (+17% profit) and wants Claude to monitor for possible re-entry.
- Focus on whether thick offer walls are real distribution or fake fear/manipulation for accumulation.

## Mentor context (2026-04-02)
- SQ still doing buyback — creates persistent bid floor
- LG/KI/BK distributing — mixed tape, not clean breakout
- trapped sellers at 3400 — overhead supply
- buyback pace matters — if slow, continuation takes months
- See: `~/workspace/learn/trade/2026-04-02-mentor-broker-intent.md`

## What to watch
- whether thick offer wall refreshes repeatedly
- whether bids hold / step up underneath
- whether the wall gets absorbed
- whether price accepts above the scary area
- whether prints remain active or stall out

## Decision framing
### Re-entry becomes more valid if
- wall is absorbed or disappears
- price accepts above resistance
- bid support remains thick and stable
- tape confirms continuation rather than queue cosmetics

### Stay out / caution if
- wall keeps reloading
- price repeatedly rejects at same level
- bid support weakens after tests
- move stalls despite apparently strong queues

## Update style
Use ultra-short alerts when relevant:
- `IMPC not ready`
- `IMPC improving`
- `IMPC re-entry confirmed`

## Done condition
- Boss O says stop monitoring, or
- task is replaced by a newer IMPC-specific plan
