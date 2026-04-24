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


TIER = {"low": 0.01, "med": 0.02, "high": 0.03, "off": None}
BP_SINGLE_NAME_CAP = 0.30


def size_plan(
    entry: float,
    stop: float,
    buying_power: float,
    aggressiveness: str,
    intraday_notch: int,
    side: Side = "buy",
) -> dict:
    """Compute lot size + risk_idr + notional from entry/stop.

    Returns:
        {"lots","risk_idr","notional","tier"} on success
        {"abort":True,"reason":str} on fail

    Rules:
    - tier = TIER[aggressiveness.lower()]; "off" → abort
    - intraday_notch < 0 → shrink tier by 0.01, floor 0.01
    - single-name cap: lots * entry * 100 ≤ buying_power * 0.30
    - sub-lot result → abort
    - zero or negative stop distance → abort
    """
    tier = TIER.get((aggressiveness or "").lower())
    if tier is None:
        return {"abort": True, "reason": "aggressiveness=off (kill-switch)"}
    if buying_power <= 0:
        return {"abort": True, "reason": "buying_power<=0"}
    if intraday_notch < 0:
        tier = max(round(tier - 0.01, 4), 0.01)
    e = float(entry)
    s = float(stop)
    dist = abs(e - s)
    if dist <= 0:
        return {"abort": True, "reason": "zero stop distance"}
    if e <= 0:
        return {"abort": True, "reason": "entry<=0"}
    risk_idr = buying_power * tier
    shares = risk_idr / dist
    lots = int(shares // 100)
    max_lots_cap = int((buying_power * BP_SINGLE_NAME_CAP) / (e * 100))
    lots = min(lots, max_lots_cap)
    if lots <= 0:
        return {"abort": True, "reason": "sub-lot size"}
    return {
        "lots": lots,
        "risk_idr": round(lots * 100 * dist),
        "notional": round(lots * 100 * e),
        "tier": tier,
    }
