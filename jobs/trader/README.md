# Trader Jobs — 4-Layer OS

Goal: beat IHSG, 50%+ annual return consistently.

## Structure

| Layer | Job | When |
|-------|-----|------|
| 1 | `layer-1-global-context.md` | Pre-market / macro reset |
| 2 | `layer-2-stock-screening.md` | After L1 / pre-open refresh |
| 3 | `layer-3-stock-monitoring.md` | Market hours (cron-driven) |
| 4 | `layer-4-trade-plan.md` | Strong shortlist / Boss O request |

## Airtable Tables

- `Insights` — context, screening, and monitoring signals
- `Superlist` — high-conviction names with active trade focus

## Skills Reference

`~/.claude/skills/trader/` — load only what each layer specifies.

## Code vs AI Rule

**Code** fetches and structures data. **Claude** reads, thinks, and decides.
No script should output conclusions, rankings, or buy/sell signals.
