"""overnight_macro.py — Prefetch global market closes at 03:00 WIB.

Fetches overnight US / Asia / commodity / FX data so L1 at 05:00
reads from a local file instead of live-fetching with risk of failure.

Output: vault/data/overnight-YYYY-MM-DD.json

Uses yfinance. Install if missing: pip install yfinance
"""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")
VAULT_DATA = Path("/home/lazywork/workspace/vault/data")

# Symbols to fetch: key → yfinance ticker
SYMBOLS = {
    "sp500":    "^GSPC",
    "nasdaq":   "^IXIC",
    "dow":      "^DJI",
    "vix":      "^VIX",
    "nikkei":   "^N225",
    "hsi":      "^HSI",
    "shanghai": "000001.SS",
    "gold":     "GC=F",
    "oil_wti":  "CL=F",
    "coal_glo": "MTF=F",   # global thermal coal futures
    "usd_idr":  "IDR=X",
    "dxy":      "DX-Y.NYB",
    "us10y":    "^TNX",
}


def fetch_all() -> dict:
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance not installed. Run: pip install yfinance")
        return {"error": "yfinance_missing"}

    results: dict = {}
    now = datetime.now(WIB)
    for key, yf_sym in SYMBOLS.items():
        try:
            t = yf.Ticker(yf_sym)
            # Get 2 days to ensure we get latest close
            hist = t.history(period="2d", interval="1d")
            if hist.empty:
                results[key] = {"error": "no_data", "sym": yf_sym}
                continue
            last_row = hist.iloc[-1]
            prev_row = hist.iloc[-2] if len(hist) >= 2 else last_row
            close = float(last_row["Close"])
            prev_close = float(prev_row["Close"])
            pct = ((close - prev_close) / prev_close * 100) if prev_close else 0
            results[key] = {
                "sym": yf_sym,
                "close": round(close, 4),
                "prev_close": round(prev_close, 4),
                "change_pct": round(pct, 2),
                "date": str(last_row.name.date()),
            }
        except Exception as e:
            log.warning(f"{key} ({yf_sym}): {e}")
            results[key] = {"error": str(e), "sym": yf_sym}

    return results


def save(data: dict, date: str | None = None) -> Path:
    date = date or datetime.now(WIB).strftime("%Y-%m-%d")
    VAULT_DATA.mkdir(parents=True, exist_ok=True)
    out = VAULT_DATA / f"overnight-{date}.json"
    payload = {"fetched_at": datetime.now(WIB).isoformat(), "date": date, "data": data}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    log.info(f"Overnight macro saved → {out}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = fetch_all()
    path = save(data)
    print(f"Overnight macro: {len(data)} instruments → {path}")
    for k, v in data.items():
        if "error" not in v:
            print(f"  {k:10s}  {v['close']:>12.4f}  {v['change_pct']:>+7.2f}%")
        else:
            print(f"  {k:10s}  ERROR: {v.get('error','?')}")
