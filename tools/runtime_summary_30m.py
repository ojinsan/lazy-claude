#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import LOCAL_NOTES_DIR

WIB = ZoneInfo('Asia/Jakarta')


def load_today_notes() -> list[dict]:
    path = LOCAL_NOTES_DIR / f"10m-{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def summarize(rows: list[dict]) -> dict:
    # Rule-based local compression only.
    # Keep this separate from HEARTBEAT.md orchestration and future AI synthesis.

    per_ticker = defaultdict(list)
    for row in rows:
        for rec in row.get('records', []):
            per_ticker[rec.get('ticker', 'UNKNOWN')].append(rec)

    interesting = []
    for ticker, items in per_ticker.items():
        latest = items[-1]
        stances = [i.get('stance') for i in items]
        if stances.count('strengthening') >= 2:
            interesting.append({'ticker': ticker, 'theme': 'repeated strengthening', 'latest': latest.get('summary')})
        elif stances.count('weakening') >= 2:
            interesting.append({'ticker': ticker, 'theme': 'repeated weakening', 'latest': latest.get('summary')})
        elif latest.get('score', 0) != 0:
            interesting.append({'ticker': ticker, 'theme': 'fresh non-neutral change', 'latest': latest.get('summary')})

    return {
        'timestamp': datetime.now(WIB).isoformat(),
        'type': 'layer-3-summary-30m',
        'layer': 'layer_3_stock_overseeing',
        'job': 'summary-30m',
        'interesting': interesting,
    }


def main():
    rows = load_today_notes()
    summary = summarize(rows)
    out = LOCAL_NOTES_DIR / f"heartbeat-{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    with out.open('a') as f:
        f.write(json.dumps(summary, ensure_ascii=False) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
