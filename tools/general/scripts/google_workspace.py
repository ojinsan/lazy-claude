#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path("/home/lazywork/.openclaw/workspace")
TOKEN_DIR = WORKSPACE / "scarlett" / "runtime" / "tokens"  # openclaw runtime path (on-disk name)
ENV_PATH = WORKSPACE / ".env.local"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

SCOPES = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "gmail_read": ["https://www.googleapis.com/auth/gmail.readonly"],
    "gmail_compose": [
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://www.googleapis.com/auth/gmail.readonly",
    ],
    "sheets": ["https://www.googleapis.com/auth/spreadsheets"],
    "docs": ["https://www.googleapis.com/auth/documents"],
    "drive": ["https://www.googleapis.com/auth/drive"],
    "tasks": ["https://www.googleapis.com/auth/tasks"],
}


def load_env() -> None:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def token_path(key: str) -> Path:
    return TOKEN_DIR / f"google_workspace_{key}.json"


def get_credentials(scope_key: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    load_env()
    scopes = SCOPES[scope_key]
    path = token_path(scope_key)
    creds = None
    if path.exists():
        creds = Credentials.from_authorized_user_file(str(path), scopes=scopes)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
        return creds

    # Fall back to the shared OAuth token (covers all workspace scopes)
    shared = TOKEN_DIR / "google_workspace_all.json"
    if not shared.exists():
        raise RuntimeError(f"No token at {shared}. Run tools/mcp-server/google_auth_setup.py first.")
    creds = Credentials.from_authorized_user_file(str(shared))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        shared.write_text(creds.to_json())
    path.write_text(creds.to_json())
    return creds


def service(name: str, version: str, scope_key: str):
    from googleapiclient.discovery import build

    creds = get_credentials(scope_key)
    return build(name, version, credentials=creds, cache_discovery=False)


def parse_json_values(raw: str) -> Any:
    return json.loads(raw)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def calendar_list(days: int, calendar_id: str) -> dict:
    svc = service("calendar", "v3", "calendar")
    time_min = datetime.now(timezone.utc).isoformat()
    time_max = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    items = svc.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy="startTime").execute().get("items", [])
    return {"ok": True, "items": items}


def calendar_create(title: str, start: str, end: str, description: str | None, calendar_id: str) -> dict:
    svc = service("calendar", "v3", "calendar")
    body = {"summary": title, "start": {"dateTime": start}, "end": {"dateTime": end}}
    if description:
        body["description"] = description
    item = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return {"ok": True, "item": item}


def calendar_update(event_id: str, calendar_id: str, title: str | None, start: str | None, end: str | None, description: str | None) -> dict:
    svc = service("calendar", "v3", "calendar")
    item = svc.events().get(calendarId=calendar_id, eventId=event_id).execute()
    if title:
        item["summary"] = title
    if start:
        item["start"] = {"dateTime": start}
    if end:
        item["end"] = {"dateTime": end}
    if description is not None:
        item["description"] = description
    updated = svc.events().update(calendarId=calendar_id, eventId=event_id, body=item).execute()
    return {"ok": True, "item": updated}


def calendar_delete(event_id: str, calendar_id: str) -> dict:
    svc = service("calendar", "v3", "calendar")
    svc.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return {"ok": True, "deleted": event_id}


def gmail_search(query: str, max_results: int) -> dict:
    svc = service("gmail", "v1", "gmail_read")
    items = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute().get("messages", [])
    return {"ok": True, "items": items}


def _gmail_message_to_dict(msg: dict) -> dict:
    headers = {h.get("name"): h.get("value") for h in msg.get("payload", {}).get("headers", [])}
    snippet = msg.get("snippet", "")
    return {"id": msg.get("id"), "threadId": msg.get("threadId"), "snippet": snippet, "headers": headers, "labelIds": msg.get("labelIds", [])}


def gmail_read(message_id: str) -> dict:
    svc = service("gmail", "v1", "gmail_read")
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    return {"ok": True, "item": _gmail_message_to_dict(msg), "raw": msg}


