# Web Browsing

## Purpose
Open modern web pages with Playwright Firefox, extract rendered text, collect links, and capture screenshots.

## Primary Tooling
- Manual: `~/workspace/tools/manual/browser.md`
- Script: `~/workspace/tools/general/browser/web_browse.py`

## Usage Path
Read `tools/manual/browser.md` first for browser-automation pattern. Then use `web_browse.py` for rendered browsing.

## Common Calls
```bash
python3 ~/workspace/tools/general/browser/web_browse.py open --url https://example.com --extract all
python3 ~/workspace/tools/general/browser/web_browse.py search --query "IHSG outlook"
```

## When to use
- JS-heavy websites
- pages that `web_fetch` cannot render well
- screenshot-based inspection

## Safety
- browser is read-only by default
- no form submission or external actions unless explicitly approved
