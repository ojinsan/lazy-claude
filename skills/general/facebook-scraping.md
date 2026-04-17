---
name: facebook-scraping
description: Scrape Facebook Marketplace listings and general post search using Firefox-session-aware Playwright. Use when Boss O needs market price research, second-hand goods data, or public post sentiment from Facebook.
---

# Facebook Scraping

## Purpose
Browse Facebook Marketplace for product/price research and Facebook search for public post sentiment using the logged-in Firefox profile.

## Primary Tooling
- Manual: `~/workspace/tools/manual/facebook.md`
- Script: `~/workspace/tools/general/playwright/facebook-scraper.js`

## Usage Path
Read `tools/manual/facebook.md` first for profile/session setup, modes, and flags. Then run `facebook-scraper.js` with the needed mode.

## Common Calls
```bash
cd ~/workspace/tools/general/playwright
node facebook-scraper.js --query "mazda 2" --location jakarta --limit 20
node facebook-scraper.js --query "banjir jakarta" --mode search --limit 15
```

## When to use
- marketplace price research
- second-hand goods comparison
- public Facebook post sentiment or topic scan

## Constraints
- do not post, message, react, or interact externally without Boss O permission
- collect only what is needed for local analysis
- do not expose cookies or session data
