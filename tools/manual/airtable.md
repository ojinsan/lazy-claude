# Connector: Airtable

Type: REST API + MCP
Script: `tools/trader/airtable_client.py`
MCP: Configured via claude.ai Airtable integration

## Two Access Paths

### MCP (preferred for Claude-native tasks)
Use the `mcp__claude_ai_Airtable__*` tools directly in Claude.
Workflow: search_bases → list_tables → get_schema → list/update records
Best for: ad-hoc queries, interactive exploration, updates from Claude.

### Script (preferred for automated jobs)
`tools/trader/airtable_client.py` — direct REST via AIRTABLE_PAT
Best for: scheduled jobs, batch writes, tool-to-tool pipelines.

## Auth
Env var: `AIRTABLE_PAT` (Personal Access Token)
Loaded from: `/home/lazywork/.openclaw/workspace/.env.local`

## Key Bases (Trader)
- Trading journal
- Watchlist (4-group structure)
- Trade plans
