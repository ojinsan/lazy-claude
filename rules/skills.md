---
description: Rules for loading and using skills
---

# skills/ — Role-Based Playbooks

These are structured operating lenses, not code. Load only what the current job requires.

## Structure
| Dir                | Purpose                                  |
|--------------------|------------------------------------------|
| trader/            | Trading analysis, orderbook, risk rules  |
| personal-assistant/| Research, docs, scheduling, sheets       |
| general/           | Google Workspace, browser, web tools     |
| content-creator/   | Content and writing workflows            |

## Rule
- Do NOT load all skills. Jobs specify which skills they need.
- Tool resolution: skills → tools/ (matching role folder), then tools/other/ for shared helpers.
- Paths: ~/.claude/tools/<role>/
