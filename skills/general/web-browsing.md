# Web Browsing

## What This Does
Open modern web pages with Playwright Firefox, extract rendered text, collect links, and capture screenshots.

## Tool Path
`~/workspace/tools/general/browser/web_browse.py`

## Usage
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
