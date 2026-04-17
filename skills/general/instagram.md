# Instagram

## Purpose
Browse Instagram profiles, posts, stories, feed, search, and reels through the logged-in Firefox profile.

## Primary Tooling
- Manual: `~/workspace/tools/manual/instagram.md`
- Browser script: `~/workspace/tools/general/browser/instagram_browser.py`
- Scraper script: `~/workspace/tools/general/playwright/instagram-scraper.js`

## Usage Path
Read `tools/manual/instagram.md` first for profile/session setup. Use `instagram_browser.py` for browser-style inspection and screenshots. Use `instagram-scraper.js` when scraper flow fits better.

## Common Calls
```bash
python3 ~/workspace/tools/general/browser/instagram_browser.py profile --username nasa
python3 ~/workspace/tools/general/browser/instagram_browser.py stories --username nasa --screenshot-all
```

## When to use
- inspect an account's posts
- read captions and visible profile info
- capture screenshots for visual review or OCR

## Safety
- read-only only
- no liking, commenting, following, or sending DMs
