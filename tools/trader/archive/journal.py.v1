"""
Journal & Learning System
==========================
Write, search, and learn from past trades and decisions.

- Daily journal: what happened, what we learned
- Transaction log: every trade with thesis + outcome
- Lesson extraction: searchable lessons by category
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

JOURNAL_DIR = Path("/home/lazywork/lazyboy/trade/journal")
TRANSACTIONS_FILE = JOURNAL_DIR / "transactions.json"
LESSONS_FILE = JOURNAL_DIR / "lessons.json"


# ─── Daily Journal ────────────────────────────────────────────────────────────

def write_journal(content: str, date: Optional[str] = None):
    """Append to daily journal."""
    if date is None:
        date = datetime.now(WIB).strftime("%Y-%m-%d")
    
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    path = JOURNAL_DIR / f"{date}.md"
    
    now = datetime.now(WIB).strftime("%H:%M")
    entry = f"\n### {now}\n{content}\n"
    
    with open(path, "a") as f:
        f.write(entry)
    
    log.info(f"Journal entry written to {path}")


def read_journal(date: Optional[str] = None) -> str:
    """Read daily journal."""
    if date is None:
        date = datetime.now(WIB).strftime("%Y-%m-%d")
    
    path = JOURNAL_DIR / f"{date}.md"
    if path.exists():
        return path.read_text()
    return ""


# ─── Transaction Log ─────────────────────────────────────────────────────────

def log_trade(
    ticker: str,
    action: str,        # "buy" / "sell" / "cut_loss"
    price: float,
    shares: int,
    thesis: str,
    conviction: str = "",
    notes: str = "",
):
    """Log a trade to transactions.json."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    transactions = []
    if TRANSACTIONS_FILE.exists():
        try:
            transactions = json.loads(TRANSACTIONS_FILE.read_text())
        except:
            transactions = []
    
    entry = {
        "id": len(transactions) + 1,
        "timestamp": datetime.now(WIB).isoformat(),
        "ticker": ticker,
        "action": action,
        "price": price,
        "shares": shares,
        "value": price * shares,
        "thesis": thesis,
        "conviction": conviction,
        "notes": notes,
        "pnl": None,            # filled on exit
        "pnl_pct": None,
        "lesson": None,         # filled post-trade review
    }
    
    transactions.append(entry)
    TRANSACTIONS_FILE.write_text(json.dumps(transactions, indent=2, ensure_ascii=False))
    log.info(f"Trade logged: {action} {ticker} @ {price}")
    return entry


def close_trade(trade_id: int, exit_price: float, lesson: str = ""):
    """Close a trade, calculate PnL."""
    if not TRANSACTIONS_FILE.exists():
        return None
    
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    
    for t in transactions:
        if t["id"] == trade_id:
            entry_price = t["price"]
            if t["action"] == "buy":
                t["pnl"] = (exit_price - entry_price) * t["shares"]
                t["pnl_pct"] = ((exit_price - entry_price) / entry_price) * 100
            t["exit_price"] = exit_price
            t["exit_timestamp"] = datetime.now(WIB).isoformat()
            t["lesson"] = lesson
            break
    
    TRANSACTIONS_FILE.write_text(json.dumps(transactions, indent=2, ensure_ascii=False))
    return t


def get_open_positions() -> list[dict]:
    """Get trades that haven't been closed."""
    if not TRANSACTIONS_FILE.exists():
        return []
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    return [t for t in transactions if t.get("exit_price") is None and t["action"] == "buy"]


def get_trade_history(ticker: Optional[str] = None, limit: int = 20) -> list[dict]:
    """Get recent trade history."""
    if not TRANSACTIONS_FILE.exists():
        return []
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    if ticker:
        transactions = [t for t in transactions if t["ticker"] == ticker]
    return transactions[-limit:]


# ─── Lessons ──────────────────────────────────────────────────────────────────

def log_lesson(
    category: str,      # entry_timing, exit_timing, thesis_quality, psychology_read, missed_trade
    lesson: str,
    tickers: list[str] = None,
    date: Optional[str] = None,
):
    """Log a lesson learned."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    lessons = []
    if LESSONS_FILE.exists():
        try:
            lessons = json.loads(LESSONS_FILE.read_text())
        except:
            lessons = []
    
    entry = {
        "id": len(lessons) + 1,
        "date": date or datetime.now(WIB).strftime("%Y-%m-%d"),
        "category": category,
        "lesson": lesson,
        "tickers": tickers or [],
    }
    
    lessons.append(entry)
    LESSONS_FILE.write_text(json.dumps(lessons, indent=2, ensure_ascii=False))
    log.info(f"Lesson logged: [{category}] {lesson[:80]}")


def search_lessons(query: str) -> list[dict]:
    """Simple search through lessons."""
    if not LESSONS_FILE.exists():
        return []
    
    lessons = json.loads(LESSONS_FILE.read_text())
    query_lower = query.lower()
    
    results = []
    for l in lessons:
        if (query_lower in l["lesson"].lower() or
            query_lower in l["category"].lower() or
            any(query_lower in t.lower() for t in l.get("tickers", []))):
            results.append(l)
    
    return results


def get_lessons_by_category(category: str) -> list[dict]:
    """Get all lessons in a category."""
    if not LESSONS_FILE.exists():
        return []
    lessons = json.loads(LESSONS_FILE.read_text())
    return [l for l in lessons if l["category"] == category]


# ─── Trade Review ─────────────────────────────────────────────────────────────

def review_trades(days: int = 30) -> dict:
    """Generate PnL summary for recent period."""
    if not TRANSACTIONS_FILE.exists():
        return {"trades": 0}
    
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    closed = [t for t in transactions if t.get("pnl") is not None]
    
    if not closed:
        return {"trades": 0, "open_positions": len(get_open_positions())}
    
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    
    total_pnl = sum(t["pnl"] for t in closed)
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    
    return {
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(closed) * 100 if closed else 0,
        "total_pnl": total_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        "open_positions": len(get_open_positions()),
    }
