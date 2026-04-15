---
name: trade:execute
description: Execution layer — portfolio health check, exit decisions, entry orders. Places REAL orders via Carina API. Runs at 08:30 WIB pre-market and on-demand when L3 flags actionable signal.
disable-model-invocation: true
---

Non-interactive. Run to completion and exit. Do not wait for user input.

## Preconditions
- Today's L4 plan must exist: `runtime/tradeplans/YYYY-MM-DD.md` (WIB date)
- If file missing → run `/trade:tradeplan` first, then execute

## Sequence
1. Execute `playbooks/trader/execution.md`

## Output
- Orders logged to `runtime/orders/YYYY-MM-DD.jsonl`
- Airtable `Superlist` updated
- Telegram sent before and after each order
