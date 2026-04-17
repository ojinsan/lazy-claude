"""
One-time backfill: reads existing vault/ and runtime/ files and posts to fund-manager API.
Idempotent — relies on upsert. Safe to re-run.

Usage:
    python tools/fund_backfill.py --source all
    python tools/fund_backfill.py --source lessons
    python tools/fund_backfill.py --source portfolio
"""
import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.fund_api import api

log = logging.getLogger("fund_backfill")
logging.basicConfig(level=logging.INFO, format="%(message)s")

VAULT = Path("/home/lazywork/workspace/vault")
RUNTIME = Path("/home/lazywork/workspace/runtime")


def backfill_portfolio():
    state_file = VAULT / "data" / "portfolio-state.json"
    if not state_file.exists():
        log.info("portfolio-state.json not found, skipping")
        return
    state = json.loads(state_file.read_text())
    snap = {
        "date": state.get("date", datetime.now().strftime("%Y-%m-%d")),
        "equity": state.get("total_equity", 0),
        "cash": state.get("cash", 0),
        "deployed": state.get("deployed", 0),
        "utilization": state.get("utilization_pct", 0),
        "drawdown": state.get("drawdown_pct", 0),
        "hwm": state.get("high_water_mark", 0),
        "posture": state.get("posture", ""),
        "raw_json": json.dumps(state),
    }
    r = api.post_portfolio_snapshot(snap)
    log.info(f"portfolio snapshot: {r and 'OK' or 'FAILED'}")


def backfill_transactions():
    tx_file = VAULT / "data" / "transactions.json"
    if not tx_file.exists():
        log.info("transactions.json not found, skipping")
        return
    txs = json.loads(tx_file.read_text())
    ok = 0
    for t in txs:
        r = api.post_transaction({
            "ts": t.get("timestamp", ""),
            "ticker": t.get("ticker", ""),
            "side": t.get("action", "").upper(),
            "shares": t.get("shares", 0),
            "price": t.get("price", 0),
            "value": t.get("value", 0),
            "thesis": t.get("thesis", ""),
            "conviction": t.get("conviction", ""),
            "notes": t.get("notes", ""),
        })
        if r: ok += 1
    log.info(f"transactions: {ok}/{len(txs)} posted")


def backfill_lessons():
    lessons_file = VAULT / "data" / "lessons.json"
    if not lessons_file.exists():
        log.info("lessons.json not found, skipping")
        return
    lessons = json.loads(lessons_file.read_text())
    ok = 0
    for l in lessons:
        r = api.post_lesson({
            "date": l.get("date", ""),
            "category": l.get("category", ""),
            "severity": l.get("severity", "medium"),
            "pattern_tag": l.get("pattern_tag", ""),
            "tickers": ",".join(l.get("tickers") or []),
            "related_thesis": l.get("related_thesis", ""),
            "lesson_text": l.get("lesson", l.get("lesson_text", "")),
        })
        if r: ok += 1
    log.info(f"lessons: {ok}/{len(lessons)} posted")


def backfill_daily_notes():
    daily_dir = VAULT / "daily"
    if not daily_dir.exists():
        return
    count = 0
    for p in sorted(daily_dir.glob("*.md")):
        date = p.stem
        body = p.read_text()
        r = api.put_daily_note(date, body)
        if r: count += 1
    log.info(f"daily notes: {count} posted")


def backfill_thesis():
    thesis_dir = VAULT / "thesis"
    if not thesis_dir.exists():
        return
    count = 0
    for p in sorted(thesis_dir.glob("*.md")):
        ticker = p.stem.upper()
        body = p.read_text()
        r = api.post_thesis({
            "ticker": ticker, "created": datetime.now().strftime("%Y-%m-%d"),
            "layer_origin": "backfill", "status": "active",
            "body_md": body, "updated_at": datetime.now().isoformat(),
        })
        if r: count += 1
    log.info(f"thesis: {count} posted")


def backfill_themes():
    themes_dir = VAULT / "themes"
    if not themes_dir.exists():
        return
    count = 0
    for p in sorted(themes_dir.glob("*.md")):
        slug = p.stem.lower()
        body = p.read_text()
        r = api.post_theme({
            "slug": slug, "name": slug, "created": datetime.now().strftime("%Y-%m-%d"),
            "status": "active", "body_md": body, "updated_at": datetime.now().isoformat(),
        })
        if r: count += 1
    log.info(f"themes: {count} posted")


def backfill_tradeplans():
    plans_dir = RUNTIME / "tradeplans"
    if not plans_dir.exists():
        return
    count = 0
    for p in sorted(plans_dir.glob("*.md")):
        date = p.stem
        body = p.read_text()
        r = api.post_tradeplan({
            "plan_date": date, "ticker": "UNKNOWN", "mode": "full",
            "level": "local", "status": "expired", "raw_md": body,
            "created_at": datetime.now().isoformat(),
        })
        if r: count += 1
    log.info(f"tradeplans: {count} posted")


SOURCES = {
    "portfolio": backfill_portfolio,
    "transactions": backfill_transactions,
    "lessons": backfill_lessons,
    "daily_notes": backfill_daily_notes,
    "thesis": backfill_thesis,
    "themes": backfill_themes,
    "tradeplans": backfill_tradeplans,
}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="all", choices=["all"] + list(SOURCES))
    args = p.parse_args()

    targets = list(SOURCES.values()) if args.source == "all" else [SOURCES[args.source]]
    for fn in targets:
        fn()
    log.info("backfill complete")
