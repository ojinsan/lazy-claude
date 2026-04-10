#!/usr/bin/env python3
import argparse
import json
import os
from typing import List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_service():
    key_path = os.path.expanduser('/home/lazywork/workspace-sheets-key.json')
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)


def get_sheet_id_map(service, spreadsheet_id):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s['properties']['title']: s['properties']['sheetId'] for s in meta.get('sheets', [])}


def ensure_sheet(service, spreadsheet_id: str, title: str):
    mapping = get_sheet_id_map(service, spreadsheet_id)
    if title in mapping:
        return {'created': False, 'sheetId': mapping[title], 'title': title}
    body = {'requests': [{'addSheet': {'properties': {'title': title}}}]}
    resp = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    reply = resp['replies'][0]['addSheet']['properties']
    return {'created': True, 'sheetId': reply['sheetId'], 'title': reply['title']}


def write_values(service, spreadsheet_id: str, tab_name: str, rows: List[List[str]]):
    rng = f"{tab_name}!A1"
    body = {'values': rows}
    return service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=rng,
        valueInputOption='RAW',
        body=body,
    ).execute()


def clear_values(service, spreadsheet_id: str, tab_name: str):
    return service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=tab_name,
        body={},
    ).execute()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('ensure-sheet')
    p1.add_argument('--spreadsheet-id', required=True)
    p1.add_argument('--tab-name', required=True)

    p2 = sub.add_parser('write-table')
    p2.add_argument('--spreadsheet-id', required=True)
    p2.add_argument('--tab-name', required=True)
    p2.add_argument('--json-file', required=True)
    p2.add_argument('--clear-first', action='store_true')

    args = ap.parse_args()
    service = get_service()

    try:
        if args.cmd == 'ensure-sheet':
            print(json.dumps(ensure_sheet(service, args.spreadsheet_id, args.tab_name), indent=2, ensure_ascii=False))
            return

        if args.cmd == 'write-table':
            ensure = ensure_sheet(service, args.spreadsheet_id, args.tab_name)
            data = json.load(open(args.json_file, 'r', encoding='utf-8'))
            headers = list(data[0].keys()) if data else []
            rows = [headers] + [[row.get(h, '') for h in headers] for row in data]
            if args.clear_first:
                clear_values(service, args.spreadsheet_id, args.tab_name)
            resp = write_values(service, args.spreadsheet_id, args.tab_name, rows)
            print(json.dumps({'sheet': ensure, 'updated': resp}, indent=2, ensure_ascii=False))
            return
    except HttpError as e:
        print(json.dumps({'error': str(e)}, indent=2, ensure_ascii=False))
        raise


if __name__ == '__main__':
    main()
