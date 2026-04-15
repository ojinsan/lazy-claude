---
name: trade:monitoring
description: Automated intraday monitoring — Layer 3 + conditional Layer 4. Runs every 30m during market hours via cron (09:00–15:00 WIB).
disable-model-invocation: true
---

Non-interactive. Run to completion and exit. Do not wait for user input.

## Sequence
1. Execute `playbooks/trader/layer-3-stock-monitoring.md`
2. If any name promoted to L4 or structure shifted since last run: execute `playbooks/trader/layer-4-trade-plan.md` for those names only
3. If WIB time is 15:00–15:30: also run EOD publish (`tools/trader/runtime_eod_publish.py`)

## Output
Append 30m block to `runtime/monitoring/YYYY-MM-DD.md` (WIB date):
```
## HH:MM WIB
- [TICKER] level: local/insights/alert | status: intact/thesis-break/flag | reason
- L4 updates: ...
```
Scripts post to Airtable directly — do not duplicate.
