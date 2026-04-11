# Connector: Threads

Type: Playwright scraper (logged-in Firefox profile)
Scripts:
- `tools/general/playwright/threads-scraper.js` — search + scrape posts
- `tools/general/playwright/threads_search.py` — Python wrapper

## Capability
Scrapes Threads posts by query. Returns text, likes, replies.
Requires logged-in Firefox profile for authenticated access.

## Usage
```bash
node tools/general/playwright/threads-scraper.js \
  --query "keyword" --limit 10 --output /tmp/out.json
```

## Profile
Firefox profile with Threads session: `tools/general/playwright/.firefox-profile-threads`
Do NOT overwrite or clear this profile.

## Skill
See `skills/general/threads-scraping.md` for query patterns and output format.
