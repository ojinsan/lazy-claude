# Trader Playbooks

Goal: beat IHSG, 50%+ annual return consistently.

## Before Any Layer — Load Philosophy First

Read `skills/trader/README.md` before starting any layer.
It contains the master index: philosophy, SID rules, broker classification, screening criteria, skills map, and tools map.
Do NOT skip it. It prevents logic errors (e.g. misreading SID direction).

## Layer Structure

| Layer | Playbook | When |
|-------|----------|------|
| 1 | `layer-1-global-context.md` | Pre-market / macro reset |
| 2 | `layer-2-stock-screening.md` | After L1 / pre-open refresh |
| 3 | `layer-3-stock-monitoring.md` | Market hours (cron-driven) |
| 4 | `layer-4-trade-plan.md` | Strong shortlist / Boss O request |

## How Layers Select Skills and Tools

Each layer playbook specifies:
- Which skills (MDs) to load — load only those, discard after
- Which Python scripts to run — import or subprocess as needed
- What output is required before proceeding to the next layer

The flow for each layer:
```
Layer playbook → loads specific skills → calls specific tools → produces output → posts to Airtable
```

## Airtable Tables

- `Insights` — raw and synthesized signals (macro, technical, broker, SID, narrative)
- `Superlist` — active execution watchlist (actionable names only, with status and trade fields)

## Code vs AI Rule

**Code** fetches and structures data. **Claude** reads, thinks, and decides.
No script should output conclusions, rankings, or buy/sell signals.
