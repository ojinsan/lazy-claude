#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import RUNTIME
import api
from airtable_client import create_record, load_env

WIB = ZoneInfo('Asia/Jakarta')
LAYER1_DIR = RUNTIME / 'notes' / 'layer_1_global_context'
LAYER1_DIR.mkdir(parents=True, exist_ok=True)

THREADS_SCRIPT = Path('/home/lazywork/workspace/tools/general/playwright/threads-scraper.js')
THREADS_QUERIES = [
    'saham IHSG IDX BEI',
    'MSCI konglo free float dividen saham Indonesia',
    'BBCA BMRI TLKM ANTM ADRO AKRA AALI saham',
]
MARKET_SYMBOLS = ['IHSG', 'BBCA', 'BMRI', 'TLKM', 'ANTM', 'ADRO', 'AKRA', 'AALI']
RAG_QUERIES = [
    # market regime
    'IHSG hari ini kenapa turun',
    'IDX hari ini sektor apa yang kuat',
    'apa penyebab IHSG melemah hari ini',
    'arus asing IHSG hari ini',
    # sector buckets
    'banking IDX hari ini BMRI BBCA BBRI katalis',
    'energy coal IDX hari ini ADRO PTBA ITMG',
    'nickel EV IDX hari ini ANTM INCO MDKA',
    'consumer rotation IDX hari ini',
    # narrative themes
    'MSCI IDX saham apa yang terdampak',
    'free float MSCI Indonesia saham konglo',
    'dividen saham Maret April Mei IDX',
    'rights issue merger akuisisi saham Indonesia hari ini',
    # active holdings / focus
    'BUMI hari ini kenapa',
    'IMPC hari ini katalis',
    'MDKA hari ini market talk',
    'ADRO hari ini katalis',
    'ANTM hari ini katalis',
    # opportunity hunting
    'saham Indonesia akumulasi asing hari ini',
    'saham Indonesia volume naik tapi belum breakout',
    'broker accumulation saham Indonesia',
]


