#!/usr/bin/env python3
"""Compute 20 indicators from OHLCV (open-skills style) with backend fallback."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _lib.api import compute_indicators_from_price_data, get_indicators  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--timeframe", default="1d")
    ap.add_argument("--limit", type=int, default=250)
    args = ap.parse_args()

    t = args.ticker.upper().strip()
    local = compute_indicators_from_price_data(t, timeframe=args.timeframe, limit=args.limit)
    if "error" not in local:
        print(json.dumps({"source": "local_ohlcv", **local}, indent=2, ensure_ascii=False))
        return 0

    backend = get_indicators(t, timeframe=args.timeframe, limit=args.limit)
    print(json.dumps({
        "source": "backend_fallback",
        "local_error": local,
        "backend": backend,
    }, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
