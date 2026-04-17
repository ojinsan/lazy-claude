---
name: instagram-scraping
description: Scrape or collect market-relevant information from Instagram using Firefox-session-aware Playwright workflows. Use when Claude needs to gather narrative, brand, founder, corporate, retail sentiment, or catalyst-related Instagram information for trader research, especially as input to layer 1 global context or insight-crawling.
---

# Instagram Scraping

## Purpose
Use Firefox-session-aware browser automation to collect public or logged-in Instagram information when it is relevant to market, sector, company, founder, or catalyst research.

## Primary Tooling
- Manual: `~/workspace/tools/manual/instagram.md`
- Scraper script: `~/workspace/tools/general/playwright/instagram-scraper.js`
- Browser script: `~/workspace/tools/general/browser/instagram_browser.py`

## Usage Path
Read `tools/manual/instagram.md` first for profile/session setup. Use scraper for collection flows. Use browser script for interactive inspection and screenshots.

## Intended Use
- collect narrative and sentiment clues from Instagram
- inspect corporate/founder/brand posts when relevant to market narratives
- support `insight-crawling` for layer 1 global context

## Common Calls
```bash
node ~/workspace/tools/general/playwright/instagram-scraper.js profile --username <username>
python3 ~/workspace/tools/general/browser/instagram_browser.py profile --username <username>
```

## Constraints
- do not post, like, follow, reply, or interact externally without Boss O permission
- do not expose cookies, credentials, or sensitive session data
- collect only what is needed for local analysis
