"""Case 8 — Ideal markup: stepwise offer eaten → bid restacked higher, continuously."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook


def is_ideal_markup(ob_history: list[dict], tb_history: list[dict]) -> bool:
    """
    Ideal markup: each cycle, top bid advances upward AND prior offer level disappears.
    Requires 3+ consecutive confirmations.
    """
    if len(ob_history) < 3:
        return False

    def best_bid(ob: dict) -> float:
        bids = sorted([float(l["price"]) for l in ob.get("bid", [])], reverse=True)
        return bids[0] if bids else 0.0

    def best_offer(ob: dict) -> float:
        offers = sorted([float(l["price"]) for l in ob.get("offer", [])])
        return offers[0] if offers else float("inf")

    steps = 0
    for i in range(1, len(ob_history)):
        prev, curr = ob_history[i - 1], ob_history[i]
        prev_bid, curr_bid = best_bid(prev), best_bid(curr)
        prev_offer = best_offer(prev)
        curr_offer = best_offer(curr)
        # bid advanced and offer retreated or was absorbed
        if curr_bid > prev_bid and (curr_offer > prev_offer or curr_offer == float("inf")):
            steps += 1

    return steps >= 2


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    print(is_ideal_markup([ob, ob, ob], []))
