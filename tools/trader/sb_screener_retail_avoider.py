#!/usr/bin/env python3
"""Retail-avoider broker-flow screener.

Compares retail-broker net flow vs. smart-money (big foreign/institutional)
net flow for a given day. Flags tickers where retail is NET SELLING while
smart money is NET BUYING — the classic "crowd dump" contrarian signal.

Uses Stockbit `/order-trade/broker/activity` aggregated by broker-code list.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api

RETAIL_CODES = ["PD", "XL", "YP", "XC", "NI", "DP", "FS", "GA"]
SMART_CODES = ["CG", "CS", "RG", "CC", "DX", "ZP", "AK", "KZ"]


def fetch_broker_activity(broker_codes: list[str], date: Optional[str] = None) -> dict:
    """Live Stockbit fetch aggregating across broker_codes for a single date.

    Stockbit rejects comma-joined broker_code — must use repeated query params
    (`broker_code=PD&broker_code=XL&...`). httpx accepts list-of-tuples.
    """
    params: list[tuple[str, str]] = [("broker_code", c) for c in broker_codes]
    if date:
        params.append(("from", date))
        params.append(("to", date))
    return api._stockbit_get("/order-trade/broker/activity", params)


def parse_nets(raw: dict) -> tuple[str, dict[str, float]]:
    """Extract (date, {ticker: net_value}) from a broker-activity response.

    Stockbit live API returns POSITIVE values in both brokers_buy and
    brokers_sell (the bucket name encodes side). Net = sum(buy) - sum(sell).
    The fixture file kept pre-signed values — both shapes tolerated by
    treating brokers_sell as contributing negatively regardless of sign.
    """
    data = (raw or {}).get("data") or {}
    bat = data.get("broker_activity_transaction") or {}
    buy = bat.get("brokers_buy") or []
    sell = bat.get("brokers_sell") or []
    nets: dict[str, float] = {}
    for row in buy:
        code = row.get("stock_code")
        val = row.get("value")
        if not code or val is None:
            continue
        nets[code] = nets.get(code, 0) + abs(float(val))
    for row in sell:
        code = row.get("stock_code")
        val = row.get("value")
        if not code or val is None:
            continue
        nets[code] = nets.get(code, 0) - abs(float(val))
    date = data.get("from") or data.get("to") or ""
    return date, nets


def compute_retail_avoider(retail_raw: dict, smart_raw: dict) -> dict:
    """Join retail (net < 0) ∩ smart (net > 0). Returns sorted by ratio desc."""
    date, retail = parse_nets(retail_raw)
    _, smart = parse_nets(smart_raw)
    rows: list[dict] = []
    for ticker, rnet in retail.items():
        if rnet >= 0:
            continue
        snet = smart.get(ticker, 0)
        if snet <= 0:
            continue
        retail_sell = -rnet
        ratio = snet / retail_sell if retail_sell else 0.0
        rows.append({
            "ticker": ticker,
            "retail_net_sell": round(retail_sell, 2),
            "smart_net_buy": round(snet, 2),
            "ratio": round(ratio, 4),
        })
    rows.sort(key=lambda r: r["ratio"], reverse=True)
    return {"date": date, "tickers": rows}


def run(date: Optional[str] = None) -> dict:
    retail_raw = fetch_broker_activity(RETAIL_CODES, date)
    smart_raw = fetch_broker_activity(SMART_CODES, date)
    return compute_retail_avoider(retail_raw, smart_raw)


def main() -> None:
    p = argparse.ArgumentParser(description="Retail-avoider broker-flow screener")
    p.add_argument("--date", help="YYYY-MM-DD (defaults to latest)")
    p.add_argument("--top", type=int, default=5, help="Limit output rows")
    args = p.parse_args()
    out = run(date=args.date)
    out["tickers"] = out["tickers"][: args.top]
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
