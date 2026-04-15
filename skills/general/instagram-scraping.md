---
name: instagram-scraping
description: Scrape or collect market-relevant information from Instagram using Firefox-session-aware Playwright workflows. Use when Claude needs to gather narrative, brand, founder, corporate, retail sentiment, or catalyst-related Instagram information for trader research, especially as input to layer 1 global context or insight-crawling.
---

# Instagram Scraping

## Purpose

Use Firefox-session-aware browser automation to collect public or logged-in Instagram information when it is relevant to market, sector, company, founder, or catalyst research.

## Current Status

Basic scraper available. Firefox profile at `~/workspace/tools/general/playwright/.firefox-profile-instagram/` must be pre-seeded with a logged-in session (copy from `~/.mozilla/firefox/<profile>/` after manual login).

## Intended Use

- collect narrative and sentiment clues from Instagram
- inspect corporate/founder/brand posts when relevant to market narratives
- support `insight-crawling` for layer 1 global context

## Constraints

- do not post, like, follow, reply, or interact externally without Boss O permission
- do not expose cookies, credentials, or sensitive session data
- collect only what is needed for local analysis

## Tools

- `~/workspace/tools/general/playwright/instagram-scraper.js` — Firefox-session-aware Instagram scraper
- `~/workspace/tools/general/browser/instagram_browser.py` — Python Playwright Instagram automation
