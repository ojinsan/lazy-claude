"""Bid-offer pattern analysis — PRD port.

Ported from vault/developer_notes/REVAMP PLAN.md §L3 "Bid Offer thick wall setup".
Pure functions, no I/O, no API calls.
"""
from __future__ import annotations


def analyze_near_book(bids: list[dict], offers: list[dict], n: int = 7) -> dict:
    """Analyze top-n bid/offer levels for thick-wall patterns.

    bids   : list of {price, lot} — sorted desc by price (nearest first)
    offers : list of {price, lot} — sorted asc by price (nearest first)

    Returns:
      {
        pattern: "spike" | "gradient" | "normal",
        retail_scared: bool,
        ratios: list[float],
        level_1_ratio: float,
      }
    """
    bids_near   = sorted(bids,   key=lambda x: x["price"], reverse=True)[:n]
    offers_near = sorted(offers, key=lambda x: x["price"])[:n]

    ratios = []
    for i, (b, o) in enumerate(zip(bids_near, offers_near)):
        ratios.append({
            "level": i + 1,
            "ratio": round(o["lot"] / b["lot"], 2) if b["lot"] else 999,
            "bid_lot": b["lot"],
            "offer_lot": o["lot"],
        })

    r = [x["ratio"] for x in ratios]

    is_spike = r[0] >= 3.0 and r[0] >= 2.0 * max(r[1:])

    rising = sum(1 for i in range(len(r) - 1) if r[i + 1] > r[i])
    is_gradient = rising >= len(r) * 0.6

    near_bid_avg = sum(x["bid_lot"] for x in ratios[:3]) / 3
    far_bid_avg  = sum(x["bid_lot"] for x in ratios[3:]) / max(len(ratios[3:]), 1)
    retail_scared = near_bid_avg < far_bid_avg * 0.7

    pattern = "spike" if is_spike else "gradient" if is_gradient else "normal"

    return {
        "pattern": pattern,
        "retail_scared": retail_scared,
        "ratios": r,
        "level_1_ratio": r[0],
    }


def wall_withdrawn(prev_offer_map: dict[str, int], now_offer_map: dict[str, int], threshold_lot: int = 5000) -> bool:
    """True if any level in prev had >=threshold_lot offer that shrank by >=threshold_lot in now."""
    for price, prev_lot in prev_offer_map.items():
        if prev_lot < threshold_lot:
            continue
        now_lot = now_offer_map.get(price, 0)
        if prev_lot - now_lot >= threshold_lot:
            return True
    return False
