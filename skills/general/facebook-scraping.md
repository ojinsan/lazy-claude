---
name: facebook-scraping
description: Scrape Facebook Marketplace listings and general post search using Firefox-session-aware Playwright. Use when Boss O needs market price research, second-hand goods data, or public post sentiment from Facebook.
---

# Facebook Scraping

## Purpose

Browse Facebook Marketplace (for product/price research) and Facebook post search (for sentiment/narrative) using the logged-in Firefox profile.

## Tool Path

- `~/workspace/tools/general/playwright/facebook-scraper.js`

Runtime path (openclaw): `~/.openclaw/workspace/scarlett/tools/general/playwright/facebook-scraper.js`

## Firefox Profile

- Primary:  `~/.openclaw/workspace/scarlett/tools/general/playwright/.firefox-profile-facebook`
- Fallback: `~/workspace/tools/general/playwright/.firefox-profile-facebook`

Profile is auto-created on first run. Login once with `--headed` to persist the Facebook session.

## Modes

### Marketplace (default)

Scrapes listing cards from Facebook Marketplace search.

```bash
cd ~/workspace/tools/general/playwright
node facebook-scraper.js --query "mazda 2" --location jakarta --limit 20
```

With full listing detail (visits each listing page, slower):

```bash
node facebook-scraper.js --query "mazda 2" --location jakarta --limit 10 --detail
```

Output fields per listing: `url`, `title`, `price`, `location`, `description` (if `--detail`)

### General post search

Scrapes public posts from Facebook search results.

```bash
node facebook-scraper.js --query "banjir jakarta" --mode search --limit 15
```

Output fields per post: `url`, `author`, `timestamp`, `text`, `reactions`, `comments`

## Common Options

| Flag | Default | Description |
|------|---------|-------------|
| `--query` | required | Search keyword |
| `--mode` | `marketplace` | `marketplace` or `search` |
| `--location` | `jakarta` | City slug for marketplace URL |
| `--limit` | `20` | Max results |
| `--detail` | off | Visit each listing for full data |
| `--output` | none | Save JSON to file |
| `--headed` | off | Show browser UI (use for first login) |

## First-Time Login

Facebook requires a logged-in session for full results. Run once with `--headed` to authenticate:

```bash
node facebook-scraper.js --query "test" --headed
```

Then log in manually. Session is saved to the persistent Firefox profile and reused in headless runs.

## Constraints

- Do not post, message, react, or interact externally without Boss O permission.
- Collect only what is needed for local analysis.
- Do not expose cookies or session data.
