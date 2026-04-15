# Google Sheets

## What This Does
Read, write, append, and create Google Sheets through the unified Google Workspace tool.

## Tool Path
`~/workspace/tools/general/scripts/google_workspace.py`

## Usage
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
