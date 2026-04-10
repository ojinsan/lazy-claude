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

## Directory Map
| Location               | Purpose                                        |
|------------------------|------------------------------------------------|
| ~/.claude/skills/      | Role playbooks (trader/, personal-assistant/, general/, content-creator/) |
| ~/.claude/jobs/        | Workflow definitions (trader/, personal-assistant/, adhoc/, etc.) |
| ~/.claude/rules/       | Scoped rules for skills, tools, jobs, code     |
| ~/.claude/hooks/       | Hook scripts (pre/post tool use)               |
| ~/.claude/tools/       | Reusable scripts (trader/, general/, other/)   |
| ~/workspace/code/      | Active code projects                           |

## Importing Context
- For trading tasks: read ~/.claude/jobs/trader/README.md + use `/trade`
- For personal assistant tasks: see ~/.claude/skills/personal-assistant/README.md
- For tool usage: see ~/.claude/rules/tools.md — scripts live in ~/.claude/tools/
- For job templates: see ~/.claude/rules/jobs.md