def run_threads(queries: list[str] = THREADS_QUERIES, limit: int = 6) -> dict:
    all_items = []
    seen = set()
    for query in queries:
        cmd = ['node', str(THREADS_SCRIPT), '--query', query, '--limit', str(limit)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            continue
        try:
            data = json.loads(proc.stdout)
        except Exception:
            continue
        for row in data.get('captured', []):
            txt = row.get('text', '').strip()
            if txt and txt not in seen:
                seen.add(txt)
                all_items.append({'query': query, 'text': txt})
    return {'captured': all_items}


def get_market_snapshot() -> list[dict]:
    rows = []
    for sym in MARKET_SYMBOLS:
        try:
            if sym == 'IHSG':
                ob = api.get_stockbit_index('IHSG')
                chart = api.get_stockbit_chart('IHSG', 'today')
            else:
                ob = api.get_stockbit_orderbook(sym)
                chart = api.get_stockbit_chart(sym, 'today')
            prices = chart.get('prices', []) if isinstance(chart, dict) else []
            last = prices[-1] if prices else {}
            rows.append({
                'ticker': sym,
                'change': ob.get('change_percent') or last.get('percentage') or 0,
                'price': ob.get('lastprice') or last.get('value') or 0,
                'value': ob.get('value') or 0,
            })
        except Exception:
            continue
    return rows


def clean_rag_items(items: list[dict]) -> list[dict]:
    cleaned = []
    seen = set()
    for r in items:
        summary = (r.get('summary') or '').strip()
        label = (r.get('ticker') or r.get('title') or '').strip()
        if not summary:
            continue
        if len(summary) < 40:
            continue
        key = (label, summary[:120])
        if key in seen:
            continue
        seen.add(key)
        theme = 'general'
        low = summary.lower() + ' ' + label.lower()
        if 'msci' in low or 'free float' in low or 'konglo' in low:
            theme = 'msci/free-float'
        elif 'dividen' in low or 'dividend' in low:
            theme = 'dividend'
        elif 'merger' in low or 'akuisisi' in low or 'rights issue' in low:
            theme = 'corporate action'
        elif any(x in low for x in ['bank', 'bbca', 'bmri', 'bbri']):
            theme = 'banking'
        elif any(x in low for x in ['coal', 'adro', 'ptba', 'itmg', 'energy']):
            theme = 'energy/coal'
        elif any(x in low for x in ['nickel', 'mdka', 'antm', 'inco', 'ev']):
            theme = 'nickel/ev'
        cleaned.append({**r, 'theme': theme})
    return cleaned


def get_rag_items() -> list[dict]:
    out = []
    for q in RAG_QUERIES:
        try:
            res = api.rag_search(q, top_n=4, min_confidence=35, max_days=30)
            for r in res[:3]:
                out.append({
                    'query': q,
                    'ticker': r.get('ticker') or '',
                    'title': r.get('title') or r.get('name') or '',
                    'summary': (r.get('summary') or r.get('content') or r.get('text') or '')[:240],
                })
        except Exception:
            continue
    return clean_rag_items(out)


def synthesize(snapshot: list[dict], rag_items: list[dict], threads: dict) -> dict:
    market = next((x for x in snapshot if x['ticker'] == 'IHSG'), {})
    regime = 'mixed'
    try:
        c = float(str(market.get('change', 0)).replace('%', ''))
        if c >= 1:
            regime = 'bullish'
        elif c <= -1:
            regime = 'bearish'
        elif c > 0:
            regime = 'slightly constructive'
        elif c < 0:
            regime = 'slightly defensive'
    except Exception:
        pass

    sector_lines = [f"{x['ticker']} {x['change']}% @ {x['price']}" for x in snapshot if x['ticker'] != 'IHSG']
    threads_texts = [x.get('text', '') for x in threads.get('captured', [])[:5] if x.get('text')]
    rag_hits = [f"{(x['ticker'] or x['title'])} [{x.get('theme','general')}]" for x in rag_items[:8] if x.get('ticker') or x.get('title')]

    narrative_flags = []
    joined = '\n'.join(threads_texts).lower()
    if 'msci' in joined:
        narrative_flags.append('MSCI chatter active')
    if 'konglo' in joined or 'free float' in joined:
        narrative_flags.append('konglo / free-float chatter active')
    if 'dividen' in joined or 'dividend' in joined:
        narrative_flags.append('dividend chatter active')
    if not narrative_flags and threads_texts:
        narrative_flags.append('Threads chatter present but mixed/noisy')
    if not narrative_flags:
        narrative_flags.append('No useful Threads chatter captured')

    content = (
        f"Layer 1 global context using Stockbit + RAG + Threads. IHSG regime looks {regime}; "
        f"IHSG {market.get('change')}% @ {market.get('price')}. "
        f"Sector proxy snapshot: {' | '.join(sector_lines) if sector_lines else 'limited sector snapshot'}. "
        f"Threads narrative: {' | '.join(narrative_flags)}. "
        f"RAG narrative/ticker hits: {', '.join(rag_hits) if rag_hits else 'no strong clean RAG summary yet'}. "
        f"Trading posture: stay selective and prioritize names with aligned narrative + liquidity + tape confirmation."
    )
    return {
        'timestamp': datetime.now(WIB).isoformat(),
        'type': 'layer-1-global-context',
        'layer': 'layer_1_global_context',
        'job': 'layer-1-context-fetch',
        'regime': regime,
        'market': market,
        'sector_snapshot': snapshot,
        'rag_items': rag_items,
        'threads': threads,
        'content': content,
    }


def _safe_jsonable(obj):
    if isinstance(obj, str):
        return obj.encode('utf-8', 'replace').decode('utf-8')
    if isinstance(obj, list):
        return [_safe_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _safe_jsonable(v) for k, v in obj.items()}
    return obj


def save_local(payload: dict) -> Path:
    path = LAYER1_DIR / f"{datetime.now(WIB).strftime('%Y-%m-%d')}.jsonl"
    with path.open('a') as f:
        f.write(json.dumps(_safe_jsonable(payload), ensure_ascii=False) + '\n')
    return path


def publish_airtable(payload: dict) -> list[str]:
    load_env()
    ids = []
    rec = create_record('Insights', {
        'Name': 'Layer 1 context fetch - reusable workflow',
        'Ticker': 'IHSG',
        'Status': 'High Confidence',
        'Content': payload['content'],
    })
    ids.append(rec['id'])
    threads_texts = [x.get('text', '') for x in payload.get('threads', {}).get('captured', [])[:2] if x.get('text')]
    for idx, txt in enumerate(threads_texts, start=1):
        rec2 = create_record('Insights', {
            'Name': f'Threads narrative capture {idx}',
            'Ticker': 'Theme',
            'Status': 'Low Confidence',
            'Content': txt[:1000],
        })
        ids.append(rec2['id'])
    return ids


def main():
    snapshot = get_market_snapshot()
    rag_items = get_rag_items()
    threads = run_threads()
    payload = synthesize(snapshot, rag_items, threads)
    local_path = save_local(payload)
    created = publish_airtable(payload)
    print(json.dumps(_safe_jsonable({
        'local_path': str(local_path),
        'created_ids': created,
        'regime': payload['regime'],
        'market': payload['market'],
        'threads_count': len(payload.get('threads', {}).get('captured', [])),
    }), indent=2, default=str))


if __name__ == '__main__':
    main()
