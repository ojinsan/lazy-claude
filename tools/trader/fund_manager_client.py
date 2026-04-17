"""
Local fund-manager backend client.
Base URL: http://127.0.0.1:8787 (fund-manager Go service, code/fund-manager/backend)

All functions raise requests.HTTPError on non-2xx. Callers should handle gracefully.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

log = logging.getLogger(__name__)

BASE = os.environ.get("FUND_API_BASE", "http://127.0.0.1:8787")
_TIMEOUT = 10


def _get(path: str, params: dict | None = None) -> list | dict:
    resp = requests.get(f"{BASE}{path}", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, body: dict) -> list | dict:
    resp = requests.post(f"{BASE}{path}", json=body, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ─── Watchlist ────────────────────────────────────────────────────────────────

def get_watchlist(status: Optional[str] = None) -> list[dict]:
    """GET /api/v1/watchlist — merged Lark + local SQLite.
    Each item: {ticker, status, source}
    """
    try:
        data = _get("/api/v1/watchlist", {"status": status} if status else None)
        if isinstance(data, dict):
            return data.get("items", [])
        return data
    except Exception as e:
        log.warning(f"fund_manager_client.get_watchlist failed: {e}")
        return []


def get_holds() -> list[str]:
    """Return list of ticker strings where status='hold'."""
    wl = get_watchlist()
    return [
        w["ticker"].upper()
        for w in wl
        if isinstance(w, dict) and (w.get("status") or "").lower() == "hold"
    ]


def upsert_watchlist(ticker: str, status: str = "active", notes: str = "") -> dict:
    """POST /api/v1/watchlist — local-only addition."""
    try:
        return _post("/api/v1/watchlist", {"ticker": ticker, "status": status, "notes": notes})
    except Exception as e:
        log.warning(f"fund_manager_client.upsert_watchlist failed: {e}")
        return {}


# ─── Insights ─────────────────────────────────────────────────────────────────

def get_positive_candidates(min_confidence: int = 60, days: int = 3) -> list[str]:
    """GET /api/v1/insights/positive-candidates — high-confidence tickers from telegram.
    Returns list of ticker strings.
    """
    try:
        data = _get("/api/v1/insights/positive-candidates",
                    {"min_confidence": min_confidence, "days": days})
        if isinstance(data, list):
            return [c["ticker"].upper() for c in data if c.get("ticker")]
        return []
    except Exception as e:
        log.warning(f"fund_manager_client.get_positive_candidates failed: {e}")
        return []


def rag_search(query: str, limit: int = 20) -> list[dict]:
    """POST /api/v1/rag/search — FTS5 search over telegram insights."""
    try:
        data = _post("/api/v1/rag/search", {"query": query, "limit": limit})
        return data if isinstance(data, list) else []
    except Exception as e:
        log.warning(f"fund_manager_client.rag_search failed: {e}")
        return []


# ─── Thesis ───────────────────────────────────────────────────────────────────

def get_thesis(ticker: str) -> dict:
    try:
        return _get(f"/api/v1/thesis/{ticker.upper()}")
    except Exception as e:
        log.warning(f"fund_manager_client.get_thesis({ticker}) failed: {e}")
        return {}


def upsert_thesis(ticker: str, data: dict) -> dict:
    try:
        return _post(f"/api/v1/thesis/{ticker.upper()}", data)
    except Exception as e:
        log.warning(f"fund_manager_client.upsert_thesis({ticker}) failed: {e}")
        return {}


if __name__ == "__main__":
    import json
    print("watchlist:", json.dumps(get_watchlist(), indent=2)[:300])
    print("holds:", get_holds())
    print("telegram positives:", get_positive_candidates())
