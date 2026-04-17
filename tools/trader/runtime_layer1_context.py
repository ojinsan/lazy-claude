#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import concurrent.futures
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import RUNTIME
import api
import sys as _sys; _sys.path.insert(0, '/home/lazywork/workspace')
from tools.fund_api import api as _fund_api

WIB = ZoneInfo('Asia/Jakarta')
LAYER1_DIR = RUNTIME / 'notes' / 'layer_1_global_context'
LAYER1_DIR.mkdir(parents=True, exist_ok=True)

THREADS_SCRIPT = Path('/home/lazywork/workspace/tools/general/playwright/threads-scraper.js')
THREADS_QUERIES_BASE = [
    'saham IHSG IDX BEI hari ini',
    'MSCI konglo free float dividen saham Indonesia',
]
MARKET_SYMBOLS_BASE = ['IHSG', 'BBCA', 'BMRI', 'TLKM', 'ANTM', 'ADRO']

PORTFOLIO_STATE_PATH = Path('/home/lazywork/workspace/vault/data/portfolio-state.json')


def load_l0_state() -> dict:
    try:
        return json.loads(PORTFOLIO_STATE_PATH.read_text())
    except Exception:
        return {}


def get_hold_tickers() -> list[str]:
    """Return tickers from current portfolio holdings."""
    state = load_l0_state()
    by_ticker = state.get('exposure', {}).get('by_ticker', [])
    return [h.get('symbol') or h.get('ticker', '') for h in by_ticker if h.get('symbol') or h.get('ticker')]


def build_dynamic_queries(hold_tickers: list[str]) -> list[str]:
    queries = list(THREADS_QUERIES_BASE)
    if hold_tickers:
        # Grouped holding query
        queries.append(' '.join(hold_tickers[:6]) + ' saham hari ini')
        # Per-ticker for top 3 holds
        for t in hold_tickers[:3]:
            queries.append(f'{t} saham hari ini katalis')
    return queries


def build_market_symbols(hold_tickers: list[str]) -> list[str]:
    seen = set(MARKET_SYMBOLS_BASE)
    symbols = list(MARKET_SYMBOLS_BASE)
    for t in hold_tickers:
        if t and t not in seen:
            symbols.append(t)
            seen.add(t)
    return symbols
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


def _run_one_query(query: str, limit: int) -> list[dict]:
    cmd = ['node', str(THREADS_SCRIPT), '--query', query, '--limit', str(limit)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if proc.returncode != 0:
            return []
        # stdout contains progress messages before the JSON blob; find the JSON start
        stdout = proc.stdout
        json_start = stdout.find('{')
        if json_start == -1:
            return []
        data = json.loads(stdout[json_start:])
        return [{'query': query, 'text': r.get('text', '').strip()}
                for r in data.get('results', data.get('captured', []))
                if r.get('text', '').strip()]
    except Exception:
        return []


def run_threads(queries: list[str] | None = None, limit: int = 5) -> dict:
    if queries is None:
        queries = THREADS_QUERIES_BASE

    # Launch all node processes in parallel (Playwright needs real processes, not threads)
    procs = []
    for q in queries:
        cmd = ['node', str(THREADS_SCRIPT), '--query', q, '--limit', str(limit)]
        procs.append((q, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)))

    all_items = []
    seen: set[str] = set()
    import time
    deadline = time.time() + 60
    for query, proc in procs:
        remaining = max(1, deadline - time.time())
        try:
            stdout, _ = proc.communicate(timeout=remaining)
            json_start = stdout.find('{')
            if json_start == -1:
                continue
            data = json.loads(stdout[json_start:])
            for r in data.get('results', data.get('captured', [])):
                txt = r.get('text', '').strip()
                if txt and txt not in seen:
                    seen.add(txt)
                    all_items.append({'query': query, 'text': txt})
        except Exception:
            proc.kill()
            continue

    return {'captured': all_items}


def get_market_snapshot(symbols: list[str] | None = None) -> list[dict]:
    rows = []
    for sym in (symbols or MARKET_SYMBOLS_BASE):
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


def synthesize(snapshot: list[dict], rag_items: list[dict], threads: dict, hold_tickers: list[str] | None = None) -> dict:
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

    # Holding-specific price analysis
    hold_lines = []
    if hold_tickers:
        for t in hold_tickers:
            row = next((x for x in snapshot if x['ticker'] == t), None)
            if row:
                hold_lines.append(f"{t} {row['change']}% @ {row['price']}")

    holding_block = ""
    if hold_lines:
        holding_block = f" Current holds today: {' | '.join(hold_lines)}."

    content = (
        f"Layer 1 global context using Stockbit + RAG + Threads. IHSG regime looks {regime}; "
        f"IHSG {market.get('change')}% @ {market.get('price')}. "
        f"Sector proxy snapshot: {' | '.join(sector_lines) if sector_lines else 'limited sector snapshot'}."
        f"{holding_block} "
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
    today = datetime.now(WIB).strftime('%Y-%m-%d')
    ts_now = datetime.now(WIB).isoformat()
    ids = []
    # Main L1 context → layer_output
    r = _fund_api.post_layer_output({
        'run_date': today, 'layer': 'L1', 'ts': ts_now,
        'summary': payload.get('content', '')[:300],
        'body_md': payload.get('content', ''),
        'severity': 'info', 'tickers': 'IHSG',
    })
    if r: ids.append(str(r.get('id', '')))
    # Threads narratives → signals
    threads_texts = [x.get('text', '') for x in payload.get('threads', {}).get('captured', [])[:2] if x.get('text')]
    for txt in threads_texts:
        r2 = _fund_api.post_signal({
            'ts': ts_now, 'ticker': 'IHSG', 'layer': 'L1',
            'kind': 'narrative_capture', 'severity': 'low',
            'payload_json': json.dumps({'text': txt[:500]}),
        })
        if r2: ids.append(str(r2.get('id', '')))
    return ids


def main():
    hold_tickers = get_hold_tickers()
    symbols = build_market_symbols(hold_tickers)
    queries = build_dynamic_queries(hold_tickers)

    # Run in parallel: snapshot + rag + threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f_snap = pool.submit(get_market_snapshot, symbols)
        f_rag = pool.submit(get_rag_items)
        f_threads = pool.submit(run_threads, queries)
        snapshot = f_snap.result(timeout=60)
        rag_items = f_rag.result(timeout=90)
        threads = f_threads.result(timeout=70)

    payload = synthesize(snapshot, rag_items, threads, hold_tickers)
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
