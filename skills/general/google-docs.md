# Google Docs

## Purpose
Create, read, and append text to Google Docs through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Docs commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py docs create --title "Draft"
python3 ~/workspace/tools/general/scripts/google_workspace.py docs append --document-id DOC_ID --text "Hello"
```

## When to use
- draft structured notes
- create working documents for Boss O
- append research summaries

## Safety
- reading is safe
- creating/editing is internal and safe
- sharing externally still needs Boss O permission
