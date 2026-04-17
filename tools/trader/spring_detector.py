"""
Spring setup detector (Wyckoff Phase C engineered shakeout).
Composes: api.get_support_resistance, api.get_price, api.analyze_bid_offer,
          api.get_volume_ratio, api.get_running_trades, broker_profile.analyze_players.
"""
import sys
import json
import argparse
from typing import Literal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import tools.trader.api as api
import tools.trader.broker_profile as broker_profile

Confidence = Literal["low", "med", "high"]


def detect(ticker: str) -> dict:
    """
    Detect a Wyckoff spring setup.
    Returns dict with is_spring, support, last, pct_below, bid_offer_ratio,
    smart_money_bid_freq_ratio, volume_spike, confidence, notes.
    """
    t = ticker.upper()
    notes = []
    checks_passed = 0

    # Fetch data
    try:
        sr = api.get_support_resistance(t)
        support = sr.support if sr and sr.support else 0.0
    except Exception as e:
        support = 0.0
        notes.append(f"support fetch failed: {e}")

    try:
        last = api.get_price(t)
    except Exception as e:
        return {"ticker": t, "is_spring": False, "error": str(e)}

    try:
        bo = api.analyze_bid_offer(t)
        bid_offer_ratio = bo.get("bid_offer_ratio", 0.0)
        thick_bid_near = bo.get("pattern") == "bid_pressure"
    except Exception:
        bid_offer_ratio = 0.0
        thick_bid_near = False

    try:
        vol_ratio = api.get_volume_ratio(t)
    except Exception:
        vol_ratio = 0.0

    try:
        pa = broker_profile.analyze_players(t)
        sm_side = pa.smart_money_side  # "buying" / "selling" / "mixed" / "absent"
        sm_count = len(pa.smart_money_buyers)
        retail_count = max(1, len([b for b in pa.buyers if b.category == "retail"]))
        sm_bid_freq_ratio = sm_count / retail_count
    except Exception:
        sm_side = "absent"
        sm_bid_freq_ratio = 0.0

    # Gate 1: price < support * 0.98
    if support > 0 and last < support * 0.98:
        pct_below = (support - last) / support * 100
        checks_passed += 1
        notes.append(f"price {last} below support {support} by {pct_below:.1f}%")
    else:
        pct_below = 0.0
        notes.append(f"price {last} not below support {support} by >=2%")

    # Gate 2: bid_offer_ratio > 1.5 OR thick_bid_near
    if bid_offer_ratio > 1.5 or thick_bid_near:
        checks_passed += 1
        notes.append(f"bid stack quality ok (ratio={bid_offer_ratio}, thick_bid={thick_bid_near})")
    else:
        notes.append(f"bid stack weak (ratio={bid_offer_ratio})")

    # Gate 3: smart money net bidding
    if sm_side == "buying":
        checks_passed += 1
        notes.append("smart money net bidding confirmed")
    else:
        notes.append(f"smart money side: {sm_side}")

    # Gate 4: vol_ratio >= 1.5
    volume_spike = vol_ratio >= 3.0
    if vol_ratio >= 1.5:
        checks_passed += 1
        notes.append(f"volume spike ok (ratio={vol_ratio:.2f}, spike={volume_spike})")
    else:
        notes.append(f"volume insufficient (ratio={vol_ratio:.2f})")

    is_spring = checks_passed == 4

    if is_spring:
        if volume_spike:
            confidence: Confidence = "high"
        else:
            confidence = "med"
    elif checks_passed == 3:
        confidence = "low"
    else:
        confidence = "low"
        is_spring = False

    return {
        "ticker": t,
        "is_spring": is_spring,
        "support": support,
        "last": last,
        "pct_below": round(pct_below, 2),
        "bid_offer_ratio": round(bid_offer_ratio, 2),
        "smart_money_bid_freq_ratio": round(sm_bid_freq_ratio, 2),
        "volume_spike": volume_spike,
        "confidence": confidence if (is_spring or checks_passed == 3) else "low",
        "checks_passed": checks_passed,
        "notes": notes,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    args = p.parse_args()
    print(json.dumps(detect(args.ticker), indent=2))
