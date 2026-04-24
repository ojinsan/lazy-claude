"""L4 pure helpers: IDX tick math, sizing, prompt builders, parsers, formatters.

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md.
"""
from __future__ import annotations

import json as _json
import math
from typing import Literal

Side = Literal["buy", "sell"]
Role = Literal["entry", "stop", "tp"]


def get_tick(price: float) -> int:
    """IDX fraksi harga. Raises for negative prices."""
    p = float(price)
    if p < 0:
        raise ValueError(f"negative price: {p}")
    if p < 200:
        return 1
    if p < 500:
        return 2
    if p < 2000:
        return 5
    if p < 5000:
        return 10
    return 25


def round_to_tick(price: float, side: Side, role: Role) -> int:
    """Round price to IDX tick with conservative-fill bias by side/role.

    buy  → entry down, stop down, tp up
    sell → entry up,   stop up,   tp down
    """
    t = get_tick(price)
    if side == "buy":
        direction = {"entry": "down", "stop": "down", "tp": "up"}[role]
    elif side == "sell":
        direction = {"entry": "up", "stop": "up", "tp": "down"}[role]
    else:
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    if direction == "up":
        return int(math.ceil(price / t) * t)
    return int(math.floor(price / t) * t)