def _make_mime(to: str, subject: str, body: str) -> dict:
    raw = f"To: {to}\r\nSubject: {subject}\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{body}".encode("utf-8")
    return {"raw": base64.urlsafe_b64encode(raw).decode("utf-8")}


def gmail_draft(to: str, subject: str, body: str) -> dict:
    svc = service("gmail", "v1", "gmail_compose")
    item = svc.users().drafts().create(userId="me", body={"message": _make_mime(to, subject, body)}).execute()
    return {"ok": True, "item": item}


def gmail_send(to: str, subject: str, body: str) -> dict:
    svc = service("gmail", "v1", "gmail_compose")
    item = svc.users().messages().send(userId="me", body=_make_mime(to, subject, body)).execute()
    return {"ok": True, "item": item}


def gmail_labels() -> dict:
    svc = service("gmail", "v1", "gmail_compose")
    items = svc.users().labels().list(userId="me").execute().get("labels", [])
    return {"ok": True, "items": items}


def sheets_read(spreadsheet_id: str, range_name: str) -> dict:
    svc = service("sheets", "v4", "sheets")
    values = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute().get("values", [])
    return {"ok": True, "values": values}


def sheets_write(spreadsheet_id: str, range_name: str, values: list) -> dict:
    svc = service("sheets", "v4", "sheets")
    item = svc.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="USER_ENTERED", body={"values": values}).execute()
    return {"ok": True, "item": item}


def sheets_append(spreadsheet_id: str, range_name: str, values: list) -> dict:
    svc = service("sheets", "v4", "sheets")
    item = svc.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": values}).execute()
    return {"ok": True, "item": item}


def sheets_create(title: str) -> dict:
    svc = service("sheets", "v4", "sheets")
    item = svc.spreadsheets().create(body={"properties": {"title": title}}).execute()
    return {"ok": True, "item": item}


def docs_read(document_id: str) -> dict:
    svc = service("docs", "v1", "docs")
    item = svc.documents().get(documentId=document_id).execute()
    return {"ok": True, "item": item}


def docs_create(title: str, body: str | None) -> dict:
    svc = service("docs", "v1", "docs")
    doc = svc.documents().create(body={"title": title}).execute()
    if body:
        svc.documents().batchUpdate(documentId=doc["documentId"], body={"requests": [{"insertText": {"location": {"index": 1}, "text": body}}]}).execute()
    return {"ok": True, "item": doc}


def docs_append(document_id: str, text: str) -> dict:
    svc = service("docs", "v1", "docs")
    doc = svc.documents().get(documentId=document_id).execute()
    end_index = doc.get("body", {}).get("content", [])[-1].get("endIndex", 1) - 1
    item = svc.documents().batchUpdate(documentId=document_id, body={"requests": [{"insertText": {"location": {"index": end_index}, "text": text}}]}).execute()
    return {"ok": True, "item": item}


def drive_search(query: str, max_results: int) -> dict:
    svc = service("drive", "v3", "drive")
    items = svc.files().list(q=f"name contains '{query}'", pageSize=max_results, fields="files(id,name,mimeType,modifiedTime,parents)").execute().get("files", [])
    return {"ok": True, "items": items}


def drive_list(folder_id: str | None, max_results: int) -> dict:
    svc = service("drive", "v3", "drive")
    q = f"'{folder_id}' in parents" if folder_id else None
    items = svc.files().list(q=q, pageSize=max_results, fields="files(id,name,mimeType,modifiedTime,parents)").execute().get("files", [])
    return {"ok": True, "items": items}


def drive_download(file_id: str, output: str) -> dict:
    svc = service("drive", "v3", "drive")
    content = svc.files().get_media(fileId=file_id).execute()
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(content)
    return {"ok": True, "path": str(out), "fileId": file_id}


