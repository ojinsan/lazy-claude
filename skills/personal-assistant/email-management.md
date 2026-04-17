# Email Management

## Purpose
Use Gmail for search, triage, reading, and drafting.

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

## Use This When
- Boss O wants inbox triage
- an old email must be found quickly
- a reply draft is needed

## Safety
- reading and drafting are safe
- sending requires Boss O approval
