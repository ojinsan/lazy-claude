#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import LOCAL_NOTES_DIR
import sys as _sys; _sys.path.insert(0, '/home/lazywork/workspace')
from tools.fund_api import api as _fund_api

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
    ts_now = datetime.now(WIB).isoformat()
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    created = []
    for item in items[:5]:
        severity = 'high' if 'strengthening' in item.get('theme', '') else 'low'
        r = _fund_api.post_signal({
            'ts': ts_now, 'ticker': item['ticker'], 'layer': 'L3',
            'kind': 'eod_heartbeat', 'severity': severity,
            'payload_json': json.dumps({'theme': item.get('theme', ''), 'latest': item.get('latest', '')}),
        })
        if r:
            created.append(r)
    # EOD layer output summary
    _fund_api.post_layer_output({
        'run_date': today, 'layer': 'L3', 'ts': ts_now,
        'summary': f"EOD publish: {len(items)} heartbeat items, {len(created)} posted",
        'tickers': ','.join(i['ticker'] for i in items[:5]),
        'severity': 'info',
    })
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
