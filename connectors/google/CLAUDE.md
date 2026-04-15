# Connector: Google Workspace

Type: OAuth REST API
Script: `tools/general/scripts/google_workspace.py`
Supporting scripts: `google_sheet_crud.py`, `google_sheet_tab_write.py`

## Services Covered
- **Sheets** — read/write cells, append rows, tab management
- **Docs** — create/update documents
- **Gmail** — read/send email (see `skills/general/google-gmail.md`)
- **Maps** — geocoding, place search (`tools/general/scripts/google_maps.py`)
- **Tasks** — task list management (see `skills/general/google-tasks.md`)

## Auth
OAuth 2.0 credentials. Scopes vary by service.
Credential file: `.env.local` or service account JSON.

## Usage Pattern
```bash
python3 google_sheet_crud.py csv   # read sheet as CSV
python3 google_workspace.py        # generic workspace ops
```
