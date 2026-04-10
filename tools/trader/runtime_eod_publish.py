#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import LOCAL_NOTES_DIR
from airtable_client import create_record

WIB = ZoneInfo('Asia/Jakarta')


def load_heartbeat_items() -> list[dict]:
    path = LOCAL_NOTES_DIR / f"summary-30m-{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    if not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        items.extend(row.get('interesting', []))
    return items


def publish(items: list[dict]):
    created = []
    for item in items[:5]:
        fields = {
            'Name': f"Layer 3 heartbeat note - {item['ticker']}",
            'Ticker': item['ticker'],
            'Status': 'High Confidence' if 'strengthening' in item['theme'] else 'Low Confidence',
            'Content': f"Layer 3 heartbeat signal | {item['theme']}: {item['latest']}",
        }
        created.append(create_record('Insights', fields))
    return created


def main():
    items = load_heartbeat_items()
    if not items:
        print('No interesting heartbeat items to publish.')
        return
    created = publish(items)
    print(json.dumps({'published': len(created)}, indent=2))


if __name__ == '__main__':
    main()
