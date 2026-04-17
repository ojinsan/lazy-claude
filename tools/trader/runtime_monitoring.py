#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from config import LOCAL_NOTES_DIR, WATCHLIST_FILE, load_env
import time
import api
import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.fund_api import api as _fund_api

WIB = ZoneInfo('Asia/Jakarta')


def load_hold_tickers(limit: int = 5) -> list[str]:
    # Read from fund-manager API (portfolio holdings)
    try:
        today = datetime.now(WIB).strftime("%Y-%m-%d")
        holdings = _fund_api.get_holdings(date=today)
        if not holdings:
            # Try latest available date
            holdings = _fund_api.get_holdings()
        out = [h["ticker"] for h in holdings if h.get("shares", 0) > 0]
        return out[:limit]
    except Exception:
        return []


def load_watchlist_tickers(limit: int = 8) -> list[str]:
    # 1) local active watchlist
    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text())
            if isinstance(data, dict):
                vals = [k.upper() for k in data.keys() if not str(k).startswith('_')][:limit]
                if vals:
                    return vals
            if isinstance(data, list):
                out = []
                for row in data:
                    if isinstance(row, dict) and row.get('ticker'):
                        out.append(str(row['ticker']).upper())
                if out:
                    return out[:limit]
        except Exception:
            pass
    # 2) backend watchlist fallback
    try:
        data = api._backend_get('/watchlist')
        rows = data.get('data', []) if isinstance(data, dict) else []
        out = []
        for row in rows:
            ticker = (row.get('stock') or row.get('ticker') or '').upper()
            if ticker and ticker not in out:
                out.append(ticker)
            if len(out) >= limit:
                break
        if out:
            return out
    except Exception:
        pass
    return []


def summarize_ticker(ticker: str, include_running_trade: bool = True) -> dict:
    ob = api.get_orderbook_delta(ticker)
    rt = api.get_stockbit_running_trade(ticker, mode='realtime', limit=40) if include_running_trade else {}

    summary_bits = []
    score = 0

    if isinstance(ob, dict) and 'error' not in ob:
        pressure = ob.get('pressure_side', 'balanced')
        bor = ob.get('bid_offer_value_ratio', 0)
        dominance = ob.get('dominance', 'neutral')

        if pressure == 'buyers':
            summary_bits.append(f'buyer pressure ({bor:.2f}x)')
            score += 1
        elif pressure == 'sellers':
            summary_bits.append(f'seller pressure ({bor:.2f}x)')
            score -= 1

        # Strong dominance signals (learned from VKTR/IMPC case study)
        if dominance in ('extreme_bid', 'strong_bid'):
            summary_bits.append(f'dominance={dominance}')
            score += 2  # much stronger signal
        elif dominance in ('extreme_offer', 'strong_offer'):
            summary_bits.append(f'dominance={dominance}')
            score -= 2

        # Whale tick detection (lots-per-frequency analysis)
        bid_whale = ob.get('bid_whale_ticks', [])
        offer_whale = ob.get('offer_whale_ticks', [])
        if bid_whale:
            top_whale = max(bid_whale, key=lambda x: x.get('lots_per_order', 0))
            summary_bits.append(f'{len(bid_whale)} whale bid ticks (max {top_whale["lots_per_order"]} lots/order at {top_whale["price"]})')
            score += 1
        if offer_whale:
            top_whale = max(offer_whale, key=lambda x: x.get('lots_per_order', 0))
            summary_bits.append(f'{len(offer_whale)} whale offer ticks (max {top_whale["lots_per_order"]} lots/order at {top_whale["price"]})')
            score -= 1

        # Bid depth shape
        bid_shape = ob.get('bid_depth_shape', '')
        if bid_shape == 'spread' and dominance in ('extreme_bid', 'strong_bid', 'moderate_bid'):
            summary_bits.append('spread bid support')
            score += 1

        # Manipulation pattern detection
        manipulation_setup = ob.get('manipulation_setup')
        contested_tape = ob.get('contested_tape')
        wick_shakeout = ob.get('wick_shakeout')
        if manipulation_setup == 'accumulation_setup':
            summary_bits.append('ACCUMULATION SETUP: offer wall trap + whale bids')
            score += 3
        elif manipulation_setup == 'distribution_setup':
            summary_bits.append('DISTRIBUTION SETUP: bid wall trap + whale offers')
            score -= 3
        if contested_tape == 'controlled_bid_support':
            summary_bits.append('CONTESTED TAPE: strong bid support despite whale offers')
            score += 1
        if wick_shakeout == 'shakeout_with_accumulation':
            summary_bits.append('WICK SHAKEOUT: price dip but whale bids hold')
            score += 2
        elif wick_shakeout == 'shakeout_trap':
            summary_bits.append('SHAKEOUT TRAP: engineered dip + whale accumulation')
            score += 2

        if ob.get('new_large_offers'):
            summary_bits.append(f"{len(ob['new_large_offers'])} new large offers")
            score -= 1
        if ob.get('withdrawn_offers'):
            summary_bits.append(f"{len(ob['withdrawn_offers'])} offers withdrawn")
            score += 1
        if ob.get('new_large_bids'):
            summary_bits.append(f"{len(ob['new_large_bids'])} new large bids")
            score += 1
        if ob.get('withdrawn_bids'):
            summary_bits.append(f"{len(ob['withdrawn_bids'])} bids withdrawn")
            score -= 1

    rt_count = 0
    if isinstance(rt, dict) and 'error' not in rt:
        trades = rt.get('running_trade', []) if isinstance(rt.get('running_trade', []), list) else []
        rt_count = len(trades)
        if rt_count:
            summary_bits.append(f'{rt_count} recent trades observed')

    if score >= 4:
        stance = 'strong_accumulation'  # extreme signal like IMPC 3.6:1 + whale ticks
    elif score >= 2:
        stance = 'strengthening'
    elif score <= -4:
        stance = 'strong_distribution'
    elif score <= -2:
        stance = 'weakening'
    else:
        stance = 'mixed'

    if not summary_bits:
        summary_bits.append('no meaningful microstructure change detected')

    return {
        'ticker': ticker,
        'stance': stance,
        'score': score,
        'summary': '; '.join(summary_bits),
        'orderbook': ob,
        'running_trade_count': rt_count,
    }


