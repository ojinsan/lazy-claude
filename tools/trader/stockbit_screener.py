#!/usr/bin/env python3
"""
Stockbit Screening API
======================
Run rule-based stock screens via Stockbit's native screener.
Wraps exodus.stockbit.com/screener/* endpoints exposed in api.py.

Usage:
    from stockbit_screener import run_screen, COMMON_FILTERS
    results = run_screen(filters=COMMON_FILTERS["volume_breakout"])
    # Returns: [{company: {symbol, name}, ...metrics}]

    # Or with raw filter dicts:
    results = run_screen(filters=[
        {"type": "gt", "item1": 2661, "item2": "1.5"},  # volume ratio > 1.5
    ], universe={"scope": "IHSG", "scopeID": "", "name": ""})
"""

import logging
from typing import Optional
import api

log = logging.getLogger(__name__)

# ─── Known metric fitem_ids (from GET /screener/metric) ───────────────────────
# Use get_screener_metrics() to discover more.
FITEM = {
    # Price & volume
    "price":           2661,   # Last price
    "volume":          2662,   # Volume
    # Valuation
    "pe":              2667,   # P/E ratio
    "pb":              2668,   # P/B ratio
    "ps":              2669,   # P/S ratio
    "ev_ebitda":       2674,   # EV/EBITDA
    # Profitability
    "roe":             2676,   # ROE
    "roa":             2677,   # ROA
    "net_margin":      2678,   # Net profit margin
    "gross_margin":    2679,   # Gross margin
    # Growth
    "revenue_growth":  2681,   # Revenue growth YoY
    "eps_growth":      2682,   # EPS growth YoY
    # Size
    "market_cap":      2892,   # Market cap
}

# ─── Pre-built filter sets ─────────────────────────────────────────────────────
COMMON_FILTERS = {
    "volume_breakout": [
        # price 100-10000, use template run for more complex ones
    ],
    "undervalued": [
        {"type": "lt", "item1": FITEM["pe"], "item2": "15"},
        {"type": "lt", "item1": FITEM["pb"], "item2": "1.5"},
        {"type": "gt", "item1": FITEM["roe"], "item2": "10"},
    ],
    "growth": [
        {"type": "gt", "item1": FITEM["revenue_growth"], "item2": "20"},
        {"type": "gt", "item1": FITEM["eps_growth"], "item2": "20"},
        {"type": "gt", "item1": FITEM["roe"], "item2": "15"},
    ],
    "low_pb_roe": [
        {"type": "lt", "item1": FITEM["pb"], "item2": "1"},
        {"type": "gt", "item1": FITEM["roe"], "item2": "12"},
    ],
}

# ─── Universe shortcuts ────────────────────────────────────────────────────────
UNIVERSE = {
    "all":    {"scope": "IHSG", "scopeID": "", "name": ""},
    "lq45":   {"scope": "idx",  "scopeID": "550", "name": "LQ45"},
    "idx30":  {"scope": "idx",  "scopeID": "559", "name": "IDX30"},
    "idx80":  {"scope": "idx",  "scopeID": "551", "name": "IDX80"},
    "idxsmc": {"scope": "idx",  "scopeID": "558", "name": "IDXSmallCap"},
}


def run_screen(
    filters: Optional[list[dict]] = None,
    universe: Optional[dict] = None,
    page: int = 1,
    ordercol: int = 2,
    ordertype: str = "desc",
) -> list[dict]:
    """
    Run a custom Stockbit screen.

    Args:
        filters: List of filter rules. Each:
            {"type": "gt"|"lt"|"eq"|"between",
             "item1": <fitem_id>,
             "item2": <value>,
             "item3": <upper_bound>}  # for "between" only
        universe: Universe dict. Use UNIVERSE shortcuts or get_screener_universe().
        page: Page number (each page ~50 results)
        ordercol: Sort column index
        ordertype: "asc" or "desc"

    Returns:
        list of companies [{company: {symbol, name, exchange}, ...metric values}]
    """
    if filters is None:
        filters = []
    if universe is None:
        universe = UNIVERSE["all"]

    results = api.run_screener_custom(
        filters=filters,
        universe=universe,
        page=page,
        ordercol=ordercol,
        ordertype=ordertype,
    )
    log.info(f"Screener returned {len(results)} results (page {page})")
    return results


def run_template(template_id: int, result_type: str = "TEMPLATE_TYPE_CUSTOM") -> list[dict]:
    """
    Run a saved or preset screener template by ID.

    Get template IDs from:
        api.get_screener_templates()   — your saved templates
        api.get_screener_presets()     — Stockbit preset templates (Guru, Value, etc.)
        api.get_screener_favorites()   — your favorites

    Args:
        template_id: Template numeric ID
        result_type: "TEMPLATE_TYPE_CUSTOM" or "TEMPLATE_TYPE_GURU"
    """
    return api.run_screener_template(template_id, result_type=result_type)


def list_templates() -> list[dict]:
    """List all available screener templates (saved + preset favorites)."""
    return api.get_screener_templates()


def list_presets() -> list[dict]:
    """List Stockbit preset screener categories (Guru, Value, Growth, etc.)."""
    return api.get_screener_presets()


def search_metrics(keyword: str) -> list[dict]:
    """
    Search available screening metrics by name.

    Args:
        keyword: Case-insensitive search string (e.g. "volume", "pe", "roe")

    Returns: Flat list of matching metrics [{fitem_id, fitem_name}]
    """
    all_metrics = api.get_screener_metrics()
    keyword_lower = keyword.lower()
    matches = []
    for group in all_metrics:
        for child in group.get("child", []):
            if keyword_lower in child.get("fitem_name", "").lower():
                matches.append({
                    "fitem_id": child.get("fitem_id"),
                    "fitem_name": child.get("fitem_name"),
                    "group": group.get("fitem_name"),
                })
    return matches
