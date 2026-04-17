"""
Tape state orchestrator — runs all 9 cases and produces a composite TapeState.
Composes: tape/ package modules, spring_detector.
CLI: python tools/trader/tape_runner.py BBCA
"""
import sys
import json
import argparse
from dataclasses import dataclass, asdict
from typing import Optional, Literal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.trader.tape._lib import load_orderbook, load_running, load_orderbook_delta
from tools.trader.tape.case1_walls import detect_walls
from tools.trader.tape.case2_eaten_vs_pulled import classify_wall_fate
from tools.trader.tape.case3_offer_eaten_bullish import detect_bullish_absorption
from tools.trader.tape.case4_freq_lot import analyze_orderbook_nature
from tools.trader.tape.case5_ganjelan import detect_fake_queue
from tools.trader.tape.case6_healthy_markup import is_healthy_markup
from tools.trader.tape.case7_crossing import detect_crossing
from tools.trader.tape.case8_ideal_markup import is_ideal_markup
from tools.trader.tape.case9_spam_lot import detect_spam
import tools.trader.spring_detector as spring_detector

Composite = Literal[
    "ideal_markup", "healthy_markup", "spring_ready",
    "fake_support", "distribution_trap", "crossing_flag",
    "spam_warning", "neutral"
]
Confidence = Literal["low", "med", "high"]


@dataclass
class TapeState:
    ticker: str
    ts: str
    walls: dict
    wall_fate: str
    bullish_absorption: bool
    queue_nature: dict
    fake_queue_risk: str
    healthy_markup: bool
    ideal_markup: bool
    crossing: Optional[dict]
    spam: dict
    composite: Composite
    confidence: Confidence


def _now_ts() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot(ticker: str) -> TapeState:
    t = ticker.upper()

    ob = load_orderbook(t)
    running = load_running(t, limit=200)
    delta = load_orderbook_delta(t)

    walls = detect_walls(ob)
    wall_fate = classify_wall_fate(ob, ob, delta)   # prev=ob (single snapshot degraded to stable)
    absorption = detect_bullish_absorption([ob, ob], [])
    bullish_abs = absorption.get("is_absorbing", False)
    queue_nat = analyze_orderbook_nature(ob)
    fake_q = detect_fake_queue(ob)
    fake_queue_risk = fake_q.get("risk", "low")
    healthy = is_healthy_markup([ob, ob], [])
    ideal = is_ideal_markup([ob, ob, ob], [])
    crossing = detect_crossing(running, delta)
    spam = detect_spam(running)

    spring = spring_detector.detect(t)
    is_spring = spring.get("is_spring", False)
    spring_conf = spring.get("confidence", "low")

    # Composite rule — first match wins
    composite: Composite
    confidence: Confidence

    if ideal and wall_fate == "eaten" and not spam.get("is_spam"):
        composite, confidence = "ideal_markup", "high"
    elif healthy and bullish_abs and fake_queue_risk != "high":
        composite = "healthy_markup"
        confidence = "high" if ideal else "med"
    elif walls.get("support") and wall_fate == "stable" and is_spring:
        composite = "spring_ready"
        confidence = spring_conf  # type: ignore[assignment]
    elif walls.get("support") and wall_fate == "eaten":
        composite, confidence = "fake_support", "high"
    elif crossing and crossing.get("is_crossing"):
        composite, confidence = "crossing_flag", "med"
    elif spam.get("is_spam"):
        composite, confidence = "spam_warning", "med"
    elif fake_queue_risk == "high":
        composite, confidence = "distribution_trap", "med"
    else:
        composite, confidence = "neutral", "low"

    return TapeState(
        ticker=t,
        ts=_now_ts(),
        walls=walls,
        wall_fate=wall_fate,
        bullish_absorption=bullish_abs,
        queue_nature=queue_nat,
        fake_queue_risk=fake_queue_risk,
        healthy_markup=healthy,
        ideal_markup=ideal,
        crossing=crossing,
        spam=spam,
        composite=composite,
        confidence=confidence,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    args = p.parse_args()
    state = snapshot(args.ticker)
    print(json.dumps(asdict(state), indent=2, default=str))