def drive_upload(path: str, folder_id: str | None) -> dict:
    from googleapiclient.http import MediaFileUpload

    svc = service("drive", "v3", "drive")
    src = Path(path)
    body = {"name": src.name}
    if folder_id:
        body["parents"] = [folder_id]
    media = MediaFileUpload(str(src), resumable=False)
    item = svc.files().create(body=body, media_body=media, fields="id,name,mimeType,parents").execute()
    return {"ok": True, "item": item}


def tasks_list(tasklist: str, max_results: int) -> dict:
    svc = service("tasks", "v1", "tasks")
    items = svc.tasks().list(tasklist=tasklist, maxResults=max_results).execute().get("items", [])
    return {"ok": True, "items": items}


def tasks_create(title: str, notes: str | None, due: str | None, tasklist: str) -> dict:
    svc = service("tasks", "v1", "tasks")
    body: dict[str, Any] = {"title": title}
    if notes:
        body["notes"] = notes
    if due:
        body["due"] = due
    item = svc.tasks().insert(tasklist=tasklist, body=body).execute()
    return {"ok": True, "item": item}


def tasks_complete(task_id: str, tasklist: str) -> dict:
    svc = service("tasks", "v1", "tasks")
    item = svc.tasks().get(tasklist=tasklist, task=task_id).execute()
    item["status"] = "completed"
    item["completed"] = iso_now()
    updated = svc.tasks().update(tasklist=tasklist, task=task_id, body=item).execute()
    return {"ok": True, "item": updated}


def tasks_delete(task_id: str, tasklist: str) -> dict:
    svc = service("tasks", "v1", "tasks")
    svc.tasks().delete(tasklist=tasklist, task=task_id).execute()
    return {"ok": True, "deleted": task_id}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Unified Google Workspace tool")
    root = p.add_subparsers(dest="group", required=True)

    cal = root.add_parser("calendar")
    cal_sub = cal.add_subparsers(dest="action", required=True)
    x = cal_sub.add_parser("list")
    x.add_argument("--days", type=int, default=7)
    x.add_argument("--calendar-id", default="primary")
    x = cal_sub.add_parser("create")
    x.add_argument("--title", required=True)
    x.add_argument("--start", required=True)
    x.add_argument("--end", required=True)
    x.add_argument("--description")
    x.add_argument("--calendar-id", default="primary")
    x = cal_sub.add_parser("update")
    x.add_argument("--event-id", required=True)
    x.add_argument("--title")
    x.add_argument("--start")
    x.add_argument("--end")
    x.add_argument("--description")
    x.add_argument("--calendar-id", default="primary")
    x = cal_sub.add_parser("delete")
    x.add_argument("--event-id", required=True)
    x.add_argument("--calendar-id", default="primary")

    gmail = root.add_parser("gmail")
    gmail_sub = gmail.add_subparsers(dest="action", required=True)
    x = gmail_sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--max", type=int, default=10)
    x = gmail_sub.add_parser("read")
    x.add_argument("--message-id", required=True)
    x = gmail_sub.add_parser("draft")
    x.add_argument("--to", required=True)
    x.add_argument("--subject", required=True)
    x.add_argument("--body", required=True)
    x = gmail_sub.add_parser("send")
    x.add_argument("--to", required=True)
    x.add_argument("--subject", required=True)
    x.add_argument("--body", required=True)
    gmail_sub.add_parser("labels")

    sheets = root.add_parser("sheets")
    sheets_sub = sheets.add_subparsers(dest="action", required=True)
    x = sheets_sub.add_parser("read")
    x.add_argument("--spreadsheet-id", required=True)
    x.add_argument("--range", required=True, dest="range_name")
    x = sheets_sub.add_parser("write")
    x.add_argument("--spreadsheet-id", required=True)
    x.add_argument("--range", required=True, dest="range_name")
    x.add_argument("--values", required=True)
    x = sheets_sub.add_parser("append")
    x.add_argument("--spreadsheet-id", required=True)
    x.add_argument("--range", required=True, dest="range_name")
    x.add_argument("--values", required=True)
    x = sheets_sub.add_parser("create")
    x.add_argument("--title", required=True)

    docs = root.add_parser("docs")
    docs_sub = docs.add_subparsers(dest="action", required=True)
    x = docs_sub.add_parser("read")
    x.add_argument("--document-id", required=True)
    x = docs_sub.add_parser("create")
    x.add_argument("--title", required=True)
    x.add_argument("--body")
    x = docs_sub.add_parser("append")
    x.add_argument("--document-id", required=True)
    x.add_argument("--text", required=True)

    drive = root.add_parser("drive")
    drive_sub = drive.add_subparsers(dest="action", required=True)
    x = drive_sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--max", type=int, default=10)
    x = drive_sub.add_parser("download")
    x.add_argument("--file-id", required=True)
    x.add_argument("--output", required=True)
    x = drive_sub.add_parser("upload")
    x.add_argument("--file", required=True)
    x.add_argument("--folder-id")
    x = drive_sub.add_parser("list")
    x.add_argument("--folder-id")
    x.add_argument("--max", type=int, default=25)

    tasks = root.add_parser("tasks")
    tasks_sub = tasks.add_subparsers(dest="action", required=True)
    x = tasks_sub.add_parser("list")
    x.add_argument("--tasklist", default="@default")
    x.add_argument("--max", type=int, default=25)
    x = tasks_sub.add_parser("create")
    x.add_argument("--title", required=True)
    x.add_argument("--notes")
    x.add_argument("--due")
    x.add_argument("--tasklist", default="@default")
    x = tasks_sub.add_parser("complete")
    x.add_argument("--task-id", required=True)
    x.add_argument("--tasklist", default="@default")
    x = tasks_sub.add_parser("delete")
    x.add_argument("--task-id", required=True)
    x.add_argument("--tasklist", default="@default")

    return p


