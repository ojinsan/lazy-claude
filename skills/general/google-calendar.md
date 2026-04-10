# Google Calendar

## What This Does
Read, create, update, and delete Google Calendar events through the unified Google Workspace tool.

## Tool Path
`~/.claude/tools/general/scripts/google_workspace.py`

## Usage
```bash
python3 ~/.claude/tools/general/scripts/google_workspace.py calendar list --days 7
python3 ~/.claude/tools/general/scripts/google_workspace.py calendar create --title "Meeting" --start "2026-04-02T09:00:00+07:00" --end "2026-04-02T10:00:00+07:00"
```

## When to use
- check schedule availability
- add or update events for Boss O
- review calendar before planning work

## Safety
- reading is safe
- creating/updating calendar events is low risk
- deleting events should be done carefully
