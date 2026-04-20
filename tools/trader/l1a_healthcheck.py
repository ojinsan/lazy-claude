"""L1-A freshness gate.

Queries fund-manager backend for MAX(occurred_at) of ingested telegram insights.
Used by L1 playbook as a gate: stale scraper → hard abort.
"""
from __future__ import annotations

import datetime as dt
import os

import requests

THRESHOLD_MINUTES = 120
_BASE = os.environ.get("FUND_API_BASE", "http://127.0.0.1:8787")
_TIMEOUT = 5


def _fetch_last_insight_ts() -> str:
    resp = requests.get(f"{_BASE}/api/v1/insights/last", timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json() or {}
    return data.get("last_insight_at") or ""


def _parse_iso(ts: str) -> dt.datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    d = dt.datetime.fromisoformat(ts)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def check() -> dict:
    try:
        ts = _fetch_last_insight_ts()
    except (requests.RequestException, ConnectionError, TimeoutError):
        return {"fresh": False, "last_seen_minutes_ago": None, "threshold_minutes": THRESHOLD_MINUTES}
    if not ts:
        return {"fresh": False, "last_seen_minutes_ago": None, "threshold_minutes": THRESHOLD_MINUTES}
    try:
        last = _parse_iso(ts)
    except (ValueError, TypeError):
        return {"fresh": False, "last_seen_minutes_ago": None, "threshold_minutes": THRESHOLD_MINUTES}
    delta = dt.datetime.now(dt.timezone.utc) - last
    mins = int(delta.total_seconds() // 60)
    return {
        "fresh": mins < THRESHOLD_MINUTES,
        "last_seen_minutes_ago": mins,
        "threshold_minutes": THRESHOLD_MINUTES,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(check(), indent=2))
