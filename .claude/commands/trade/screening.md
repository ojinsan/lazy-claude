---
name: trade:screening
description: Automated pre-market screening — Layer 1 (macro context) + Layer 2 (stock screening). Runs non-interactively via cron at 05:00 and 05:30 WIB.
disable-model-invocation: true
---

Non-interactive. Run to completion and exit. Do not wait for user input.

## Sequence
1. Execute `playbooks/trader/layer-1-global-context.md`
2. Execute `playbooks/trader/layer-2-stock-screening.md`

## Output
Write structured report to `runtime/screening/YYYY-MM-DD.md` (WIB date).
Scripts post to Airtable directly — do not duplicate.
