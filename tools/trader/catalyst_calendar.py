"""catalyst_calendar.py — Upcoming corporate events for Superlist tickers.

Pulls earnings, dividends, RUPS, rights issues via api.get_emitten_info() for
each ticker in vault/data/thesis-actions.json (active holds) and today's
universe scan (optional --full flag).

Outputs vault/data/catalyst-YYYY-MM-DD.json:
  [{ticker, date, event_type, note}] — forward 14 days.

Idempotent. Safe to re-run.

Usage:
    python tools/trader/catalyst_calendar.py
    python tools/trader/catalyst_calendar.py --tickers ANTM BBCA AADI
    python tools/trader/catalyst_calendar.py --full   # include full universe
"""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

from api import get_emitten_info

WIB = ZoneInfo("Asia/Jakarta")
VAULT_DATA = Path("/home/lazywork/workspace/vault/data")
log = logging.getLogger(__name__)

FORWARD_DAYS = 14


def _load_active_tickers() -> list[str]:
    """Load tickers from thesis-actions (today's L0 output) + any active thesis."""
    tickers: set[str] = set()

    actions_file = VAULT_DATA / "thesis-actions.json"
    if actions_file.exists():
        try:
            actions = json.loads(actions_file.read_text())
            tickers.update(t.upper() for t in actions)
        except (json.JSONDecodeError, TypeError):
            pass

    thesis_dir = Path("/home/lazywork/workspace/vault/thesis")
    if thesis_dir.exists():
        for p in thesis_dir.glob("*.md"):
            tickers.add(p.stem.upper())

    return sorted(tickers)


def _extract_events(ticker: str, info: dict, today: str, horizon: str) -> list[dict]:
    """Parse emitten_info for relevant upcoming events."""
    events: list[dict] = []

    # Dividend
    ex_div = (info.get("ex_dividend_date") or info.get("dividend_date") or "").strip()
    if ex_div and today <= ex_div <= horizon:
        events.append({"ticker": ticker, "date": ex_div, "event_type": "dividend", "note": f"Ex-dividend date. Yield: {info.get('dividend_yield','?')}"})

    # Rights issue
    rights_date = (info.get("rights_date") or "").strip()
    if rights_date and today <= rights_date <= horizon:
        events.append({"ticker": ticker, "date": rights_date, "event_type": "rights_issue", "note": info.get("rights_note", "")})

    # IPO / public offering
    ipo_date = (info.get("ipo_date") or "").strip()
    if ipo_date and today <= ipo_date <= horizon:
        events.append({"ticker": ticker, "date": ipo_date, "event_type": "ipo", "note": info.get("ipo_note", "")})

    return events


def build(tickers: list[str] | None = None, date: str | None = None) -> list[dict]:
    today = date or datetime.now(WIB).strftime("%Y-%m-%d")
    horizon = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=FORWARD_DAYS)).strftime("%Y-%m-%d")

    if tickers is None:
        tickers = _load_active_tickers()

    log.info(f"Scanning {len(tickers)} tickers for catalysts {today} → {horizon}")
    events: list[dict] = []
    for ticker in tickers:
        try:
            info = get_emitten_info(ticker)
        except Exception as e:
            log.debug(f"{ticker}: emitten_info failed ({e})")
            continue
        events.extend(_extract_events(ticker, info, today, horizon))

    # Sort by date
    events.sort(key=lambda e: e["date"])
    return events


def save(events: list[dict], date: str | None = None) -> Path:
    date = date or datetime.now(WIB).strftime("%Y-%m-%d")
    VAULT_DATA.mkdir(parents=True, exist_ok=True)
    out = VAULT_DATA / f"catalyst-{date}.json"
    out.write_text(json.dumps(events, indent=2, ensure_ascii=False))
    log.info(f"Catalyst calendar saved: {len(events)} events → {out}")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", nargs="*", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--full", action="store_true", help="include full universe")
    args = p.parse_args()

    tickers = [t.upper() for t in args.tickers] if args.tickers else None

    if args.full and not tickers:
        universe_file = VAULT_DATA / f"universe-{args.date or datetime.now(WIB).strftime('%Y-%m-%d')}.json"
        if universe_file.exists():
            univ = json.loads(universe_file.read_text())
            tickers = [u["ticker"] for u in univ]
            log.info(f"Full mode: {len(tickers)} tickers from universe")

    events = build(tickers, args.date)
    path = save(events, args.date)
    print(f"Catalyst calendar: {len(events)} events → {path}")
    for e in events[:5]:
        print(f"  {e['date']} {e['ticker']:6s} {e['event_type']:15s} {e['note'][:50]}")
