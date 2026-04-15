---
name: insight-crawling
description: Crawl and gather market, sector, theme, and narrative insight from web, Threads, and browser sources for trader layer 1 global context work. Use when building top-down context, catalyst maps, sector leadership views, government-policy context, or narrative/theme intelligence such as MSCI, konglo play, M&A, dividend play, and macro/news-driven idea generation.
---

# Insight Crawling

Use real browser-based crawling now:
- `~/workspace/tools/general/browser/web_browse.py` for general rendered browsing
- `~/workspace/tools/general/browser/instagram_browser.py` for Instagram-based inspection
- existing Threads tools for Threads-specific crawling


## Purpose

Use this skill for top-down market intelligence gathering.

## Role In Layer 1

This skill is primarily the **context-fetch** part of Layer 1.

It should gather broad evidence from:
- web tools
- RAG retrieval
- Threads scraping
- later browser/news crawling

It should not replace Claude's actual Layer 1 thinking.
Claude must still do:
- context-map
- aggression selection
- exploit/opportunity hunting

## Current Inputs

- RAG retrieval through trader tools
- Threads scraping through general Playwright tooling
- Stockbit context through trader tools

## Related Skills

- `~/workspace/skills/general/threads-scraping.md`
- `~/workspace/skills/general/instagram-scraping.md`

## Placeholder / Tool Paths

- Threads scraper: `~/workspace/tools/general/playwright/threads-scraper.js`
- Layer 1 input collector: `~/workspace/tools/trader/runtime_layer1_context.py`

## Notes

- use collected evidence to support Claude thinking, not to replace it
- keep weak/noisy context local
- post only meaningful market/theme insight into Airtable `Insights`
