# Notion

## What This Does
Open public or shared Notion pages, read rendered content, search inside the page, append text to editable shared pages, and capture screenshots/OCR.

## Tool Path
`~/.claude/tools/general/browser/notion_browser.py`

## Usage
```bash
source ~/workspace/.venv-browser/bin/activate
python ~/.claude/tools/general/browser/notion_browser.py open --url "https://www.notion.so/..." --extract text
python ~/.claude/tools/general/browser/notion_browser.py search --url "https://www.notion.so/..." --query "Scarlett"
python ~/.claude/tools/general/browser/notion_browser.py append --url "https://www.notion.so/..." --text "hello from Scarlett"
python ~/.claude/tools/general/browser/notion_browser.py screenshot --url "https://www.notion.so/..."
```

## When to use
- review a public/shared Notion page
- pull text from a Notion page rendered in browser
- search inside a page quickly
- append text to a publicly editable page with Boss O approval
- inspect layout visually with screenshots

## Safety
- reading public/shared pages is safe
- editing a shared page should only be done with Boss O approval
- some public edit links still require a logged-in Notion account before write actions work
- do not paste sensitive data into public edit links
