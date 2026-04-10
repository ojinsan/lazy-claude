#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import RUNTIME, WATCHLIST_FILE
import api
from airtable_client import create_record, load_env, list_records

WIB = ZoneInfo('Asia/Jakarta')
OUTDIR = RUNTIME / 'notes' / 'layer_2_stock_screening'
OUTDIR.mkdir(parents=True, exist_ok=True)
STOCKLIST = Path('/home/lazywork/workspace/tools/data-persistance/stocklist.csv')
LAYER1_DIR = RUNTIME / 'notes' / 'layer_1_global_context'
TICKER_RE = re.compile(r'\b[A-Z]{4}\b')


def load_stock_universe() -> set[str]:
    names: set[str] = set()
    with STOCKLIST.open() as f:
        r = csv.DictReader(f)
        for row in r:
            code = (row.get('code') or '').strip().upper()
            board = (row.get('listing_board') or '').strip().lower()
            if code and board in {'main', 'development'}:
                names.add(code)
    return names


def latest_layer1_payload() -> dict:
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    path = LAYER1_DIR / f'{today}.jsonl'
    if not path.exists():
        return {}
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not lines:
        return {}
    try:
        return json.loads(lines[-1])
    except Exception:
        return {}


def extract_layer1_candidates(valid: set[str]) -> list[str]:
    payload = latest_layer1_payload()
    out: list[str] = []

    def add(ticker: str):
        ticker = str(ticker or '').upper().strip()
        if ticker in valid and ticker not in out:
            out.append(ticker)

    for item in payload.get('rag_items', []):
        add(item.get('ticker'))
        for key in ('title', 'summary', 'query'):
            text = str(item.get(key) or '').upper()
            for match in TICKER_RE.findall(text):
                add(match)

    for item in payload.get('sector_snapshot', []):
        add(item.get('ticker'))

    for item in payload.get('threads', {}).get('captured', []):
        text = str(item.get('text') or '').upper()
        for match in TICKER_RE.findall(text):
            add(match)

    return out


def extract_backend_watchlist(valid: set[str], limit: int = 80) -> list[str]:
    out: list[str] = []
    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text())
            if isinstance(data, dict):
                for key in data.keys():
                    ticker = str(key).upper().strip()
                    if ticker in valid and ticker not in out:
                        out.append(ticker)
            elif isinstance(data, list):
                for row in data:
                    ticker = str((row or {}).get('ticker') or '').upper().strip()
                    if ticker in valid and ticker not in out:
                        out.append(ticker)
        except Exception:
            pass

    try:
        data = api._backend_get('/watchlist')
        rows = data.get('data', []) if isinstance(data, dict) else []
        for row in rows:
            ticker = str(row.get('stock') or row.get('ticker') or '').upper().strip()
            if ticker in valid and ticker not in out:
                out.append(ticker)
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out


def extract_hold_priority(valid: set[str], limit: int = 30) -> list[str]:
    out: list[str] = []
    try:
        load_env()
        data = list_records('Superlist', max_records=100)
        for rec in data.get('records', []):
            fields = rec.get('fields', {})
            if fields.get('Status') != 'Hold':
                continue
            ticker = str(fields.get('Ticker') or '').upper().strip()
            if ticker in valid and ticker not in out:
                out.append(ticker)
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out


def candidate_universe(max_total: int = 120) -> tuple[list[str], dict]:
    valid = load_stock_universe()
    hold = extract_hold_priority(valid)
    layer1 = extract_layer1_candidates(valid)
    watchlist = extract_backend_watchlist(valid)

    ordered: list[str] = []
    for bucket in (hold, layer1, watchlist):
        for ticker in bucket:
            if ticker not in ordered:
                ordered.append(ticker)

    if len(ordered) < max_total:
        for ticker in sorted(valid):
            if ticker not in ordered:
                ordered.append(ticker)
            if len(ordered) >= max_total:
                break

    selected = ordered[:max_total]
    meta = {
        'hold_count': len(hold),
        'layer1_count': len(layer1),
        'watchlist_count': len(watchlist),
        'selected_count': len(selected),
        'selection_mode': 'hold_then_layer1_then_watchlist_then_fill',
    }
    return selected, meta


def score_ticker(code: str) -> dict | None:
    ob = api.get_stockbit_orderbook(code)
    if not isinstance(ob, dict) or 'error' in ob or not ob:
        return None
    price = float(ob.get('lastprice') or 0)
    change_pct = float(ob.get('change_percent') or 0)
    value = float(ob.get('value') or 0)
    bid = ob.get('bid', []) or []
    offer = ob.get('offer', []) or []
    bidv = sum(float(x.get('volume', 0) or 0) for x in bid[:5])
    offerv = sum(float(x.get('volume', 0) or 0) for x in offer[:5])
    bor = bidv / offerv if offerv else (999 if bidv else 0)
    score = max(min(change_pct, 8), -8) * 2
    score += min(math.log10(value + 1), 8) * 3 if value > 0 else 0
    score += 6 if bor > 1.5 else 3 if bor > 1.1 else -3 if bor < 0.7 else 0
    return {'ticker': code, 'price': price, 'change_pct': round(change_pct, 2), 'value': value, 'bor': round(bor, 2), 'score': round(score, 2)}


def main():
    load_env()
    tickers, meta = candidate_universe(max_total=120)
    names = [x for x in (score_ticker(c) for c in tickers) if x]
    names = sorted(names, key=lambda x: x['score'], reverse=True)
    top = names[:15]
    payload = {
        'timestamp': datetime.now(WIB).isoformat(),
        'type': 'layer-2-stock-screening',
        'layer': 'layer_2_stock_screening',
        'job': 'layer-2-stock-screening',
        'candidate_meta': meta,
        'candidate_tickers': tickers,
        'scored_count': len(names),
        'top': top,
    }
    path = OUTDIR / f"{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    with path.open('a') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    for row in top[:5]:
        create_record('Insights', {
            'Name': f"Layer 2 screen - {row['ticker']}",
            'Ticker': row['ticker'],
            'Status': 'High Confidence' if row['score'] >= 15 else 'Low Confidence',
            'Content': f"Layer 2 candidate feed. Price {row['price']:.0f}; change {row['change_pct']}%; bid-offer {row['bor']}x; turnover {row['value']:.0f}; score {row['score']}."
        })
    print(json.dumps({'path': str(path), 'candidate_meta': meta, 'top5': top[:5]}, indent=2))

if __name__ == '__main__':
    main()
