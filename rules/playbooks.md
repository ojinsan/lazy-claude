---
description: Rules for playbook definitions in playbooks/
---

# playbooks/ — Workflow Guides

Playbooks are step-by-step procedural guides for Claude to follow when assigned a role or task.
They are NOT cron job definitions — for scheduling, see schedule/ and rules/schedule.md.

## Structure
Each playbook is a markdown file: `playbooks/<role>/<name>.md`

## Playbook File Format
```
# <name>

## Use When
<trigger condition>

## Load First
<skills or context files to read>

## Workflow
1. Step one
2. Step two
...
```

## Rules
- Do not execute a playbook unless the user explicitly triggers it or a schedule does.
- Playbooks reference tools/ scripts and skills/ for execution — they contain no logic themselves.
- For trading workflows, load the trader skill before starting: skills/trader/README.md.
