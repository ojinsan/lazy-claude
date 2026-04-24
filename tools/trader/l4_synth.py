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


def format_plan_prompt_a(ctx: dict) -> str:
    """Mode A full plan prompt.

    ctx keys: ticker, regime, aggressiveness, side, bp_idr, conf, details, narrative,
    structure (dict), atr, close, hi60, lo60.
    """
    s = ctx.get("structure") or {}
    lsl = s.get("last_swing_low") or {}
    lsl_price = lsl.get("price") if isinstance(lsl, dict) else "?"
    return (
        f"You are L4 trade-plan synth for IDX ticker {ctx['ticker']}. Output one trade plan as JSON.\n\n"
        f"Context:\n"
        f"- regime={ctx.get('regime','?')}, aggressiveness={ctx.get('aggressiveness','?')}, side={ctx['side']}\n"
        f"- buying_power={ctx.get('bp_idr',0):,.0f}, confidence={ctx.get('conf','?')}/100\n"
        f"- prior details (L2): {ctx.get('details','—')}\n"
        f"- narrative: {ctx.get('narrative','—')}\n"
        f"- structure: trend={s.get('trend','?')}, wyckoff={s.get('wyckoff_phase','?')}, "
        f"support={s.get('support','?')}, resistance={s.get('resistance','?')}, "
        f"last_swing_low={lsl_price}\n"
        f"- ATR(14)={ctx.get('atr','?')}, last_close={ctx.get('close','?')}, "
        f"60d_high={ctx.get('hi60','?')}, 60d_low={ctx.get('lo60','?')}\n\n"
        f"Rules:\n"
        f"- Buy: entry near support OR above last_swing_low, stop below invalidation "
        f"(last_swing_low -1 tick OR support -0.5*ATR), TP1 >=1.5R, TP2 >=3R OR near resistance.\n"
        f"- Sell: mirror. Entry near resistance or break of support; stop above last_swing_high.\n"
        f"- Do NOT compute lot size — Python handles sizing.\n"
        f"- Output raw float prices; Python applies tick rounding.\n\n"
        f'Output strict JSON: {{"entry": <float>, "stop": <float>, "tp1": <float>, '
        f'"tp2": <float|null>, "rationale": "<=180 chars"}}'
    )


def format_plan_prompt_b(ctx: dict) -> str:
    """Mode B sizing-only prompt.

    ctx keys: ticker, conf, orderbook (dict: best_bid/best_offer/last_price),
    last_note (dict: composite/thick_wall_buy_strong/spring_confirmed),
    support, last_swing_low, atr, intraday_notch.
    """
    ob = ctx.get("orderbook") or {}
    nt = ctx.get("last_note") or {}
    return (
        f"You are L4 sizing-only synth for IDX ticker {ctx['ticker']}. L3 just fired BUY-NOW.\n\n"
        f"Context:\n"
        f"- side=buy, confidence={ctx.get('conf','?')}/100\n"
        f"- orderbook: best_bid={ob.get('best_bid','?')}, best_offer={ob.get('best_offer','?')}, "
        f"last={ob.get('last_price','?')}\n"
        f"- tape: {nt.get('composite','?')} | thick_wall_buy_strong={nt.get('thick_wall_buy_strong',False)} "
        f"| spring_confirmed={nt.get('spring_confirmed',False)}\n"
        f"- structure: support={ctx.get('support','?')}, last_swing_low={ctx.get('last_swing_low','?')}, "
        f"ATR(14)={ctx.get('atr','?')}\n"
        f"- intraday_notch={ctx.get('intraday_notch',0)}\n\n"
        f"Rules:\n"
        f"- Entry = current best_offer (sweep) OR last+1 tick.\n"
        f"- Stop = last_swing_low - 1 tick. If dist > 1.5*ATR → abort.\n"
        f"- TP1 = entry + 2*ATR (min 1.5R). TP2 = entry + 4*ATR OR resistance, whichever closer.\n\n"
        f'Output strict JSON: {{"entry": <float>, "stop": <float>, "tp1": <float>, '
        f'"tp2": <float|null>, "rationale": "<=140 chars"}} '
        f'OR {{"abort": true, "reason": "<=80 chars"}}'
    )


def parse_opus_plan_response(raw: str) -> dict:
    """Strip code fences, parse JSON, validate.

    Returns:
        {"abort": True, "reason": str} for abort responses
        {"entry","stop","tp1","tp2","rationale"} for full plans

    Raises ValueError on missing keys or malformed JSON.
    """
    s = raw.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 2 and lines[-1].startswith("```"):
            s = "\n".join(lines[1:-1])
        else:
            s = "\n".join(lines[1:])
    try:
        d = _json.loads(s)
    except _json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON: {e}") from e
    if not isinstance(d, dict):
        raise ValueError(f"expected JSON object, got {type(d).__name__}")
    if d.get("abort") is True:
        if "reason" not in d:
            raise ValueError("abort response missing 'reason'")
        return {"abort": True, "reason": str(d["reason"])[:80]}
    for k in ("entry", "stop", "tp1", "rationale"):
        if k not in d:
            raise ValueError(f"plan response missing key: {k}")
    return {
        "entry": float(d["entry"]),
        "stop": float(d["stop"]),
        "tp1": float(d["tp1"]),
        "tp2": float(d["tp2"]) if d.get("tp2") is not None else None,
        "rationale": str(d["rationale"])[:180],
    }
