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
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

VAULT = Path("/home/lazywork/workspace/vault")
DAILY_DIR = VAULT / "daily"
JOURNAL_DIR = VAULT / "journal"
LESSONS_DIR = VAULT / "lessons"
THESIS_DIR = VAULT / "thesis"
DATA_DIR = VAULT / "data"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
LESSONS_FILE = DATA_DIR / "lessons.json"
THESIS_INDEX = DATA_DIR / "thesis-index.json"


# ─── Daily Journal ────────────────────────────────────────────────────────────

def write_journal(content: str, date: Optional[str] = None):
    """Append to daily note (vault/daily/YYYY-MM-DD.md)."""
    if date is None:
        date = datetime.now(WIB).strftime("%Y-%m-%d")

    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    path = DAILY_DIR / f"{date}.md"

    now = datetime.now(WIB).strftime("%H:%M")
    entry = f"\n### {now}\n{content}\n"

    with open(path, "a") as f:
        f.write(entry)

    log.info(f"Daily note written to {path}")


def read_journal(date: Optional[str] = None) -> str:
    """Read daily note (vault/daily/YYYY-MM-DD.md)."""
    if date is None:
        date = datetime.now(WIB).strftime("%Y-%m-%d")

    path = DAILY_DIR / f"{date}.md"
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)

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
    DATA_DIR.mkdir(parents=True, exist_ok=True)

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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:50] or "note"


def _fm_render(fields: dict) -> str:
    """Render Obsidian YAML frontmatter block."""
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            rendered = ", ".join(str(x) for x in v)
            lines.append(f"{k}: [{rendered}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _fm_parse(md_text: str) -> tuple[dict, str]:
    """Extract frontmatter dict + body. Returns ({}, md_text) if no frontmatter."""
    if not md_text.startswith("---\n"):
        return {}, md_text
    end = md_text.find("\n---\n", 4)
    if end < 0:
        return {}, md_text
    raw = md_text[4:end]
    body = md_text[end + 5:]
    fm: dict = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip() for x in v[1:-1].split(",") if x.strip()]
        fm[k.strip()] = v
    return fm, body


# ─── A. Lesson v2 (dual-write: JSON + Obsidian MD) ────────────────────────────

