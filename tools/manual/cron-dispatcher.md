# Cron Dispatcher

Script: `tools/trader/cron-dispatcher.sh`
Triggered by: system crontab (every 30m during trading hours)
Logs: `runtime/cron/YYYYMMDD.log`

## Purpose
Time-based dispatcher that runs Claude command files on the WIB daily schedule.
Each job calls `claude --bare -p` with the appropriate `.claude/commands/trade/*.md` file.

## Schedule

| WIB Time | Job | Command file |
|----------|-----|-------------|
| 05:00 | L1 + L2 screening | `trade/screening.md` |
| 06:00 | L4 trade plan | `trade/tradeplan.md` |
| 08:30 | Pre-open execution | `trade/execute.md` |
| 09:00–15:00 every 30m | L3 monitoring + execution | `trade/monitoring.md`, `trade/execute.md` |
| Off-hours | Skip | — |

## How it works
Runs `claude --dangerously-skip-permissions --bare --setting-sources user` with prompt pointing to the command file. Claude reads the command file and executes the trading workflow autonomously.

Uses `openclaude` context root for Claude settings, writes outputs to `workspace/runtime/`.

## Crontab entry
```
*/30 * * * * /home/lazywork/workspace/tools/trader/cron-dispatcher.sh
```
