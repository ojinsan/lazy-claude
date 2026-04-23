"""L3 per-ticker tape gatherer.

Reads:
- tape_runner.snapshot(t)
- spring_detector.detect(t)
- runtime/monitoring/orderbook_state/{t}.json (current)
- prior-cycle orderbook snapshot (optional, for wall_withdrawn diff)
- runtime/monitoring/realtime/{t}-run.jsonl last-10m
- api.get_price(t)

Emits compact dict for judge prompt. No AI. Graceful-degrade.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.trader.api as api
import tools.trader.spring_detector as spring_detector
import tools.trader.tape_runner as tape_runner
from tools.trader.bid_offer_patterns import analyze_near_book, wall_withdrawn

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_OB_DIR = str(WORKSPACE / "runtime" / "monitoring" / "orderbook_state")
DEFAULT_RT_DIR = str(WORKSPACE / "runtime" / "monitoring" / "realtime")
WALL_THRESHOLD_LOT = 5000


def _load_json(path: str | None) -> dict | None:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _to_dict(snap) -> dict:
    if isinstance(snap, dict):
        return snap
    if is_dataclass(snap):
        return asdict(snap)
    # generic attr-bag
    return {k: getattr(snap, k) for k in dir(snap) if not k.startswith("_") and not callable(getattr(snap, k))}


def _map_to_list(m: dict[str, int]) -> list[dict]:
    return [{"price": float(p), "lot": int(l)} for p, l in m.items()]


def _running_trade_summary(path: str) -> tuple[int, float | None]:
    if not os.path.exists(path):
        return 0, None
    now_ts = int(time.time())
    cutoff = now_ts - 600
    buy_lot = 0
    total_lot = 0
    count = 0
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = row.get("ts", 0)
                if ts < cutoff:
                    continue
                count += 1
                lot = int(row.get("lot", 0))
                total_lot += lot
                if row.get("side") == "buy":
                    buy_lot += lot
    except OSError:
        return 0, None
    ratio = (buy_lot / total_lot) if total_lot else None
    return count, ratio


def gather_tape(
    ticker: str,
    *,
    prior_orderbook_path: str | None = None,
    orderbook_state_dir: str | None = None,
    running_trade_dir: str | None = None,
) -> dict:
    t = ticker.upper()
    ob_dir = orderbook_state_dir or DEFAULT_OB_DIR
    rt_dir = running_trade_dir or DEFAULT_RT_DIR

    out: dict = {"ticker": t, "status": "ok"}

    # tape_runner composite
    try:
        snap = tape_runner.snapshot(t)
        data = _to_dict(snap)
        out["tape_composite"] = data.get("composite", "neutral")
        out["tape_confidence"] = data.get("confidence", "low")
        out["wall_fate"] = data.get("wall_fate", "")
    except Exception as e:
        out["status"] = "unavailable"
        out["reason"] = f"tape/orderbook unavailable: {e}"
        out["tape_composite"] = "neutral"
        out["tape_confidence"] = "low"
        out["wall_fate"] = ""

    # spring detector
    try:
        sp = spring_detector.detect(t)
        out["spring_confirmed"] = bool(sp.get("is_spring"))
        out["spring_confidence"] = sp.get("confidence", "low")
    except Exception:
        out["spring_confirmed"] = False
        out["spring_confidence"] = "low"

    # current price
    try:
        out["price_now"] = float(api.get_price(t) or 0)
    except Exception:
        out["price_now"] = 0.0

    # orderbook state (current + prior)
    ob_path = os.path.join(ob_dir, f"{t}.json")
    ob_now = _load_json(ob_path)
    out["orderbook_available"] = ob_now is not None

    if ob_now:
        bid_map = ob_now.get("bid_map", {})
        offer_map = ob_now.get("offer_map", {})
        out["bid_map_top7"] = dict(sorted(bid_map.items(), key=lambda x: -float(x[0]))[:7])
        out["offer_map_top7"] = dict(sorted(offer_map.items(), key=lambda x: float(x[0]))[:7])
        try:
            pat = analyze_near_book(_map_to_list(bid_map), _map_to_list(offer_map), n=7)
            out["pattern"] = pat["pattern"]
            out["retail_scared"] = pat["retail_scared"]
            out["level_1_ratio"] = pat["level_1_ratio"]
        except Exception:
            out["pattern"] = "normal"
            out["retail_scared"] = False
            out["level_1_ratio"] = 1.0

        prior = _load_json(prior_orderbook_path)
        if prior:
            out["wall_withdrawn"] = wall_withdrawn(
                prior.get("offer_map", {}), offer_map, threshold_lot=WALL_THRESHOLD_LOT
            )
        else:
            out["wall_withdrawn"] = False
    else:
        out["bid_map_top7"] = None
        out["offer_map_top7"] = None
        out["pattern"] = "normal"
        out["retail_scared"] = False
        out["level_1_ratio"] = 1.0
        out["wall_withdrawn"] = False
        if out["status"] == "ok":
            out["status"] = "unavailable"
            out["reason"] = "orderbook_state missing"

    # composite PRD signals
    tape_bullish = out["tape_composite"] in ("healthy_markup", "ideal_markup")
    tape_bearish = out["tape_composite"] in ("fake_support", "distribution_trap")
    out["thick_wall_buy"] = (
        out["pattern"] in ("spike", "gradient")
        and out["retail_scared"]
        and tape_bullish
        and not tape_bearish
    )
    out["thick_wall_buy_strong"] = out["thick_wall_buy"] and out["wall_withdrawn"]

    # running trades
    rt_path = os.path.join(rt_dir, f"{t}-run.jsonl")
    count, buy_ratio = _running_trade_summary(rt_path)
    out["running_trade_count_10m"] = count
    out["running_trade_buy_ratio"] = buy_ratio

    return out
