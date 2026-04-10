#!/usr/bin/env python3
import argparse
import csv
import io
import json
import re
import sys
from urllib.parse import urlparse, parse_qs
import requests

SHEET_ID = '1k3abGLxjuJiVI27Qqd8LqSXDwePMoj-MG66bloBy2NE'
SHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?usp=sharing'


def gviz_url(gid: str | None = None) -> str:
    base = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json'
    if gid:
        base += f'&gid={gid}'
    return base


def csv_url(gid: str | None = None) -> str:
    base = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'
    if gid:
        base += f'&gid={gid}'
    return base


def parse_gviz(text: str):
    m = re.search(r"google\.visualization\.Query\.setResponse\((.*)\);?\s*$", text, re.S)
    if not m:
        raise ValueError('Could not parse GViz response')
    data = json.loads(m.group(1))
    table = data['table']
    cols = [c.get('label') or c.get('id') or f'col{i}' for i, c in enumerate(table.get('cols', []))]
    rows = []
    for row in table.get('rows', []):
        vals = []
        for cell in row.get('c', []):
            vals.append(None if cell is None else cell.get('v'))
        rows.append(dict(zip(cols, vals)))
    return {'columns': cols, 'rows': rows, 'raw': data}


def list_sheet(gid: str | None = None):
    r = requests.get(gviz_url(gid), timeout=30)
    r.raise_for_status()
    return parse_gviz(r.text)


def export_csv(gid: str | None = None):
    r = requests.get(csv_url(gid), timeout=30)
    r.raise_for_status()
    return r.text


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    l = sub.add_parser('read')
    l.add_argument('--gid', default=None)
    l.add_argument('--limit', type=int, default=20)

    c = sub.add_parser('csv')
    c.add_argument('--gid', default=None)

    args = ap.parse_args()

    if args.cmd == 'read':
        data = list_sheet(args.gid)
        data['rows'] = data['rows'][:args.limit]
        print(json.dumps(data, indent=2, default=str))
    elif args.cmd == 'csv':
        print(export_csv(args.gid))


if __name__ == '__main__':
    main()
