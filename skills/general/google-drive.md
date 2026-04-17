# Google Drive

## Purpose
Search, list, upload, and download files in Google Drive through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Drive commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py drive search --query "tradeplan"
python3 ~/workspace/tools/general/scripts/google_workspace.py drive upload --file ./note.txt
```

## When to use
- find files quickly
- upload local drafts
- pull down documents for analysis

## Safety
- searching/listing is safe
- uploads/downloads are internal file operations
- sharing files externally still needs permission
