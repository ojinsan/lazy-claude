# Connector: Notion

Type: Browser automation + MCP
Script: `tools/general/browser/notion_browser.py`
MCP: Configured via claude.ai Notion integration

## Two Access Paths

### MCP (preferred for Claude-native tasks)
Use `mcp__claude_ai_Notion__*` tools directly.
Operations: fetch, search, create-pages, update-page, create-database, get-comments.
Best for: reading/writing structured content, page creation, interactive tasks.

### Browser Script
`tools/general/browser/notion_browser.py` — Playwright-based, logged-in session.
Best for: operations not covered by MCP, bulk interactions.

## Auth
MCP: claude.ai oauth
Browser: Firefox profile with logged-in Notion session
