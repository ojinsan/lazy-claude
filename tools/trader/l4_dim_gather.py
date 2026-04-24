"""L4 dim gatherers.

Mode A: structure + indicators (ATR, close, 60d high/low).
Mode B: adds orderbook snapshot + last tape note.

All gatherers graceful-degrade: exceptions captured into context_missing list,
partial data returned so the playbook can decide whether to abort.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional


def _sp_to_dict(sp: Any) -> Optional[dict]:
    if sp is None:
        return None
    try:
        return {"price": float(sp.price), "time": getattr(sp, "time", ""), "strength": getattr(sp, "strength", 0)}
    except Exception:
        return None


def gather_structure(
    ticker: str,
    *,
    market_structure_fn: Optional[Callable] = None,
    indicators_fn: Optional[Callable] = None,
) -> dict:
    """Returns merged structure + indicators context.

    Keys:
        structure: {trend, wyckoff_phase, support, resistance, last_swing_low, last_swing_high}
        atr: float | None
        close: float | None
        hi60: float | None
        lo60: float | None
        context_missing: list[str] (error tags)
    """
    missing: list[str] = []
    struct: dict = {}
    if market_structure_fn is None:
        try:
            from tools.trader.market_structure import analyze_market_structure as market_structure_fn  # type: ignore
        except Exception as e:
            missing.append(f"structure_import:{e}")
            market_structure_fn = None
    if market_structure_fn is not None:
        try:
            ms = market_structure_fn(ticker, days=30)
            struct = {
                "trend": getattr(ms, "trend", ""),
                "wyckoff_phase": getattr(ms, "wyckoff_phase", ""),
                "support": getattr(ms, "support", 0),
                "resistance": getattr(ms, "resistance", 0),
                "last_swing_low": _sp_to_dict(getattr(ms, "last_swing_low", None)),
                "last_swing_high": _sp_to_dict(getattr(ms, "last_swing_high", None)),
            }
        except Exception as e:
            missing.append(f"structure:{e}")

    atr = close = hi60 = lo60 = None
    if indicators_fn is None:
        try:
            from tools._lib.api import compute_indicators_from_price_data as indicators_fn  # type: ignore
        except Exception as e:
            missing.append(f"indicators_import:{e}")
            indicators_fn = None
    if indicators_fn is not None:
        try:
            ind = indicators_fn(ticker, timeframe="1d", limit=60)
            if isinstance(ind, dict) and "error" not in ind:
                atr = ind.get("atr_14")
                close = ind.get("close")
                hi60 = ind.get("high_60d")
                lo60 = ind.get("low_60d")
                if hi60 is None and ind.get("highs"):
                    hi60 = max(ind["highs"])
                if lo60 is None and ind.get("lows"):
                    lo60 = min(ind["lows"])
            else:
                missing.append(f"indicators:{ind.get('error') if isinstance(ind, dict) else 'unknown'}")
        except Exception as e:
            missing.append(f"indicators:{e}")

    return {
        "structure": struct,
        "atr": atr,
        "close": close,
        "hi60": hi60,
        "lo60": lo60,
        "context_missing": missing,
    }


def gather_orderbook(ticker: str, orderbook_state_dir: str) -> Optional[dict]:
    """Read latest orderbook snapshot written by L3 cycle. Returns None if missing or corrupt."""
    p = Path(orderbook_state_dir) / f"{ticker}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def gather_last_tape_note(ticker: str, notes_path: str) -> Optional[dict]:
    """Scan jsonl file, return last entry matching ticker. None if no match / missing / empty."""
    p = Path(notes_path)
    if not p.exists():
        return None
    last: Optional[dict] = None
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("ticker") == ticker:
            last = d
    return last
