---
description: Rules for job definitions in ~/.claude/jobs/
---

# jobs/ — Scheduled and Recurring Jobs

## Structure
Each job is a markdown file or folder: `~/.claude/jobs/<role>/<name>.md`

## Job File Format
```
# Job: <name>
Schedule: <cron or interval>
Command: <claude -p "..." or shell command>
Output: <where results go>
Last run: <date>
```

## Rules
- Do not run jobs manually unless user explicitly asks.
- Log outputs to ~/.claude/jobs/logs/<name>.log