def log_lesson_v2(
    lesson: str,
    category: str,                 # entry_timing|exit_timing|thesis_quality|sizing|psychology|missed_trade|portfolio
    tickers: Optional[list[str]] = None,
    severity: str = "medium",      # low|medium|high
    pattern_tag: Optional[str] = None,
    related_thesis: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    """Log a lesson to both vault/data/lessons.json and vault/lessons/<date>-<slug>.md.

    MD includes frontmatter (category, tickers, severity, pattern_tag, related_thesis)
    and Obsidian-style inline tags for quick filtering.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)

    date = date or datetime.now(WIB).strftime("%Y-%m-%d")
    tickers = tickers or []

    lessons: list[dict] = []
    if LESSONS_FILE.exists():
        try:
            lessons = json.loads(LESSONS_FILE.read_text())
        except json.JSONDecodeError:
            lessons = []

    entry = {
        "id": len(lessons) + 1,
        "date": date,
        "category": category,
        "severity": severity,
        "pattern_tag": pattern_tag,
        "tickers": tickers,
        "related_thesis": related_thesis,
        "lesson": lesson,
    }
    lessons.append(entry)
    LESSONS_FILE.write_text(json.dumps(lessons, indent=2, ensure_ascii=False))

    slug = _slugify(pattern_tag or category)
    md_path = LESSONS_DIR / f"{date}-{slug}-{entry['id']}.md"
    fm = {
        "id": entry["id"],
        "date": date,
        "category": category,
        "severity": severity,
        "pattern_tag": pattern_tag or "",
        "tickers": tickers,
        "related_thesis": related_thesis or "",
    }
    tag_line_parts = [f"#severity/{severity}", f"#category/{category}"]
    if pattern_tag:
        tag_line_parts.append(f"#pattern/{_slugify(pattern_tag)}")
    tag_line_parts += [f"[[{t}]]" for t in tickers]
    related_line = f"Related thesis: [[{related_thesis}]]" if related_thesis else ""
    body = "\n\n".join([
        f"# Lesson {entry['id']} — {pattern_tag or category}",
        " ".join(tag_line_parts),
        lesson,
        related_line,
    ]).strip()
    md_path.write_text(_fm_render(fm) + "\n\n" + body + "\n")
    log.info(f"Lesson v2 logged: [{category}/{severity}] {lesson[:60]}")
    return entry


# ─── B. Pattern Detection ─────────────────────────────────────────────────────

def detect_recurring_mistakes(days: int = 30, min_count: int = 3) -> dict[str, dict]:
    """Group lessons by pattern_tag over the last N days.

    Returns {pattern_tag: {count, tickers, severity_avg, latest_date, lesson_ids}}.
    Only patterns with count >= min_count are returned. Caller (L0 Step 6) alerts
    Boss O via Telegram when anything comes back.
    """
    if not LESSONS_FILE.exists():
        return {}
    lessons = json.loads(LESSONS_FILE.read_text())
    cutoff = (datetime.now(WIB) - timedelta(days=days)).strftime("%Y-%m-%d")
    severity_score = {"low": 1, "medium": 2, "high": 3}

    groups: dict[str, dict] = defaultdict(lambda: {"count": 0, "tickers": set(), "severity_scores": [], "latest_date": "", "lesson_ids": []})
    for row in lessons:
        tag = row.get("pattern_tag")
        if not tag or row.get("date", "") < cutoff:
            continue
        g = groups[tag]
        g["count"] += 1
        for t in row.get("tickers", []):
            g["tickers"].add(t)
        g["severity_scores"].append(severity_score.get(row.get("severity", "medium"), 2))
        if row["date"] > g["latest_date"]:
            g["latest_date"] = row["date"]
        g["lesson_ids"].append(row["id"])

    result: dict[str, dict] = {}
    for tag, g in groups.items():
        if g["count"] < min_count:
            continue
        scores = g["severity_scores"]
        result[tag] = {
            "count": g["count"],
            "tickers": sorted(g["tickers"]),
            "severity_avg": round(sum(scores) / len(scores), 2),
            "latest_date": g["latest_date"],
            "lesson_ids": g["lesson_ids"],
        }
    return result


# ─── C. Per-Trade Attribution ─────────────────────────────────────────────────

def attribute_trade(trade_id: int) -> dict:
    """Score which factors drove the outcome for a closed trade.

    Heuristic: thesis_quality uses conviction vs pnl; entry/exit timing use pnl_pct
    relative to risk bands; sizing uses position size vs capital. Scores are 0.0–1.0.
    """
    if not TRANSACTIONS_FILE.exists():
        return {}
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    trade = next((t for t in transactions if t.get("id") == trade_id), None)
    if not trade or trade.get("pnl") is None:
        return {}

    conviction = (trade.get("conviction") or "").lower()
    pnl_pct = float(trade.get("pnl_pct") or 0)
    was_win = pnl_pct > 0

    conviction_weight = {"high": 0.9, "med": 0.6, "medium": 0.6, "low": 0.3}.get(conviction, 0.5)
    thesis_quality = conviction_weight if was_win else 1 - conviction_weight
    entry_timing = min(1.0, max(0.0, 0.5 + pnl_pct / 20))
    exit_timing = 0.7 if was_win and pnl_pct >= 5 else (0.3 if not was_win and pnl_pct <= -3 else 0.5)
    value = float(trade.get("value") or 0)
    sizing = 0.7 if value > 0 else 0.5

    scores = {
        "thesis_quality": round(thesis_quality, 2),
        "entry_timing": round(entry_timing, 2),
        "exit_timing": round(exit_timing, 2),
        "sizing": round(sizing, 2),
    }
    best = max(scores, key=scores.get)
    worst = min(scores, key=scores.get)
    return {
        **scores,
        "biggest_contributor": best,
        "biggest_detractor": worst,
    }


# ─── D. Confidence Calibration ────────────────────────────────────────────────

def confidence_calibration(days: int = 90) -> dict[str, dict]:
    """Compare predicted conviction vs actual outcome bucket.

    Returns {HIGH|MED|LOW: {trades, predicted_hit_rate, actual_win_rate, drift}}.
    Drift > 0.2 either direction → caller flags in L0 review.
    """
    if not TRANSACTIONS_FILE.exists():
        return {}
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    cutoff = (datetime.now(WIB) - timedelta(days=days)).strftime("%Y-%m-%d")
    predicted = {"high": 0.7, "med": 0.55, "medium": 0.55, "low": 0.4}
    buckets: dict[str, dict] = defaultdict(lambda: {"trades": 0, "wins": 0})
    for t in transactions:
        ts = (t.get("exit_timestamp") or t.get("timestamp") or "")[:10]
        if ts < cutoff or t.get("pnl") is None:
            continue
        conv = (t.get("conviction") or "med").lower()
        key = conv if conv in predicted else "med"
        b = buckets[key]
        b["trades"] += 1
        if float(t["pnl"]) > 0:
            b["wins"] += 1

    result: dict[str, dict] = {}
    for key, b in buckets.items():
        if b["trades"] == 0:
            continue
        actual = b["wins"] / b["trades"]
        pred = predicted.get(key, 0.5)
        result[key.upper()] = {
            "trades": b["trades"],
            "predicted": round(pred, 2),
            "actual_win_rate": round(actual, 2),
            "drift": round(actual - pred, 2),
        }
    return result


# ─── E. Weekly / Monthly Auto-Reviews ─────────────────────────────────────────

def _summarize_period(start: str, end: str) -> dict:
    if not TRANSACTIONS_FILE.exists():
        return {"trades": 0}
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    closed = [t for t in transactions if t.get("pnl") is not None and start <= (t.get("exit_timestamp") or "")[:10] <= end]
    if not closed:
        return {"trades": 0, "start": start, "end": end}
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    r_multiples = [float(t.get("pnl_pct") or 0) for t in closed]
    return {
        "start": start,
        "end": end,
        "trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(closed) * 100, 1),
        "total_pnl": round(sum(t["pnl"] for t in closed), 2),
        "avg_win": round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
        "r_min": round(min(r_multiples), 2),
        "r_max": round(max(r_multiples), 2),
        "top_winners": sorted(wins, key=lambda t: t["pnl"], reverse=True)[:3],
        "top_losers": sorted(losses, key=lambda t: t["pnl"])[:3],
    }


def _render_review_md(title: str, summary: dict, patterns: dict, calibration: dict) -> str:
    lines = [f"# {title}", ""]
    if summary.get("trades", 0) == 0:
        lines.append("No closed trades in this period.")
        return "\n".join(lines) + "\n"
    lines += [
        f"**Period:** {summary['start']} → {summary['end']}",
        f"**Trades:** {summary['trades']} ({summary['wins']}W / {summary['losses']}L, win rate {summary['win_rate']}%)",
        f"**Total PnL:** {summary['total_pnl']}",
        f"**Avg win / loss:** {summary['avg_win']} / {summary['avg_loss']}",
        f"**R-multiple range:** {summary['r_min']}% to {summary['r_max']}%",
        "",
        "## Top 3 Winners",
    ]
    for t in summary["top_winners"]:
        attr = attribute_trade(t["id"])
        lines.append(f"- [[{t['ticker']}]] +{t['pnl']} ({t.get('pnl_pct', 0):.1f}%) — best: {attr.get('biggest_contributor', 'n/a')}")
    lines += ["", "## Top 3 Losers"]
    for t in summary["top_losers"]:
        attr = attribute_trade(t["id"])
        lines.append(f"- [[{t['ticker']}]] {t['pnl']} ({t.get('pnl_pct', 0):.1f}%) — worst: {attr.get('biggest_detractor', 'n/a')}")

    lines += ["", "## Recurring Mistake Patterns"]
    if not patterns:
        lines.append("None with count ≥ 3 this period.")
    else:
        for tag, p in patterns.items():
            lines.append(f"- **{tag}** — {p['count']}×, severity avg {p['severity_avg']}, tickers {p['tickers']}")

    lines += ["", "## Confidence Calibration"]
    if not calibration:
        lines.append("Insufficient data.")
    else:
        for bucket, c in calibration.items():
            flag = " ⚠️ drift > 0.2" if abs(c["drift"]) > 0.2 else ""
            lines.append(f"- **{bucket}** — {c['trades']} trades, predicted {c['predicted']}, actual {c['actual_win_rate']}, drift {c['drift']:+.2f}{flag}")

    return "\n".join(lines) + "\n"


def generate_weekly_review(end_date: Optional[str] = None) -> str:
    """Render weekly review Obsidian MD → vault/reviews/weekly/YYYY-Www.md. Returns MD text."""
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now(WIB)
    start_dt = end_dt - timedelta(days=6)
    start, end = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    iso_year, iso_week, _ = end_dt.isocalendar()
    path = VAULT / "reviews" / "weekly" / f"{iso_year}-W{iso_week:02d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = _summarize_period(start, end)
    patterns = detect_recurring_mistakes(days=7, min_count=2)
    calibration = confidence_calibration(days=7)
    md = _render_review_md(f"Weekly Review — {iso_year}-W{iso_week:02d}", summary, patterns, calibration)
    path.write_text(md)
    log.info(f"Weekly review written to {path}")
    return md


def generate_monthly_review(year: Optional[int] = None, month: Optional[int] = None) -> str:
    """Render monthly review → vault/reviews/monthly/YYYY-MM.md. Returns MD text."""
    now = datetime.now(WIB)
    year = year or now.year
    month = month or now.month
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_dt = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_dt = datetime(year, month + 1, 1) - timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%d")
    path = VAULT / "reviews" / "monthly" / f"{year:04d}-{month:02d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = _summarize_period(start, end)
    patterns = detect_recurring_mistakes(days=31, min_count=3)
    calibration = confidence_calibration(days=31)
    md = _render_review_md(f"Monthly Review — {year:04d}-{month:02d}", summary, patterns, calibration)
    path.write_text(md)
    log.info(f"Monthly review written to {path}")
    return md


# ─── F. Thesis-Aware Queries ──────────────────────────────────────────────────

def get_thesis(ticker: str) -> dict:
    """Read vault/thesis/<TICKER>.md, return {frontmatter: ..., sections: {name: body}}."""
    path = THESIS_DIR / f"{ticker.upper()}.md"
    if not path.exists():
        return {}
    text = path.read_text()
    fm, body = _fm_parse(text)
    sections: dict[str, str] = {}
    current = "_intro"
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    sections[current] = "\n".join(buf).strip()
    return {"ticker": ticker.upper(), "frontmatter": fm, "sections": sections}


def append_thesis_review(ticker: str, layer: str, note: str) -> Path:
    """Append a dated entry under the ## Review Log section of vault/thesis/<TICKER>.md.

    Creates the section if missing. Never overwrites prior entries.
    """
    THESIS_DIR.mkdir(parents=True, exist_ok=True)
    path = THESIS_DIR / f"{ticker.upper()}.md"
    date = datetime.now(WIB).strftime("%Y-%m-%d")
    new_line = f"- {date} ({layer}): {note}"

    if not path.exists():
        fm = _fm_render({
            "ticker": ticker.upper(),
            "created": date,
            "layer_origin": layer,
            "status": "active",
        })
        path.write_text(f"{fm}\n\n# {ticker.upper()}\n\n## Review Log\n{new_line}\n")
        return path

    text = path.read_text()
    if "## Review Log" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n## Review Log\n{new_line}\n"
    else:
        text = text.rstrip() + f"\n{new_line}\n"
    path.write_text(text)
    return path


def thesis_status_summary() -> dict:
    """Scan all vault/thesis/*.md → {active: [...], archived: [...], closed: [...], stale: [...]}.

    Stale = status `active` with no Review Log entry in 7+ days.
    """
    result = {"active": [], "archived": [], "closed": [], "stale": []}
    if not THESIS_DIR.exists():
        return result
    now = datetime.now(WIB)
    for p in sorted(THESIS_DIR.glob("*.md")):
        text = p.read_text()
        fm, body = _fm_parse(text)
        ticker = (fm.get("ticker") or p.stem).upper()
        status = (fm.get("status") or "active").lower()
        bucket = status if status in result else "active"
        result[bucket].append(ticker)

        if status == "active":
            dates = re.findall(r"^- (\d{4}-\d{2}-\d{2})", body, flags=re.MULTILINE)
            if dates:
                try:
                    last = max(datetime.strptime(d, "%Y-%m-%d") for d in dates)
                    if (now.replace(tzinfo=None) - last).days >= 7:
                        result["stale"].append(ticker)
                except ValueError:
                    pass
    return result


# ─── Daily-Note Auto-Append (Phase 5.6 helper) ───────────────────────────────

def append_daily_layer_section(layer: str, content: str, date: Optional[str] = None) -> Path:
    """Append a layer section under `## Auto-Appended` in today's vault/daily/YYYY-MM-DD.md.

    Creates the section the first time. Each call appends `### L{layer} — HH:MM\n{content}\n`.
    """
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    date = date or datetime.now(WIB).strftime("%Y-%m-%d")
    time = datetime.now(WIB).strftime("%H:%M")
    path = DAILY_DIR / f"{date}.md"

    section = f"### L{layer} — {time}\n{content.strip()}\n"
    if not path.exists():
        path.write_text(f"# {date}\n\n## Auto-Appended\n\n{section}\n")
        return path

    text = path.read_text()
    if "## Auto-Appended" not in text:
        if not text.endswith("\n"):
            text += "\n"
        text += f"\n## Auto-Appended\n\n{section}\n"
    else:
        text = text.rstrip() + f"\n\n{section}"
    path.write_text(text)
    return path


# ─── G. Previous-Day Orders (M1.2 Gap 1) ─────────────────────────────────────

def load_previous_orders(days_back: int = 1) -> list[dict]:
    """Return all order rows from the last N trading days (reverse chronological).

    Reads runtime/orders/YYYY-MM-DD.jsonl files. Returns [] if none found.
    """
    from pathlib import Path
    orders_dir = Path("/home/lazywork/workspace/runtime/orders")
    if not orders_dir.exists():
        return []
    results: list[dict] = []
    today = datetime.now(WIB).date()
    for i in range(1, days_back + 2):
        candidate = today - timedelta(days=i)
        p = orders_dir / f"{candidate.strftime('%Y-%m-%d')}.jsonl"
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return results


# ─── H. Thesis-Action State Bus (M1.2 Gap 2) ─────────────────────────────────

THESIS_ACTIONS_FILE = DATA_DIR / "thesis-actions.json"


def set_thesis_action(ticker: str, action: str) -> None:
    """Write per-ticker L0 action to vault/data/thesis-actions.json.

    action in {hold, add-to, reduce, exit-candidate, stale}.
    Idempotent: overwrites existing entry for the same ticker + date.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    date = datetime.now(WIB).strftime("%Y-%m-%d")
    actions: dict = {}
    if THESIS_ACTIONS_FILE.exists():
        try:
            actions = json.loads(THESIS_ACTIONS_FILE.read_text())
        except json.JSONDecodeError:
            actions = {}
    actions[ticker.upper()] = {"action": action, "date": date}
    THESIS_ACTIONS_FILE.write_text(json.dumps(actions, indent=2, ensure_ascii=False))


def get_thesis_actions(date: Optional[str] = None) -> dict[str, str]:
    """Return {ticker: action} for today (or given date). Returns {} if file missing."""
    if not THESIS_ACTIONS_FILE.exists():
        return {}
    try:
        actions = json.loads(THESIS_ACTIONS_FILE.read_text())
    except json.JSONDecodeError:
        return {}
    target = date or datetime.now(WIB).strftime("%Y-%m-%d")
    return {t: v["action"] for t, v in actions.items() if v.get("date") == target}


# ─── I. Intraday Regime (M1.2 Gap 3) ─────────────────────────────────────────

REGIME_INTRADAY_FILE = DATA_DIR / "regime-intraday.json"


def set_intraday_posture(posture: int, reason: str) -> None:
    """Write intraday posture flip to vault/data/regime-intraday.json.

    Called by mid-day regime check at 11:30 and 14:00 WIB.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "posture": posture,
        "reason": reason,
        "ts": datetime.now(WIB).isoformat(),
        "date": datetime.now(WIB).strftime("%Y-%m-%d"),
    }
    REGIME_INTRADAY_FILE.write_text(json.dumps(entry, indent=2, ensure_ascii=False))
    log.info(f"Intraday posture set to {posture}: {reason}")


def get_intraday_posture() -> dict:
    """Return latest intraday posture. {} if not set today."""
    if not REGIME_INTRADAY_FILE.exists():
        return {}
    try:
        entry = json.loads(REGIME_INTRADAY_FILE.read_text())
    except json.JSONDecodeError:
        return {}
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if entry.get("date") != today:
        return {}
    return entry


# ─── J. Kill-Switch (M1.4 §4.4, implemented here for M1.2 Gap 5 order) ──────

def kill_switch_state(days: int = 5) -> dict:
    """Return {'active': bool, 'reason': str}.

    Active if any of:
    - 3+ consecutive losing trades in recent history
    - DD > 10% from HWM (reads vault/data/portfolio-state.json)
    - Same pattern_tag lost 3+ trades in last N days
    """
    active = False
    reasons: list[str] = []

    # Check consecutive losses
    if TRANSACTIONS_FILE.exists():
        try:
            txs = json.loads(TRANSACTIONS_FILE.read_text())
        except json.JSONDecodeError:
            txs = []
        closed = [t for t in txs if t.get("pnl") is not None]
        if len(closed) >= 3:
            last3 = closed[-3:]
            if all(float(t["pnl"]) <= 0 for t in last3):
                active = True
                reasons.append("3 consecutive losing trades")

    # Check DD
    from pathlib import Path
    state_file = DATA_DIR / "portfolio-state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            dd = float(state.get("drawdown_pct") or state.get("drawdown") or 0)
            if dd > 10:
                active = True
                reasons.append(f"drawdown {dd:.1f}% > 10% HWM threshold")
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Check repeating pattern loss
    if LESSONS_FILE.exists():
        try:
            cutoff = (datetime.now(WIB) - timedelta(days=days)).strftime("%Y-%m-%d")
            lessons = json.loads(LESSONS_FILE.read_text())
            pattern_losses: dict[str, int] = defaultdict(int)
            for l in lessons:
                if l.get("date", "") >= cutoff and l.get("severity") in {"medium", "high"} and l.get("pattern_tag"):
                    pattern_losses[l["pattern_tag"]] += 1
            for tag, count in pattern_losses.items():
                if count >= 3:
                    active = True
                    reasons.append(f"pattern '{tag}' repeated {count}× in last {days}d")
        except (json.JSONDecodeError, KeyError):
            pass

    return {"active": active, "reason": "; ".join(reasons) if reasons else "none"}


# ─── K. Per-Dimension Hit Rate (M1.4 §4.1) ────────────────────────────────────

def hit_rate_by(dim: str, days: int = 90) -> list[dict]:
    """Compute hit rate by dimension.

    dim in {sector, pattern_tag, setup, conviction, layer_origin}.
    Returns [{key, trades, wins, win_rate, avg_r, expectancy}] sorted by trades desc.
    """
    if not TRANSACTIONS_FILE.exists():
        return []
    cutoff = (datetime.now(WIB) - timedelta(days=days)).strftime("%Y-%m-%d")
    txs = json.loads(TRANSACTIONS_FILE.read_text())
    closed = [t for t in txs if t.get("pnl") is not None and (t.get("exit_timestamp") or "")[:10] >= cutoff]

    dim_map = {
        "conviction": lambda t: (t.get("conviction") or "unknown").lower(),
        "layer_origin": lambda t: t.get("notes", ""),  # notes may contain layer tag
    }
    get_key = dim_map.get(dim, lambda t: t.get(dim, "unknown"))

    buckets: dict[str, dict] = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl_pcts": []})
    for t in closed:
        key = str(get_key(t) or "unknown")
        b = buckets[key]
        b["trades"] += 1
        if float(t["pnl"]) > 0:
            b["wins"] += 1
        b["pnl_pcts"].append(float(t.get("pnl_pct") or 0))

    result = []
    for key, b in buckets.items():
        if b["trades"] == 0:
            continue
        win_rate = b["wins"] / b["trades"]
        avg_r = sum(b["pnl_pcts"]) / len(b["pnl_pcts"]) if b["pnl_pcts"] else 0
        losses = b["trades"] - b["wins"]
        avg_loss = sum(x for x in b["pnl_pcts"] if x < 0) / losses if losses else -1
        expectancy = win_rate * avg_r + (1 - win_rate) * avg_loss
        result.append({
            "key": key,
            "trades": b["trades"],
            "wins": b["wins"],
            "win_rate": round(win_rate, 3),
            "avg_r": round(avg_r, 2),
            "expectancy": round(expectancy, 2),
        })
    return sorted(result, key=lambda x: x["trades"], reverse=True)


# ─── L. Auto-Lesson Suggestion on Close (M1.4 §4.2) ──────────────────────────

def _draft_lesson_from_close(trade: dict, pnl_pct: float) -> dict:
    """Return a suggested lesson dict for a just-closed trade. Caller confirms + calls log_lesson_v2."""
    if pnl_pct < -5:
        return {"category": "exit_timing", "severity": "high", "pattern_tag": "stop-hit", "lesson_text": f"Loss of {pnl_pct:.1f}%. Review why stop was hit — thesis break, fake support, or poor entry?"}
    if pnl_pct > 10:
        return {"category": "thesis_quality", "severity": "low", "pattern_tag": "thesis-confirmed", "lesson_text": f"Win of {pnl_pct:.1f}%. Record what worked — narrative, broker flow, timing."}
    if abs(pnl_pct) <= 2:
        return {"category": "psychology", "severity": "low", "pattern_tag": "indecision-exit", "lesson_text": f"Exit at {pnl_pct:.1f}% — near-zero result. Was this premature, or disciplined stop?"}
    if pnl_pct > 0:
        return {"category": "exit_timing", "severity": "low", "pattern_tag": "early-exit", "lesson_text": f"Win of {pnl_pct:.1f}%. Did we leave significant upside? Check T2 vs actual exit."}
    return {"category": "exit_timing", "severity": "medium", "pattern_tag": "managed-loss", "lesson_text": f"Managed loss {pnl_pct:.1f}%. Was the thesis wrong or just timing?"}


# ─── CLI Entry Points ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "stale":
        summary = thesis_status_summary()
        print(json.dumps(summary["stale"], indent=2, ensure_ascii=False))

    elif cmd == "kill-switch":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        print(json.dumps(kill_switch_state(days), indent=2, ensure_ascii=False))

    elif cmd == "hit-rate":
        dim = sys.argv[2] if len(sys.argv) > 2 else "conviction"
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 90
        print(json.dumps(hit_rate_by(dim, days), indent=2, ensure_ascii=False))

    elif cmd == "calibration":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        print(json.dumps(confidence_calibration(days), indent=2, ensure_ascii=False))

    elif cmd == "thesis-actions":
        print(json.dumps(get_thesis_actions(), indent=2, ensure_ascii=False))

    elif cmd == "intraday-posture":
        print(json.dumps(get_intraday_posture(), indent=2, ensure_ascii=False))

    elif cmd == "weekly":
        print(generate_weekly_review())

    elif cmd == "monthly":
        print(generate_monthly_review())

    else:
        print("Commands: stale | kill-switch [days] | hit-rate [dim] [days] | calibration [days] | thesis-actions | intraday-posture | weekly | monthly")
