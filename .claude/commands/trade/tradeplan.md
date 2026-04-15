---
name: trade:tradeplan
description: Pre-market trade plan generation — Layer 4. Reads L2 shortlist and builds actionable plans before market opens. Runs at 06:00 WIB non-interactively.
disable-model-invocation: true
---

Non-interactive. Run to completion and exit. Do not wait for user input.

## Precondition
Read today's screening output: `runtime/screening/YYYY-MM-DD.md` (WIB date).
If file does not exist, exit silently — do not invent candidates.

## Sequence
For each ticker in today's shortlist with conviction `high` or `med`:
1. Execute `playbooks/trader/layer-4-trade-plan.md`

## Output
Write plans to `runtime/tradeplans/YYYY-MM-DD.md` (WIB date).
