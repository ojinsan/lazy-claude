#!/usr/bin/env python3
"""
Realtime listener (waterseven-data style, lightweight)
- Poll running trade + orderbook deltas
- Persist crossing/flow events for evaluation step and heartbeat
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import api

WIB = ZoneInfo("Asia/Jakarta")
OUT_DIR = Path(__file__).parent.parent.parent / "runtime" / "monitoring" / "realtime"
OUT_FILE = OUT_DIR / "listener_events.jsonl"


def now_iso() -> str:
    return datetime.now(WIB).isoformat()


def append_event(event: dict):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def collect_for_ticker(ticker: str) -> dict:
    rt = api.analyze_running_trades(ticker, limit=120)
    sb_rt = api.get_stockbit_running_trade(ticker, limit=120)
    ob = api.get_orderbook_delta(ticker)

    negotiated = 0
    if isinstance(sb_rt, dict):
        negotiated = int(sb_rt.get("summary", {}).get("negotiated_count", 0))

    return {
        "ts": now_iso(),
        "ticker": ticker,
        "running_trade_pattern": rt.get("pattern", "unknown"),
        "running_trade_interpretation": rt.get("interpretation", ""),
        "crossing_hint": negotiated,
        "orderbook": {
            "bid_withdrawal_detected": ob.get("bid_withdrawal_detected"),
            "offer_pressure_detected": ob.get("offer_pressure_detected"),
            "top_bid_change": ob.get("top_bid_price_change"),
            "top_offer_change": ob.get("top_offer_price_change"),
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", nargs="+", required=True)
    p.add_argument("--interval", type=int, default=30)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()

    tickers = [t.upper() for t in args.tickers]
    while True:
        for t in tickers:
            try:
                evt = collect_for_ticker(t)
                append_event(evt)
                print(f"[{evt['ts']}] {t} pattern={evt['running_trade_pattern']} crossing={evt['crossing_hint']}", flush=True)
            except Exception as e:
                append_event({"ts": now_iso(), "ticker": t, "error": str(e)})

        if args.once:
            break
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
