#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import RUNTIME, WATCHLIST_FILE
import api
import sys as _sys; _sys.path.insert(0, '/home/lazywork/workspace')
from tools.fund_api import api as _fund_api

WIB = ZoneInfo('Asia/Jakarta')
OUTDIR = RUNTIME / 'notes' / 'layer_2_stock_screening'
OUTDIR.mkdir(parents=True, exist_ok=True)
STOCKLIST = Path('/home/lazywork/workspace/tools/data-persistence/stocklist.csv')
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
    """Read today's L1 output. Falls back to yesterday if today's file is missing."""
    from datetime import timedelta
    for delta in (0, 1):  # try today first, then yesterday
        date = (datetime.now(WIB) - timedelta(days=delta)).strftime('%Y-%m-%d')
        path = LAYER1_DIR / f'{date}.jsonl'
        if not path.exists():
            continue
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        if not lines:
            continue
        try:
            return json.loads(lines[-1])
        except Exception:
            continue
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
        holdings = _fund_api.get_holdings()
        for h in holdings:
            ticker = str(h.get('ticker') or '').upper().strip()
            if ticker in valid and ticker not in out and int(h.get('shares', 0)) > 0:
                out.append(ticker)
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out


def get_threads_account_tickers() -> list[str]:
    """Scrape Threads accounts from CSV, extract IDX ticker mentions."""
    import subprocess
    ACCOUNTS_CSV = Path('/home/lazywork/workspace/tools/data-persistence/threads-accounts.csv')
    SCRAPER = Path('/home/lazywork/workspace/tools/general/playwright/threads-scraper.js')
    if not ACCOUNTS_CSV.exists() or not SCRAPER.exists():
        return []
    tickers: list[str] = []
    seen: set[str] = set()
    try:
        with open(ACCOUNTS_CSV) as f:
            reader = csv.DictReader(f)
            handles = [row['handle'].strip() for row in reader if row.get('handle', '').strip() and not row['handle'].startswith('#')]
    except Exception:
        return []
    for handle in handles:
        if not handle:
            continue
        try:
            result = subprocess.run(
                ['node', str(SCRAPER), '--username', handle, '--limit', '8'],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                continue
            # Parse JSON from stdout (scraper prints to stdout)
            payload = json.loads(result.stdout)
            for post in payload.get('results', []):
                text = str(post.get('text') or '').upper()
                for m in TICKER_RE.findall(text):
                    if m not in seen:
                        seen.add(m)
                        tickers.append(m)
        except Exception:
            continue
    return tickers


def candidate_universe() -> tuple[list[str], dict]:
    """Build L2 candidate pool from 4 signal-driven sources. No alphabetical fill."""
    import fund_manager_client as fmc

    # Source 1: holds (always first)
    holds = fmc.get_holds()

    # Source 2: today's L1 output (yesterday fallback if L1 hasn't run yet)
    valid = load_stock_universe()
    layer1 = extract_layer1_candidates(valid)

    # Source 3: telegram positive candidates from local fund-manager backend
    telegram = fmc.get_positive_candidates(min_confidence=60, days=3)

    # Source 4: watchlist from fund-manager (Lark + local SQLite)
    watchlist_raw = fmc.get_watchlist()
    watchlist = [
        w['ticker'].upper() for w in watchlist_raw
        if isinstance(w, dict) and w.get('ticker')
        and (w.get('status') or '').lower() != 'hold'
    ]

    # Merge in priority order, dedup
    ordered: list[str] = []
    seen: set[str] = set()
    for bucket in (holds, layer1, telegram, watchlist):
        for ticker in bucket:
            t = str(ticker or '').upper().strip()
            if t and t not in seen:
                seen.add(t)
                ordered.append(t)

    meta = {
        'holds': len(holds),
        'layer1_today': len(layer1),
        'telegram_positives': len(telegram),
        'watchlist': len(watchlist),
        'total': len(ordered),
        'selection_mode': 'holds→l1_today→telegram→watchlist (no_fill)',
    }
    return ordered, meta


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


def score_holdings_vs_candidates(hold_tickers: list[str], top_candidates: list[dict]) -> dict:
    """Compare current holdings score to top new candidates. Return rotation recommendations."""
    hold_scored = [x for x in (score_ticker(t) for t in hold_tickers) if x]
    hold_scored = sorted(hold_scored, key=lambda x: x['score'])

    # Use 75th percentile of valid candidates (bor < 100) as benchmark — ignore broken tickers
    valid_cands = [c for c in top_candidates if c.get('bor', 0) < 100 and c.get('value', 0) > 1_000_000_000]
    top_score = valid_cands[0]['score'] if valid_cands else (top_candidates[0]['score'] if top_candidates else 0)

    rotations = []
    for h in hold_scored:
        # Flag if: score < 55% of valid market top AND negative/flat momentum AND better liquid alternative exists
        weak = h['score'] < top_score * 0.55
        negative_momentum = h.get('change_pct', 0) < 0
        better = [c for c in valid_cands if c['score'] > h['score'] * 1.3][:2]
        if weak and negative_momentum and better:
            rotations.append({
                'from': h['ticker'],
                'from_score': h['score'],
                'reason': f"score={h['score']:.1f} vs market={top_score:.1f}, momentum={h['change_pct']}%, bor={h['bor']}",
                'to_candidates': [{'ticker': b['ticker'], 'score': b['score']} for b in better],
            })

    keepers = [h for h in hold_scored if h['score'] >= top_score * 0.6]
    return {
        'hold_scored': hold_scored,
        'rotation_candidates': rotations,
        'keepers': [k['ticker'] for k in keepers],
        'top_new_score': top_score,
    }


def main():
    # Load current holdings for rotation analysis
    # Deduplicate: get latest date's holdings only
    all_holdings = _fund_api.get_holdings()
    seen_tickers: set[str] = set()
    hold_tickers: list[str] = []
    for h in all_holdings:
        t = h.get('ticker', '')
        if t and t not in seen_tickers:
            seen_tickers.add(t)
            hold_tickers.append(t)

    tickers, meta = candidate_universe(max_total=120)
    names = [x for x in (score_ticker(c) for c in tickers) if x]
    names = sorted(names, key=lambda x: x['score'], reverse=True)
    top = names[:15]

    # Rotation analysis
    rotation = score_holdings_vs_candidates(hold_tickers, top) if hold_tickers else {}

    payload = {
        'timestamp': datetime.now(WIB).isoformat(),
        'type': 'layer-2-stock-screening',
        'layer': 'layer_2_stock_screening',
        'job': 'layer-2-stock-screening',
        'candidate_meta': meta,
        'candidate_tickers': tickers,
        'scored_count': len(names),
        'top': top,
        'rotation': rotation,
    }
    path = OUTDIR / f"{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    with path.open('a') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    ts_now = datetime.now(WIB).isoformat()

    # Build rotation summary for output
    rot_summary = ""
    if rotation.get('rotation_candidates'):
        rot_lines = [f"{r['from']} → {r['to_candidates'][0]['ticker'] if r['to_candidates'] else 'watch'}" for r in rotation['rotation_candidates']]
        rot_summary = f" | Rotation flags: {', '.join(rot_lines)}"

    # Post layer output summary (includes rotation)
    _fund_api.post_layer_output({
        'run_date': today, 'layer': 'L2', 'ts': ts_now,
        'summary': f"L2 screen: {meta['selected_count']} candidates, top {len(top)} scored{rot_summary}",
        'body_md': json.dumps({'top': top[:10], 'meta': meta, 'rotation': rotation}, indent=2),
        'severity': 'high' if rotation.get('rotation_candidates') else 'info',
        'tickers': ','.join(r['ticker'] for r in top[:10]),
    })

    # Post rotation signals
    for rot in rotation.get('rotation_candidates', []):
        _fund_api.post_signal({
            'ts': ts_now, 'ticker': rot['from'], 'layer': 'L2',
            'kind': 'rotation_candidate',
            'severity': 'high',
            'payload_json': json.dumps(rot),
        })

    # Post new top candidates as signals + watchlist
    for row in top[:5]:
        if row['ticker'] not in hold_tickers:
            _fund_api.post_signal({
                'ts': ts_now, 'ticker': row['ticker'], 'layer': 'L2',
                'kind': 'screening_hit',
                'severity': 'high' if row['score'] >= 15 else 'low',
                'price': row['price'],
                'payload_json': json.dumps({'score': row['score'], 'change_pct': row['change_pct'], 'bor': row['bor'], 'value': row['value']}),
            })
            _fund_api.post_watchlist({
                'ticker': row['ticker'], 'first_added': today,
                'status': 'active', 'conviction': 'high' if row['score'] >= 15 else 'low',
                'updated_at': ts_now,
            })

    print(json.dumps({
        'path': str(path), 'candidate_meta': meta,
        'top5': top[:5],
        'rotation': rotation,
    }, indent=2))

if __name__ == '__main__':
    main()
