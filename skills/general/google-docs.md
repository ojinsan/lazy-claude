# Google Docs

## What This Does
Create, read, and append text to Google Docs using the unified Google Workspace tool.

## Tool Path
`~/.claude/tools/general/scripts/google_workspace.py`

## Usage
```bash
python3 ~/.claude/tools/general/scripts/google_workspace.py docs create --title "Draft"
python3 ~/.claude/tools/general/scripts/google_workspace.py docs append --document-id DOC_ID --text "Hello"
```

## When to use
- draft structured notes
- create working documents for Boss O
- append research summaries

## Safety
- reading is safe
- creating/editing is internal and safe
- sharing externally still needs Boss O permission
