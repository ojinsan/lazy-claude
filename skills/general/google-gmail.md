# Google Gmail

## Purpose
Search, read, draft, and send Gmail through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Gmail commands from `google_workspace.py`.

## Common Calls
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
