# Connector: Facebook

Type: Playwright scraper (logged-in Firefox profile)
Script: `tools/general/playwright/facebook-scraper.js`

## Capability
Scrapes Facebook Marketplace listings and Facebook search posts.
Requires persistent Firefox profile for logged-in access.

## Profile
Primary runtime profile may live under openclaw runtime paths.
Workspace fallback profile: `tools/general/playwright/.firefox-profile-facebook`

If session missing, run headed once and log in manually:

```bash
cd tools/general/playwright
node facebook-scraper.js --query "test" --headed
```

Do not overwrite or clear saved profile casually.

## Modes
- `marketplace` — product/listing search
- `search` — general Facebook post search

## Common Calls
```bash
cd tools/general/playwright
node facebook-scraper.js --query "mazda 2" --location jakarta --limit 20
node facebook-scraper.js --query "banjir jakarta" --mode search --limit 15
```

## Common Flags
- `--query` — required keyword
- `--mode` — `marketplace` or `search`
- `--location` — marketplace city slug
- `--limit` — max results
- `--detail` — visit each listing for more fields
- `--output` — write JSON to file
- `--headed` — show browser UI for session/login checks

## Constraints
- Read-only only. No posting, messaging, reacting, or external interaction without permission.
- Collect only what is needed for local analysis.
- Do not expose cookies or session data.
