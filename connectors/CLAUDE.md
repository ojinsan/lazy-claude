# connectors/ — External Service Clients

## Concept
Connectors are thin, reusable clients that know HOW to talk to one external service.
They do not contain business logic — only auth, request construction, and response parsing.

## Rule
- One directory per service.
- Tools import from connectors. Skills do not import directly.
- If a service has an MCP server, the connector's README documents both paths (MCP vs script).
- Auth/secrets always loaded from env or `.env.local` — never hardcoded.

## Available Connectors

| Connector   | Type              | Script Location                          | MCP Available |
|-------------|-------------------|------------------------------------------|---------------|
| stockbit    | REST API          | tools/trader/api.py                      | No            |
| airtable    | REST API + MCP    | tools/trader/airtable_client.py          | Yes           |
| notion      | Browser + MCP     | tools/general/browser/notion_browser.py  | Yes           |
| google      | OAuth REST        | tools/general/scripts/google_workspace.py| Yes (lazytools MCP) |
| threads     | Playwright        | tools/general/playwright/threads-scraper.js | Yes (lazytools MCP) |
| browser     | Playwright base   | tools/general/browser/browser_base.py    | No            |

## Dependency Direction
```
skills/ → tools/ → connectors/ → external services
plugins/ (MCP) → external services (native, no script needed)
```
