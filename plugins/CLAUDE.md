# plugins/ — Claude Code Extensions

## Concept
Plugins extend Claude Code's native capabilities at the agent level.
They do not contain business logic — they wire up how Claude perceives and acts.

## Three Plugin Types

### 1. Hooks (`~/workspace/hooks/`)
Shell scripts that fire on Claude Code lifecycle events.
Configured in `~/.claude/settings.json`.

| Script        | Event        | Purpose                                 |
|---------------|--------------|-----------------------------------------|
| pre-bash.sh   | PreToolUse   | Block dangerous Bash commands           |
| post-tool.sh  | PostToolUse  | Log all tool calls to tool-log.txt      |

### 2. MCP Servers
Extend Claude with native tool access to external services.
Configured via claude.ai integrations (not in settings.json manually).

| MCP Server  | Provides                            | Use instead of        |
|-------------|-------------------------------------|-----------------------|
| Airtable    | CRUD on all bases/tables            | airtable_client.py    |
| Notion      | Read/write pages, databases         | notion_browser.py     |

### 3. Commands (`~/workspace/.claude/commands/`)
Slash commands that trigger skills or jobs.
Written as markdown prompt templates, invoked as `/command-name`.

See `.claude/commands/` for available commands.

## Rule
- Hooks and commands live in this workspace repo (version-controlled).
- MCP server auth lives in claude.ai — do not store tokens here.
- A plugin adds a capability; a tool uses it.
