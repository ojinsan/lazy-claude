"""
Volume-price state classifier (Wyckoff 4-quadrant).
Composes: api.get_candles, api.get_volume_ratio, api.get_avg_volume.
"""
import sys
import json
import argparse
from typing import Literal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tools.trader.api as api

VPState = Literal["healthy_up", "healthy_correction", "weak_rally", "distribution", "indeterminate"]


def classify(ticker: str, timeframe: str = "1d") -> dict:
    """Classify latest candle volume-price state."""
    candles = api.get_candles(ticker, timeframe, limit=22)
    if len(candles) < 2:
        return {"ticker": ticker, "state": "indeterminate", "price_delta_pct": 0.0, "vol_ratio": 0.0, "note": "insufficient data"}

    latest = candles[-1]
    prev = candles[-2]

    close = float(latest.get("close") or latest.get("price", 0))
    prev_close = float(prev.get("close") or prev.get("price", 0))
    price_delta = (close - prev_close) / prev_close * 100 if prev_close else 0.0

    vol_ratio = api.get_volume_ratio(ticker)

    if price_delta >= 0.5 and vol_ratio >= 1.0:
        state: VPState = "healthy_up"
    elif price_delta <= -0.5 and vol_ratio < 1.0:
        state = "healthy_correction"
    elif price_delta >= 0.5 and vol_ratio < 0.8:
        state = "weak_rally"
    elif price_delta <= -0.5 and vol_ratio >= 1.2:
        state = "distribution"
    else:
        state = "indeterminate"

    return {
        "ticker": ticker,
        "state": state,
        "price_delta_pct": round(price_delta, 2),
        "vol_ratio": round(vol_ratio, 2),
        "note": _note(state),
    }


def _note(state: VPState) -> str:
    return {
        "healthy_up": "price up + volume confirms — bullish",
        "healthy_correction": "price down + low volume — healthy pullback",
        "weak_rally": "price up + low volume — no conviction, no chase",
        "distribution": "price down + high volume — exit signal",
        "indeterminate": "ambiguous — wait for confirmation",
    }[state]


def classify_series(ticker: str, days: int = 10) -> list[dict]:
    """Per-day VP classifications for trend continuity."""
    candles = api.get_candles(ticker, "1d", limit=days + 2)
    if len(candles) < 2:
        return []

    avg_vol = api.get_avg_volume(ticker)
    results = []

    for i in range(1, min(days + 1, len(candles))):
        c = candles[i]
        p = candles[i - 1]
        close = float(c.get("close") or c.get("price", 0))
        prev_close = float(p.get("close") or p.get("price", 0))
        price_delta = (close - prev_close) / prev_close * 100 if prev_close else 0.0

        vol = int(c.get("volume", 0))
        vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0

        if price_delta >= 0.5 and vol_ratio >= 1.0:
            state: VPState = "healthy_up"
        elif price_delta <= -0.5 and vol_ratio < 1.0:
            state = "healthy_correction"
        elif price_delta >= 0.5 and vol_ratio < 0.8:
            state = "weak_rally"
        elif price_delta <= -0.5 and vol_ratio >= 1.2:
            state = "distribution"
        else:
            state = "indeterminate"

        results.append({
            "date": c.get("date") or c.get("ts") or f"t-{days - i}",
            "ticker": ticker,
            "state": state,
            "price_delta_pct": round(price_delta, 2),
            "vol_ratio": round(vol_ratio, 2),
        })

    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--series", type=int, default=0, help="days for series mode (0 = single)")
    args = p.parse_args()

    if args.series:
        print(json.dumps(classify_series(args.ticker, args.series), indent=2))
    else:
        print(json.dumps(classify(args.ticker, args.timeframe), indent=2))
