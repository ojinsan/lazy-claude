# Tokopedia

## What This Does
Search products, inspect product pages, view shops, compare items, and read cart/order pages using the logged-in Firefox profile.

## Tool Path
`~/.claude/tools/general/browser/tokopedia_browser.py`

## Usage
```bash
python3 ~/.claude/tools/general/browser/tokopedia_browser.py search --query "office chair"
python3 ~/.claude/tools/general/browser/tokopedia_browser.py compare --urls URL1 URL2
```

## When to use
- shopping research
- marketplace comparison
- order tracking

## Safety
- read-only only
- no checkout, no purchases, no account changes
