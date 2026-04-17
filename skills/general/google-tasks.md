# Google Tasks

## Purpose
List, create, complete, and delete Google Tasks through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Tasks commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py tasks list
python3 ~/workspace/tools/general/scripts/google_workspace.py tasks create --title "Follow up"
```

## When to use
- turn requests into tracked tasks
- manage personal assistant follow-ups
- clear completed work

## Safety
- task management is safe
- deleting tasks should be intentional
