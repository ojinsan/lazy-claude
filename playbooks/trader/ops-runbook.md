# Ops Runbook — Trader CRON

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-8-orchestration.md`

## Pause CRON

Comment out the crontab line:

```bash
crontab -e
# Add # before the dispatcher line:
# * * * * * /home/lazywork/workspace/tools/trader/cron-dispatcher.sh
```

Or use the kill-switch (faster, no edit needed):

```python
# In Python / Claude Code session:
from tools._lib import current_trade as ct_mod
ct = ct_mod.load()
ct.trader_status.aggressiveness = "off"
ct_mod.save(ct, "l0", "ok", note="manual kill-switch")
```

`aggressiveness=off` aborts L2/L3/L4/L5 at their own healthchecks. The dispatcher still ticks, but every layer exits immediately.

## Resume CRON

```bash
crontab -e
# Remove the # from the dispatcher line
```

Or flip aggressiveness back via L0 playbook (preferred — lets L0 re-assess the right tier).

## Read today's log

```bash
tail -f /home/lazywork/workspace/runtime/cron/$(TZ='Asia/Jakarta' date +%Y%m%d).log
```

Key patterns:
- `→ LABEL start` — job fired
- `← LABEL done` — job completed OK
- `← LABEL FAILED` — job returned non-zero; scroll up for error output
- `WARN ... failed — falling back` — openclaude settings failed, retried with default Claude
- `off-hours — skip` — dispatcher tick outside any window (normal)

## Force-rerun a layer

```bash
cd /home/lazywork/workspace
claude --dangerously-skip-permissions --bare \
  -p "Non-interactive cron run. Read the instructions in .claude/commands/trade/LAYER.md and execute them. Run to completion and exit. Do not wait for user input."
```

Replace `LAYER` with `portfolio`, `insight`, `screening`, `tradeplan`, `execute`, `monitor`.

## Rotate Carina broker token

1. Run `python3 tools/trader/stockbit_login.py` → saves fresh token
2. Run `python3 tools/trader/stockbit_auth.py` → verify token active
3. Check `runtime/cron/YYYYMMDD.log` for next L5 healthcheck to confirm no `token expired` warn

## Force-run watchdog

```bash
cd /home/lazywork/workspace
python3 tools/trader/runtime_cron_watchdog.py
```

Watchdog reads today's log, telegrams any missed windows, prunes logs >30d.

## Emergency stop sequence

1. **Kill-switch:** set `aggressiveness=off` (stops L2–L5 immediately, no order placement)
2. **Pause CRON:** comment out crontab line (stops all new jobs)
3. **Cancel open orders:** use Carina app or `mcp__lazytools__carina_cancel_order` MCP tool
4. **Verify holdings:** run `/trade:portfolio` manually to confirm state
5. **Resume when ready:** uncomment crontab + set appropriate aggressiveness tier via L0

## Holiday file

`vault/data/idx_holidays.json` — update yearly from IDX official announcement.

```bash
# Edit and add new year's holidays:
code vault/data/idx_holidays.json
```

Missing file → dispatcher treats every day as trading day (fail-open, logs a warning once).

## Log rotation

Watchdog prunes `runtime/cron/*.log` files older than 30 days automatically at 09:05 WIB.
Manual prune if needed:

```bash
find /home/lazywork/workspace/runtime/cron -name "*.log" -mtime +30 -delete
```
