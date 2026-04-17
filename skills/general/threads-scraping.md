---
name: threads-scraping
description: Scrape or collect market-relevant information from Threads using Firefox-session-aware Playwright workflows. Use when Claude needs to gather narrative, sentiment, catalyst chatter, or topic-specific Threads posts for trader research, especially as input to layer 1 global context or insight-crawling.
---

# Threads Scraping

## Purpose
Use Firefox-session-aware browser automation to collect public or logged-in Threads information when it is relevant to market, sector, or ticker narrative work.

## Primary Tooling
- Manual: `~/workspace/tools/manual/threads.md`
- Primary script: `~/workspace/tools/general/playwright/threads-scraper.js`
- Compatibility wrapper: `~/workspace/tools/general/playwright/threads_search.py`

## Usage Path
Read `tools/manual/threads.md` first for profile/session handling. Preferred usage is the JS scraper. Python wrapper exists only so old calls do not break.

## Intended Use
- collect Threads posts related to sector/theme/ticker narrative
- gather public chatter around catalyst topics
- support `insight-crawling` for layer 1 global context

## Common Calls
```bash
cd ~/workspace/tools/general/playwright
node threads-scraper.js --query "IDX Indonesia MSCI" --limit 10
node threads-scraper.js --query "IDX Indonesia MSCI" --limit 10 --headed
```

## Constraints
- do not post, like, follow, reply, or interact externally without Boss O permission
- do not expose cookies, credentials, or sensitive session data
- collect only what is needed for local analysis
