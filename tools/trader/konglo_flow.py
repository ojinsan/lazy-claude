"""
Konglo group flow analyzer.
Composes: konglo_loader, api.get_broker_distribution, api.get_price, api.get_volume_ratio.
"""
import sys
import json
import argparse
from typing import Literal
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.trader.api as api
import tools.trader.konglo_loader as konglo_loader

Verdict = Literal["rotation_in", "rotation_out", "mixed", "insufficient_data"]


def _sm_net(dist: api.BrokerDistribution) -> float:
    """Smart money net = sum of buy inventory_val for smart buyers minus smart sellers."""
    sm_buy = sum(
        e.inventory_val for e in dist.top_buyers
        if api.classify_broker(e.code) == "smart_money"
    )
    sm_sell = sum(
        e.inventory_val for e in dist.top_sellers
        if api.classify_broker(e.code) == "smart_money"
    )
    return sm_buy - sm_sell


def group_flow_today(group_id: str) -> dict:
    tickers = konglo_loader.tickers_for_group(group_id)
    if not tickers:
        return {"error": f"group {group_id!r} not found"}

    members = []
    leaders = []
    laggards = []
    total_ret = 0.0
    total_vol_ratio = 0.0
    n_valid = 0

    for t in tickers:
        try:
            price = api.get_price(t)
            hist = api.get_price_history(t, days=2)
            if len(hist) < 2:
                continue
            prev_close = hist[-2]["close"] if hist[-2].get("close") else hist[-2].get("price", price)
            ret_pct = (price - prev_close) / prev_close * 100 if prev_close else 0.0
            vol_ratio = api.get_volume_ratio(t)
            dist = api.get_broker_distribution(t)
            sm_net = _sm_net(dist)
            members.append({
                "ticker": t,
                "ret_pct": round(ret_pct, 2),
                "vol_ratio": round(vol_ratio, 2),
                "smart_money_net": round(sm_net, 0),
            })
            total_ret += ret_pct
            total_vol_ratio += vol_ratio
            n_valid += 1
        except Exception:
            continue

    if n_valid == 0:
        return {
            "group_id": group_id,
            "members": [],
            "verdict": "insufficient_data",
        }

    avg_ret = total_ret / n_valid
    avg_vol = total_vol_ratio / n_valid

    members_sorted = sorted(members, key=lambda x: x["ret_pct"], reverse=True)
    if len(members_sorted) >= 2:
        leaders = [members_sorted[0]["ticker"]]
        laggards = [members_sorted[-1]["ticker"]]

    if avg_ret >= 0.5 and avg_vol >= 1.0:
        verdict: Verdict = "rotation_in"
    elif avg_ret <= -0.5 and avg_vol >= 1.0:
        verdict = "rotation_out"
    elif abs(avg_ret) < 0.5:
        verdict = "mixed"
    else:
        verdict = "mixed"

    return {
        "group_id": group_id,
        "members": members,
        "group_ret": round(avg_ret, 2),
        "group_volume_z": round(avg_vol, 2),
        "leaders": leaders,
        "laggards": laggards,
        "verdict": verdict,
    }


def all_groups_flow() -> list[dict]:
    idx = konglo_loader.load()
    results = []
    for gid in idx["by_id"]:
        r = group_flow_today(gid)
        results.append(r)
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--group", help="group_id to analyze")
    p.add_argument("--all", action="store_true", help="all groups")
    args = p.parse_args()

    if args.all:
        data = all_groups_flow()
    elif args.group:
        data = group_flow_today(args.group)
    else:
        p.print_help()
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))
