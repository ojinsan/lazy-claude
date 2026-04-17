# Google Calendar

## Purpose
Read, create, update, and delete Google Calendar events through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Calendar commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py calendar list --days 7
python3 ~/workspace/tools/general/scripts/google_workspace.py calendar create --title "Meeting" --start "2026-04-02T09:00:00+07:00" --end "2026-04-02T10:00:00+07:00"
```

## When to use
- check schedule availability
- add or update events for Boss O
- review calendar before planning work

## Safety
- reading is safe
- creating/updating calendar events is low risk
- deleting events should be done carefully