def main() -> None:
    import sys
    args = build_parser().parse_args()
    try:
        _run(args)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


def _run(args) -> None:
    if args.group == "calendar":
        if args.action == "list":
            result = calendar_list(args.days, args.calendar_id)
        elif args.action == "create":
            result = calendar_create(args.title, args.start, args.end, args.description, args.calendar_id)
        elif args.action == "update":
            result = calendar_update(args.event_id, args.calendar_id, args.title, args.start, args.end, args.description)
        else:
            result = calendar_delete(args.event_id, args.calendar_id)
    elif args.group == "gmail":
        if args.action == "search":
            result = gmail_search(args.query, args.max)
        elif args.action == "read":
            result = gmail_read(args.message_id)
        elif args.action == "draft":
            result = gmail_draft(args.to, args.subject, args.body)
        elif args.action == "send":
            result = gmail_send(args.to, args.subject, args.body)
        else:
            result = gmail_labels()
    elif args.group == "sheets":
        if args.action == "read":
            result = sheets_read(args.spreadsheet_id, args.range_name)
        elif args.action == "write":
            result = sheets_write(args.spreadsheet_id, args.range_name, parse_json_values(args.values))
        elif args.action == "append":
            result = sheets_append(args.spreadsheet_id, args.range_name, parse_json_values(args.values))
        else:
            result = sheets_create(args.title)
    elif args.group == "docs":
        if args.action == "read":
            result = docs_read(args.document_id)
        elif args.action == "create":
            result = docs_create(args.title, args.body)
        else:
            result = docs_append(args.document_id, args.text)
    elif args.group == "drive":
        if args.action == "search":
            result = drive_search(args.query, args.max)
        elif args.action == "download":
            result = drive_download(args.file_id, args.output)
        elif args.action == "upload":
            result = drive_upload(args.file, args.folder_id)
        else:
            result = drive_list(args.folder_id, args.max)
    else:
        if args.action == "list":
            result = tasks_list(args.tasklist, args.max)
        elif args.action == "create":
            result = tasks_create(args.title, args.notes, args.due, args.tasklist)
        elif args.action == "complete":
            result = tasks_complete(args.task_id, args.tasklist)
        else:
            result = tasks_delete(args.task_id, args.tasklist)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