def write_note(records: list[dict]):
    now = datetime.now(WIB)
    LOCAL_NOTES_DIR.mkdir(parents=True, exist_ok=True)
    path = LOCAL_NOTES_DIR / f"10m-{now.strftime('%Y-%m-%d')}.jsonl"
    payload = {
        'timestamp': now.isoformat(),
        'type': 'layer-3-stock-overseeing',
        'layer': 'layer_3_stock_overseeing',
        'job': 'intraday-10m-review',
        'records': records,
    }
    with path.open('a') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    print(path)


def main():
    load_env()
    hold_tickers = load_hold_tickers(limit=5)
    watchlist_tickers = load_watchlist_tickers(limit=8)
    tickers = []
    for t in hold_tickers + watchlist_tickers:
        if t not in tickers:
            tickers.append(t)
    if not tickers:
        tickers = ['BBCA', 'ASII', 'TLKM']
    records = []
    hold_count = len(hold_tickers)
    for i, t in enumerate(tickers):
        # prioritize Hold names first for running-trade access; degrade lower-priority names first
        include_rt = i < min(max(hold_count, 2), 4)
        records.append(summarize_ticker(t, include_running_trade=include_rt))
        if i < len(tickers) - 1:
            time.sleep(0.55)
    write_note(records)
    compact = [f"{r['ticker']}: {r['stance']} ({r['summary']})" for r in records]
    print('\n'.join(compact))

    # M3.7: auto-trigger check per ticker
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.trader.tape_runner import snapshot as tape_snapshot
        from tools.trader.auto_trigger import should_trigger, trigger
        for r in records:
            t = r["ticker"]
            try:
                tape = tape_snapshot(t)
                ok, reason = should_trigger(t, tape.composite)
                if ok:
                    trigger(t, tape.composite, {"stance": r["stance"], "summary": r["summary"]})
            except Exception:
                pass
    except Exception:
        pass


if __name__ == '__main__':
    main()
