# Shopee

## What This Does
Search products, inspect product pages, view shops, compare items, and read cart/order pages using the logged-in Firefox profile.

## Tool Path
`~/.claude/tools/general/browser/shopee_browser.py`

## Usage
```bash
python3 ~/.claude/tools/general/browser/shopee_browser.py search --query "mechanical keyboard"
python3 ~/.claude/tools/general/browser/shopee_browser.py compare --urls URL1 URL2
```

## When to use
- shopping research
- product comparison
- order status checking

## Safety
- read-only only
- no checkout, no cart changes, no purchases
