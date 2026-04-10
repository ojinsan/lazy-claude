# Google Drive

## What This Does
Search, list, upload, and download files in Google Drive through the unified Google Workspace tool.

## Tool Path
`~/.claude/tools/general/scripts/google_workspace.py`

## Usage
```bash
python3 ~/.claude/tools/general/scripts/google_workspace.py drive search --query "tradeplan"
python3 ~/.claude/tools/general/scripts/google_workspace.py drive upload --file ./note.txt
```

## When to use
- find files quickly
- upload local drafts
- pull down documents for analysis

## Safety
- searching/listing is safe
- uploads/downloads are internal file operations
- sharing files externally still needs permission
