"""
Vault → Airtable Sync
======================
Light dashboard sync. JSON in vault/data/ stays the source of truth. Airtable
is Boss O's dashboard view.

Tables (must be created manually in Airtable first — this module does NOT
create tables):
- Journal      — 1 row per closed trade (ticker, side, entry, exit, pnl,
                 pnl_pct, attribution, lesson_ref)
- Lessons      — high-severity lessons only (low-severity stays in vault)
- PortfolioLog — 1 row per day (equity, cash, deployed, drawdown, top exposure)

Idempotent via `upsert` against a merge key. Safe to re-run the same day.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import airtable_client
import journal

log = logging.getLogger(__name__)

VAULT_DATA = Path("/home/lazywork/workspace/vault/data")
TRANSACTIONS_FILE = VAULT_DATA / "transactions.json"
LESSONS_FILE = VAULT_DATA / "lessons.json"
STATE_FILE = VAULT_DATA / "portfolio-state.json"

TABLE_JOURNAL = "Journal"
TABLE_LESSONS = "Lessons"
TABLE_PORTFOLIO = "PortfolioLog"

HIGH_SEVERITY = {"high"}


def _table_exists(table: str) -> bool:
    try:
        schema = airtable_client.schema()
    except Exception as exc:
        log.warning(f"Airtable schema fetch failed: {exc}")
        return False
    tables = schema.get("tables", []) if isinstance(schema, dict) else []
    return any(t.get("name") == table for t in tables)


def _sync_journal() -> int:
    if not TRANSACTIONS_FILE.exists():
        return 0
    transactions = json.loads(TRANSACTIONS_FILE.read_text())
    closed = [t for t in transactions if t.get("pnl") is not None]
    count = 0
    for t in closed:
        attr = journal.attribute_trade(t["id"])
        fields = {
            "trade_id": t["id"],
            "ticker": t.get("ticker"),
            "action": t.get("action"),
            "entry_price": t.get("price"),
            "exit_price": t.get("exit_price"),
            "shares": t.get("shares"),
            "pnl": t.get("pnl"),
            "pnl_pct": t.get("pnl_pct"),
            "thesis": t.get("thesis"),
            "conviction": t.get("conviction"),
            "lesson": t.get("lesson") or "",
            "biggest_contributor": attr.get("biggest_contributor", ""),
            "biggest_detractor": attr.get("biggest_detractor", ""),
            "exit_timestamp": t.get("exit_timestamp", ""),
        }
        airtable_client.upsert(TABLE_JOURNAL, fields, merge_on=["trade_id"])
        count += 1
    return count


def _sync_lessons() -> int:
    if not LESSONS_FILE.exists():
        return 0
    lessons = json.loads(LESSONS_FILE.read_text())
    count = 0
    for l in lessons:
        if (l.get("severity") or "medium").lower() not in HIGH_SEVERITY:
            continue
        fields = {
            "lesson_id": l["id"],
            "date": l.get("date"),
            "category": l.get("category"),
            "severity": l.get("severity"),
            "pattern_tag": l.get("pattern_tag") or "",
            "tickers": ", ".join(l.get("tickers") or []),
            "related_thesis": l.get("related_thesis") or "",
            "lesson": l.get("lesson"),
        }
        airtable_client.upsert(TABLE_LESSONS, fields, merge_on=["lesson_id"])
        count += 1
    return count


def _sync_portfolio() -> int:
    if not STATE_FILE.exists():
        return 0
    state = json.loads(STATE_FILE.read_text())
    history = state.get("history", [])
    count = 0
    for row in history:
        fields = {
            "date": row.get("date"),
            "equity": row.get("equity"),
            "cash": row.get("cash"),
            "deployed": row.get("deployed"),
            "utilization_pct": row.get("utilization_pct"),
            "drawdown_pct": row.get("drawdown_pct"),
            "top_exposure": row.get("top_exposure") or "",
        }
        airtable_client.upsert(TABLE_PORTFOLIO, fields, merge_on=["date"])
        count += 1
    return count


SYNCERS = {
    "journal": (_sync_journal, TABLE_JOURNAL),
    "lessons": (_sync_lessons, TABLE_LESSONS),
    "portfolio": (_sync_portfolio, TABLE_PORTFOLIO),
}


def sync_to_airtable(kind: str = "all") -> dict[str, Any]:
    """Push vault data to Airtable.

    kind: "journal" | "lessons" | "portfolio" | "all"
    Returns {kind: count_synced}. Missing tables are skipped with a warning.
    """
    airtable_client.load_env()
    targets = SYNCERS.keys() if kind == "all" else [kind]
    result: dict[str, Any] = {}
    for k in targets:
        syncer, table = SYNCERS[k]
        if not _table_exists(table):
            log.warning(f"Airtable table {table!r} missing — skipping {k} sync")
            result[k] = "table_missing"
            continue
        try:
            result[k] = syncer()
        except Exception as exc:
            log.error(f"{k} sync failed: {exc}")
            result[k] = f"error: {exc}"
    return result


if __name__ == "__main__":
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(json.dumps(sync_to_airtable(kind), indent=2))
