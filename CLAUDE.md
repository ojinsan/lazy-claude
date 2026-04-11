# Claude Code — User Instructions

## Identity
- User: Boss O | Market: Indonesia | Currency: IDR

## Core Rules
- Be concise. No filler text, no summaries after tool calls.
- No emojis unless asked.
- Verify before acting on any memory — check current file state first.
- For destructive actions (delete, push, overwrite): always confirm first.

## Token Efficiency Rules
- Read only files explicitly relevant to the task.
- Do NOT bulk-read docs/ — grep or glob first, then read specific files.
- Keep context narrow: one task, one area at a time.

## Architecture (4 Layers)

```
plugins/     → Claude Code extensions: hooks, MCP registry, slash commands
connectors/  → External service clients: one per service, no business logic
tools/       → Business logic scripts: import from connectors, called by jobs/skills
skills/      → Role playbooks: context + rules for how to think per role
```

Dependency direction: `skills → tools → connectors → external services`
MCP servers bypass the script stack: `plugins/MCP → external services (native)`

## Directory Map
| Dir          | Purpose                                                     |
|--------------|-------------------------------------------------------------|
| plugins/     | Hooks, MCP registry, command docs — see plugins/CLAUDE.md   |
| connectors/  | Service clients (stockbit, airtable, notion, google, …)     |
| tools/       | Business logic scripts (trader/, general/, other/)          |
| skills/      | Role playbooks (trader/, personal-assistant/, general/, …)  |
| jobs/        | Scheduled workflow definitions (trader/, adhoc/, etc.)      |
| schedule/    | Cron/trigger definitions                                    |
| hooks/       | Hook scripts executed by settings.json                      |
| code/        | Active code projects                                        |
| docs/        | Reference documentation                                     |

## code/ Rules
- Each project lives in its own subdirectory with its own CLAUDE.md.
- Do not read across project boundaries unless explicitly asked.
- Check for existing venv/requirements before installing dependencies.

## schedule/ Rules
- Cron definitions reference scripts in tools/ or commands in jobs/.
- Format: one .md file per scheduled task.
- Use `claude schedule` skill to register remote triggers.

## Importing Context
- For trading tasks: see skills/trader/README.md + jobs/trader/README.md
- For personal assistant tasks: see skills/personal-assistant/README.md
- For tool usage: see tools/CLAUDE.md
- For connector details: see connectors/CLAUDE.md
- For job templates: see jobs/CLAUDE.md
- For hooks/MCP/commands: see plugins/CLAUDE.md
