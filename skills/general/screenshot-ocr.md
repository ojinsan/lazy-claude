# Screenshot OCR

## What This Does
Capture screenshots from browser pages and hand them off for OCR / vision analysis when text is embedded in images.

## Tool Path
`~/.claude/tools/general/browser/browser_base.py`

## Usage
- use browser tools with screenshot flags
- use `ocr_screenshot()` from the shared browser base for story/image extraction

## When to use
- Instagram stories
- text inside screenshots
- UI text that normal DOM extraction misses

## Safety
- screenshots stay local unless Boss O approves external sharing
