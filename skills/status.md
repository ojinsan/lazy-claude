---
name: status
description: Check current workspace status — recent file changes, active jobs, and hook activity log.
disable-model-invocation: true
---

Check the current workspace status:
1. List files modified in the last 24h under ~/ (use find with -mtime -1)
2. Show any active jobs in ~/.claude/jobs/
3. Show last 5 lines of ~/.claude/hooks/tool-log.txt if it exists
Report concisely, no filler.
