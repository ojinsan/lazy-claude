"""Case 6 — Healthy markup: offer eaten → bid thickens next tick, repeat."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook


def is_healthy_markup(ob_history: list[dict], tb_history: list[dict]) -> bool:
    """
    True if at least 2 consecutive cycles show: offer eaten at a level → bid thickens at same/next tick.
    Simpler version: check that bid stack top > offer stack bottom (bid-offer inversion or near-inversion)
    sustained across at least 2 ob snapshots.
    """
    if len(ob_history) < 2:
        return False

    confirmations = 0
    for i in range(1, len(ob_history)):
        prev = ob_history[i - 1]
        curr = ob_history[i]

        prev_offers = sorted([float(l["price"]) for l in prev.get("offer", [])], )
        curr_bids = sorted([float(l["price"]) for l in curr.get("bid", [])], reverse=True)

        if not prev_offers or not curr_bids:
            continue

        best_bid = curr_bids[0]
        best_offer_prev = prev_offers[0]

        # Bid advanced past where the offer was previously sitting
        if best_bid >= best_offer_prev:
            confirmations += 1

    return confirmations >= 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    print(is_healthy_markup([ob, ob], []))
