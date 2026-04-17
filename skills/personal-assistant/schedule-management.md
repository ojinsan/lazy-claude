# Schedule Management

## Purpose
Use Calendar and Tasks together to manage time and follow-ups.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Calendar and Tasks commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py calendar list --days 7
python3 ~/workspace/tools/general/scripts/google_workspace.py tasks list
```

## Use This When
- checking availability
- creating or moving events
- tracking follow-up tasks

## Safety
- calendar/task edits are okay
- be careful with deletion
