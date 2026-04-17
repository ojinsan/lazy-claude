"""Case 3 — Bullish absorption: offer eaten and bid thickens."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook, WALL_LOT_THRESHOLD


def detect_bullish_absorption(ob_history: list[dict], tb_history: list[dict]) -> dict:
    """
    ob_history: list of successive orderbook snapshots (oldest first).
    tb_history: list of trade book snapshots aligned with ob_history.
    Returns is_absorbing + absorbed levels.
    """
    if len(ob_history) < 2:
        return {"is_absorbing": False, "levels": [], "note": "need >= 2 snapshots"}

    absorbed_levels = []
    for i in range(1, len(ob_history)):
        prev_ob = ob_history[i - 1]
        curr_ob = ob_history[i]

        prev_offers = {float(l["price"]): int(l.get("volume") or l.get("lot") or 0)
                       for l in prev_ob.get("offer", []) if int(l.get("volume") or l.get("lot") or 0) >= WALL_LOT_THRESHOLD}
        curr_bid_prices = {float(l["price"]) for l in curr_ob.get("bid", [])}

        for price, lot in prev_offers.items():
            # offer disappeared
            curr_offer_lots = {float(l["price"]): int(l.get("volume") or l.get("lot") or 0)
                               for l in curr_ob.get("offer", [])}
            if price not in curr_offer_lots or curr_offer_lots[price] < lot * 0.5:
                # bid thickened at or below this price
                if any(bp <= price for bp in curr_bid_prices):
                    absorbed_levels.append(price)

    return {"is_absorbing": len(absorbed_levels) > 0, "levels": absorbed_levels}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    result = detect_bullish_absorption([ob, ob], [])
    print(json.dumps(result, indent=2))
