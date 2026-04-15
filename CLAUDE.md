# Claude Code — User Instructions

## Core Rules
- Be concise. No filler text, no summaries after tool calls.
- No emojis unless asked.
- Verify before acting on any memory — check current file state first.
- For destructive actions (delete, push, overwrite): always confirm first.
- Use the caveman skill/plugin when available for tasks it supports.

## Token Efficiency Rules
- Read only files explicitly relevant to the task.
- Do NOT bulk-read docs/ — grep or glob first, then read specific files.
- Keep context narrow: one task, one area at a time.

## Architecture (3 Layers)

```
tools/       → Service connectors + business logic scripts
skills/      → Role playbooks: context + rules for how to think per role
playbooks/   → Workflow guides: step-by-step context for active tasks
```

Dependency direction: `playbooks/skills → tools → external services`
Within tools/: connectors (thin service clients) are imported by business logic scripts.

**MCP servers + connectors + hooks**: see `tools/CLAUDE.md`

## Directory Map
| Dir          | Purpose                                                     |
|--------------|-------------------------------------------------------------|
| tools/       | Connectors + business logic scripts (trader/, general/)     |
| skills/      | Role playbooks (trader/, personal-assistant/, general/, …)  |
| playbooks/   | Workflow guides for Claude (trader/, personal-assistant/, adhoc/, …) |
| hooks/       | Hook scripts executed by settings.json                      |

## code/ Rules
- Each project lives in its own subdirectory with its own CLAUDE.md.
- Do not read across project boundaries unless explicitly asked.
- Check for existing venv/requirements before installing dependencies.

## Importing Context
- For trading tasks: read playbooks/trader/CLAUDE.md FIRST (mission, schedule, 4-layer structure, data pipeline), then load skills/trader/CLAUDE.md (philosophy, SID rules, broker rules, skills+tools index). Load individual layer skills only when that layer is active.
- For personal assistant tasks: see skills/personal-assistant/CLAUDE.md
- For tool usage, connectors, and file index: see tools/CLAUDE.md
