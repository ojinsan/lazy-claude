# tools/ — Guide

Business logic scripts and service connectors. Called by playbooks/, skills/, or the MCP server.

## How to pick a tool

1. **Check the active skill first.** `skills/<role>/CLAUDE.md` names the specific file to use for each scenario. This is the primary source.
2. **If unsure which file to use**, consult `tools/INDEX.md` — full per-script descriptions with layer tags.
3. **Before calling any service**, read `tools/manual/<service>.md` — each manual lists what cases it covers and a minimal how-to.

## Connectors (service clients)

| Connector   | Type              | MCP | Manual |
|-------------|-------------------|-----|--------|
| stockbit    | REST API          | No  | `manual/stockbit.md` |
| airtable    | REST API + MCP    | Yes | `manual/airtable.md` |
| notion      | Browser + MCP     | Yes | `manual/notion.md` |
| google      | OAuth REST        | Yes | `manual/google.md` |
| threads     | Playwright        | Yes | `manual/threads.md` |
| instagram   | Playwright        | No  | `manual/instagram.md` |
| browser     | Playwright base   | No  | `manual/browser.md` |
| telegram    | Bot API           | No  | `manual/telegram.md` |

Rules: no business logic in connectors. Auth/secrets from `.env.local` only. Prefer MCP for Claude-native tasks; use scripts for scheduled/automated jobs.
