"""relative_strength.py — Rank tickers within a sector by RS vs IHSG.

Computes 5d and 20d return for each ticker relative to IHSG and ranks them.
Used by L2 screening to prefer sector leaders over laggards.

Usage:
    python tools/trader/relative_strength.py --sector energy --days 20
    python tools/trader/relative_strength.py --tickers AADI ADRO PTBA --days 5
    python tools/trader/relative_strength.py --tickers AADI ADMR --days 20
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

from api import get_price_history

WIB = ZoneInfo("Asia/Jakarta")
VAULT_DATA = Path("/home/lazywork/workspace/vault/data")
log = logging.getLogger(__name__)

# Sector → sample watchlist mapping (fallback if universe scan not available)
SECTOR_TICKERS: dict[str, list[str]] = {
    "energy": ["AADI", "ADRO", "PTBA", "ITMG", "ADMR", "BUMI", "DSSA", "SSIA"],
    "banking": ["BBCA", "BBRI", "BBNI", "BMRI", "BNGA", "NISP", "MEGA", "PNBN"],
    "property": ["BSDE", "CTRA", "LPKR", "PWON", "SMRA", "BEST", "APLN"],
    "consumer": ["ICBP", "INDF", "UNVR", "KLBF", "SIDO", "MYOR", "ULTJ"],
    "telecom": ["TLKM", "EXCL", "ISAT"],
    "nickel": ["ANTM", "INCO", "MBMA", "NCKL", "MDKA"],
    "media": ["SCMA", "MNCN", "VIVA"],
    "retail": ["AMRT", "ACES", "MAPI", "LPPF"],
}


def _load_universe_tickers(sector: str) -> list[str]:
    """Load tickers for a sector from today's universe scan, or fall back to SECTOR_TICKERS."""
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    universe_file = VAULT_DATA / f"universe-{today}.json"
    if universe_file.exists():
        try:
            universe = json.loads(universe_file.read_text())
            sector_lower = sector.lower()
            tickers = [
                u["ticker"]
                for u in universe
                if sector_lower in (u.get("sector") or "").lower()
            ]
            if tickers:
                return tickers
        except (json.JSONDecodeError, KeyError):
            pass
    return SECTOR_TICKERS.get(sector.lower(), [])


def _return_pct(price_history: list[dict], days: int) -> float | None:
    """Compute return over last N days from price history list."""
    closes = [c["close"] for c in price_history if c.get("close")]
    if len(closes) < 2:
        return None
    window = closes[-min(days, len(closes)):]
    if len(window) < 2 or window[0] == 0:
        return None
    return ((window[-1] - window[0]) / window[0]) * 100


def rank(tickers: list[str], days: int = 20) -> list[dict]:
    """Rank tickers by RS vs IHSG. Returns sorted list (best first)."""
    # Get IHSG baseline
    try:
        ihsg_hist = get_price_history("IHSG", days=days + 5)
        ihsg_ret = _return_pct(ihsg_hist, days) or 0.0
    except Exception:
        log.warning("IHSG price history failed; using 0 as baseline")
        ihsg_ret = 0.0

    results: list[dict] = []
    for ticker in tickers:
        try:
            hist = get_price_history(ticker, days=days + 5)
            ret = _return_pct(hist, days)
            if ret is None:
                continue
            rs = round(ret - ihsg_ret, 2)
            results.append({
                "ticker": ticker,
                "return_pct": round(ret, 2),
                "ihsg_ret": round(ihsg_ret, 2),
                "rs": rs,
                "days": days,
            })
        except Exception as e:
            log.debug(f"{ticker}: history failed ({e})")

    return sorted(results, key=lambda x: x["rs"], reverse=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--sector", default=None, help="Sector name (energy, banking, etc.)")
    p.add_argument("--tickers", nargs="*", default=None, help="Explicit ticker list")
    p.add_argument("--days", type=int, default=20)
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()

    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    elif args.sector:
        tickers = _load_universe_tickers(args.sector)
        if not tickers:
            print(f"No tickers for sector '{args.sector}'. Known sectors: {', '.join(SECTOR_TICKERS)}")
            sys.exit(1)
    else:
        print("Provide --sector or --tickers")
        sys.exit(1)

    ranked = rank(tickers, args.days)
    print(f"Relative Strength vs IHSG — {args.days}d — {len(ranked)} tickers")
    print(f"{'Rank':<5} {'Ticker':<8} {'Return':>8} {'IHSG':>8} {'RS':>8}")
    print("-" * 40)
    for i, r in enumerate(ranked[:args.top], 1):
        print(f"{i:<5} {r['ticker']:<8} {r['return_pct']:>7.2f}% {r['ihsg_ret']:>7.2f}% {r['rs']:>+8.2f}")
