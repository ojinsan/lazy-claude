"""universe_scan.py — Daily universe scan for L2 stock screening.

Outputs vault/data/universe-YYYY-MM-DD.json with all liquid IDX tickers.
Idempotent: re-running same day overwrites.

Usage:
    python tools/trader/universe_scan.py
    python tools/trader/universe_scan.py --date 2026-04-17  # override date
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

from api import (
    run_screener_custom,
    get_volume_ratio,
    get_emitten_info,
)

WIB = ZoneInfo("Asia/Jakarta")
VAULT_DATA = Path("/home/lazywork/workspace/vault/data")
log = logging.getLogger(__name__)

# Minimum liquidity filter
MIN_AVG_VOLUME = 500_000          # avg daily volume lots
MIN_PRICE = 50                    # IDR
MAX_PRICE = 50_000                # IDR
MIN_MARKET_CAP_B = 100           # IDR billion (rough filter)


def scan(date: str | None = None) -> list[dict]:
    """Run screener and return [{ticker, last, vol_ratio, sector}] for liquid universe."""
    date = date or datetime.now(WIB).strftime("%Y-%m-%d")

    # Custom screener: price 50–50000, avg vol > 500k lots
    filters = [
        {"key": "last_price", "gte": MIN_PRICE, "lte": MAX_PRICE},
        {"key": "avg_volume_10d", "gte": MIN_AVG_VOLUME},
    ]
    try:
        raw = run_screener_custom(
            filters=filters,
            ordercol=2,       # sort by market cap desc
            ordertype="desc",
        )
    except Exception as e:
        log.warning(f"Screener custom failed ({e}); universe may be empty.")
        raw = []

    results = []
    for item in raw:
        ticker = (item.get("symbol") or item.get("ticker") or "").upper()
        if not ticker:
            continue
        last = float(item.get("last_price") or item.get("last") or 0)
        if last < MIN_PRICE or last > MAX_PRICE:
            continue

        # Try to get sector
        sector = item.get("sector") or item.get("industry") or ""
        if not sector:
            try:
                info = get_emitten_info(ticker)
                sector = info.get("sector") or info.get("industry") or "unknown"
            except Exception:
                sector = "unknown"

        # Vol ratio
        try:
            vr = get_volume_ratio(ticker)
        except Exception:
            vr = 1.0

        results.append({
            "ticker": ticker,
            "last": last,
            "vol_ratio": round(vr, 2),
            "sector": sector,
        })

    return results


def save(results: list[dict], date: str | None = None) -> Path:
    date = date or datetime.now(WIB).strftime("%Y-%m-%d")
    VAULT_DATA.mkdir(parents=True, exist_ok=True)
    out = VAULT_DATA / f"universe-{date}.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    log.info(f"Universe saved: {len(results)} tickers → {out}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=None)
    args = p.parse_args()

    results = scan(args.date)
    path = save(results, args.date)
    print(f"Universe scan complete: {len(results)} tickers → {path}")
    if results:
        print("Sample:", json.dumps(results[:3], ensure_ascii=False))
