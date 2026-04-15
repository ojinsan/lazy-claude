# Google Gmail

## What This Does
Search, read, draft, and send Gmail through the unified Google Workspace tool.

## Tool Path
`~/workspace/tools/general/scripts/google_workspace.py`

## Usage
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py gmail search --query "from:boss@example.com"
python3 ~/workspace/tools/general/scripts/google_workspace.py gmail draft --to x@y.com --subject "Hi" --body "Draft body"
```

## When to use
- search old emails
- read important messages
- prepare drafts for Boss O

## Safety
- reading/searching is safe
- drafting is safe
- sending email requires Boss O permission
