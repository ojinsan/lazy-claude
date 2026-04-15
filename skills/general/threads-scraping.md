---
name: threads-scraping
description: Scrape or collect market-relevant information from Threads using Firefox-session-aware Playwright workflows. Use when Claude needs to gather narrative, sentiment, catalyst chatter, or topic-specific Threads posts for trader research, especially as input to layer 1 global context or insight-crawling.
---

# Threads Scraping

Uses the existing Threads Playwright tools and can later share the common browser foundation patterns in `~/workspace/tools/general/browser/`.

## Purpose

Use Firefox-session-aware browser automation to collect public or logged-in Threads information when it is relevant to market, sector, or ticker narrative work.

## Current Status

This is a skill. A first Playwright workflow now exists and should be used conservatively.

## Intended Use

- collect Threads posts related to sector/theme/ticker narrative
- gather public chatter around catalyst topics
- support `insight-crawling` for layer 1 global context

## Constraints

- do not post, like, follow, reply, or interact externally without Boss O permission
- do not expose cookies, credentials, or sensitive session data
- collect only what is needed for local analysis

## Tool Paths

- Active: `~/workspace/tools/general/playwright/threads-scraper.js`
- Compatibility wrapper (deprecated entrypoint): `~/workspace/tools/general/playwright/threads_search.py`

The Python wrapper exists only so old calls do not break. Preferred usage is the JS scraper.

## Run Pattern

```bash
cd ~/workspace/tools/general/playwright
node threads-scraper.js --query "IDX Indonesia MSCI" --limit 10
```

Use headed mode first if a session check is needed:

```bash
node threads-scraper.js --query "IDX Indonesia MSCI" --limit 10 --headed
```

## Firefox Profile Standard

Default persistent profile for Threads tooling:

- `~/workspace/tools/general/playwright/.firefox-profile-threads`

Rule:
- if Boss O refreshes login/session in the original Firefox profile, sync the copied Scarlett profile again
- do not assume Chromium unless a tool explicitly requires it
- treat legacy `cloned_profile` paths as fallback only, not the standard
