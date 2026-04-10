#!/usr/bin/env python3
"""
Stockbit Screening API — Placeholder
======================================
Purpose: Run rule-based stock screens via Stockbit's screening API.
         Returns raw candidate list for Layer 2 analysis.

Status: PLACEHOLDER — Stockbit screening API endpoint TBD.
        Token is fetched from backend API (same as api.py pattern), no local storage needed.

Expected usage:
    from stockbit_screener import run_screen
    candidates = run_screen(filters={
        'min_volume_ratio': 1.5,
        'min_price': 100,
        'max_price': 5000,
        'sectors': ['ENERGY', 'BANKING', 'PROPERTY'],
    })
    # Returns: list of dicts with ticker, price, volume, sector

Token flow (when implemented):
    get_stockbit_token() from api.py → backend /token-store/stockbit → no local cache needed
"""

import logging
import api

log = logging.getLogger(__name__)


def run_screen(filters: dict | None = None) -> list[dict]:
    """
    Run Stockbit screening API with given filters.
    Returns list of candidate tickers.

    Args:
        filters: dict of screening parameters (volume, price, sector, etc.)

    Returns:
        list of dicts: [{ticker, price, volume_ratio, sector, ...}]

    TODO: implement once Stockbit screening API endpoint is provided.
          Use api.get_stockbit_token() for auth — token comes from backend, no local store.
    """
    token = api.get_stockbit_token()  # will raise if unavailable
    log.warning("stockbit_screener: NOT IMPLEMENTED — placeholder only (token: %s)", "ok" if token else "missing")
    return []


def get_screen_filters() -> dict:
    """
    Default screening filters for Layer 2.
    Adjust based on Layer 1 sector/regime output before passing to run_screen().
    """
    return {
        'min_volume_ratio': 1.5,       # volume vs 20-day avg
        'min_price': 50,               # avoid illiquid penny stocks
        'max_price': 50_000,
        'listing_board': ['main', 'development'],
        'sectors': [],                 # empty = all sectors; Layer 1 should narrow this
    }
