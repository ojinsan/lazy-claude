"""
Confluence scorer — collapse all per-dim signals into a 0-100 score.
Composes: broker_profile, sid_tracker, vp_analyzer, tape_runner, imposter_detector,
          wyckoff, spring_detector, konglo_flow, konglo_loader, api.
"""
import sys
import json
import argparse
from datetime import date
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))
import tools.trader.api as api
import tools.trader.broker_profile as broker_profile
import tools.trader.vp_analyzer as vp_analyzer
import tools.trader.spring_detector as spring_detector
import tools.trader.imposter_detector as imposter_detector
import tools.trader.konglo_loader as konglo_loader
import tools.trader.konglo_flow as konglo_flow

Bucket = Literal["reject", "watch", "plan", "execute"]


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def score(ticker: str) -> dict:
    t = ticker.upper()
    components: dict[str, int] = {}
    reasons: list[str] = []

    # --- Narrative fit (0..10) ---
    narrative_fit = 5  # default neutral
    try:
        group = konglo_loader.group_for(t)
        if group:
            gflow = konglo_flow.group_flow_today(group["id"])
            if gflow.get("verdict") == "rotation_in":
                narrative_fit = 10
                reasons.append("konglo group rotating in")
            elif gflow.get("verdict") == "rotation_out":
                narrative_fit = 0
                reasons.append("konglo group rotating out")
    except Exception:
        pass
    components["narrative_fit"] = narrative_fit

    # --- Technical (0..15) ---
    technical = 5
    try:
        trend = api.get_trend(t)
        if trend.get("direction") == "up":
            technical += 5
        sr = api.get_support_resistance(t)
        price = api.get_price(t)
        if sr.support and price > sr.support * 1.01:
            technical += 3
        elif sr.support and price <= sr.support:
            technical -= 2
    except Exception:
        pass
    technical = max(0, min(15, technical))
    components["technical"] = technical

    # --- Broker flow (-15..+15) ---
    broker_flow_score = 0
    try:
        pa = broker_profile.analyze_players(t)
        if pa.smart_money_side == "buying":
            broker_flow_score = 15
            reasons.append("smart money buying")
        elif pa.smart_money_side == "selling":
            broker_flow_score = -15
            reasons.append("smart money selling")
        elif pa.smart_money_side == "mixed":
            broker_flow_score = 0
    except Exception:
        pass
    components["broker_flow"] = broker_flow_score

    # --- SID (-10..+10) ---
    sid_score = 0
    try:
        sid_data = api.get_stockbit_sid_count(t)
        sid_trend = sid_data.get("trend") or sid_data.get("direction", "")
        if "accumulate" in str(sid_trend).lower() or sid_trend == "up":
            sid_score = 10
        elif "distribute" in str(sid_trend).lower() or sid_trend == "down":
            sid_score = -10
    except Exception:
        pass
    components["sid"] = sid_score

    # --- VP state (-10..+10) ---
    vp_score = 0
    try:
        vp = vp_analyzer.classify(t)
        vp_map = {
            "healthy_up": 10,
            "healthy_correction": 5,
            "weak_rally": -5,
            "distribution": -10,
            "indeterminate": 0,
        }
        vp_score = vp_map.get(vp["state"], 0)
        if vp_score != 0:
            reasons.append(f"vp_state={vp['state']}")
    except Exception:
        pass
    components["vp_state"] = vp_score

    # --- Orderbook / tape (-10..+10) ---
    ob_score = 0
    try:
        from tools.trader.tape_runner import snapshot as tape_snapshot
        tape = tape_snapshot(t)
        tape_map = {
            "ideal_markup": 10,
            "healthy_markup": 7,
            "spring_ready": 8,
            "neutral": 0,
            "crossing_flag": 0,
            "fake_support": -8,
            "distribution_trap": -10,
            "spam_warning": -6,
        }
        ob_score = tape_map.get(tape.composite, 0)
        if ob_score != 0:
            reasons.append(f"tape={tape.composite}")
    except Exception:
        pass
    components["orderbook"] = ob_score

    # --- Imposter (-10..+10) ---
    imposter_score = 0
    try:
        imp = imposter_detector.score(t)
        raw = imp.get("imposter_score", 0)
        imposter_score = max(-10, min(10, raw))
    except Exception:
        pass
    components["imposter"] = imposter_score

    # --- Wyckoff phase (0..10) ---
    wyckoff_score = 0
    try:
        import tools.trader.wyckoff as wyckoff
        wa = wyckoff.analyze_wyckoff(t)
        phase_map = {"A": 2, "B": 5, "C": 8, "D": 10, "E": 3}
        phase_str = str(wa.phase).replace("Phase.", "")
        wyckoff_score = phase_map.get(phase_str, 0)
    except Exception:
        pass
    components["wyckoff_phase"] = wyckoff_score

    # --- Spring bonus (0..15) ---
    spring_bonus = 0
    try:
        sp = spring_detector.detect(t)
        if sp.get("is_spring"):
            conf_map = {"high": 15, "med": 10, "low": 5}
            spring_bonus = conf_map.get(sp.get("confidence", "low"), 0)
            reasons.append(f"spring conf={sp['confidence']}")
    except Exception:
        pass
    components["spring_bonus"] = spring_bonus

    # --- Konglo bonus (0..10) ---
    konglo_bonus = 0
    try:
        group = konglo_loader.group_for(t)
        if group:
            gflow = konglo_flow.group_flow_today(group["id"])
            if gflow.get("verdict") == "rotation_in":
                konglo_bonus = 10
    except Exception:
        pass
    components["konglo_bonus"] = konglo_bonus

    # --- Sum and clamp ---
    raw_sum = sum(components.values())
    total = max(0, min(100, raw_sum))

    if total < 40:
        bucket: Bucket = "reject"
    elif total < 60:
        bucket = "watch"
    elif total < 80:
        bucket = "plan"
    else:
        bucket = "execute"

    return {
        "ticker": t,
        "ts": date.today().isoformat(),
        "components": components,
        "score": total,
        "bucket": bucket,
        "reasons": reasons,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    args = p.parse_args()
    print(json.dumps(score(args.ticker), indent=2))
