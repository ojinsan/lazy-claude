# Google Sheets

## Purpose
Read, write, append, and create Google Sheets through Google Workspace tooling.

## Primary Tooling
- Manual: `~/workspace/tools/manual/google.md`
- Script: `~/workspace/tools/general/scripts/google_workspace.py`

## Usage Path
Read `tools/manual/google.md` first for auth and Workspace scope. Then use Sheets commands from `google_workspace.py`.

## Common Calls
```bash
python3 ~/workspace/tools/general/scripts/google_workspace.py sheets read --spreadsheet-id ID --range "Sheet1!A1:C10"
python3 ~/workspace/tools/general/scripts/google_workspace.py sheets append --spreadsheet-id ID --range "Sheet1!A:C" --values '[["a","b","c"]]'
```

## When to use
- research tables
- screening sheets
- structured note-taking
- appending summarized rows

## Safety
- internal spreadsheet edits are safe
- be careful not to overwrite important ranges unintentionally
