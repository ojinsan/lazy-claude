---
description: Rules for using tools in ~/.claude/tools/
---

# tools/ — Reusable Scripts and Utilities

Location: ~/.claude/tools/

## Rules
- Scripts here are standalone and reusable across jobs.
- Always check if a tool already exists before creating a new one.
- Prefer Python for data/finance tools, bash for glue scripts.
- Each script must have a comment header: purpose, usage, dependencies.
