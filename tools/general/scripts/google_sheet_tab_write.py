#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

OUTBOX = Path('/home/lazywork/workspace/tools/general/scripts/google_sheet_write_outbox.jsonl')
OUTBOX.parent.mkdir(parents=True, exist_ok=True)

# NOTE:
# This is a safe local write-intent tool. True public-edit Google Sheet writes need
# a browser/API write path that is not yet implemented in this helper.
# We queue exact write payloads locally so Scarlett can prepare structured sheet writes safely.

def queue_write(payload: dict):
    with OUTBOX.open('a') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    t = sub.add_parser('queue-table')
    t.add_argument('--tab-name', required=True)
    t.add_argument('--json-file', required=True)

    args = ap.parse_args()
    if args.cmd == 'queue-table':
        data = json.loads(Path(args.json_file).read_text())
        payload = {
            'action': 'queue-table',
            'tab_name': args.tab_name,
            'rows': data,
        }
        queue_write(payload)
        print(json.dumps({'queued': True, 'tab_name': args.tab_name, 'rows': len(data)}, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
