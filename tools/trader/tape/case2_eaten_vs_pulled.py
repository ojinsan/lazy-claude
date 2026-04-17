"""Case 2 — Distinguish eaten vs pulled walls."""
import sys, json, argparse
from pathlib import Path
from typing import Literal
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook, load_orderbook_delta, WALL_LOT_THRESHOLD

WallFate = Literal["eaten", "pulled", "stable"]


def classify_wall_fate(ob_prev: dict, ob_now: dict, tb_delta: dict) -> WallFate:
    """
    eaten = wall gone AND trade book shows volume transacted at that price.
    pulled = wall gone AND no trades at that price.
    stable = wall still present.
    """
    def wall_prices(ob: dict) -> set[float]:
        levels = ob.get("bid", []) + ob.get("offer", [])
        return {float(l["price"]) for l in levels if int(l.get("volume") or l.get("lot") or 0) >= WALL_LOT_THRESHOLD}

    prev_walls = wall_prices(ob_prev)
    now_walls = wall_prices(ob_now)
    gone = prev_walls - now_walls
    if not gone:
        return "stable"

    # check if trades happened at those prices
    traded_prices = set()
    for side in ("buy_by_price", "sell_by_price"):
        for entry in tb_delta.get(side, []):
            p = float(entry.get("price", 0))
            if int(entry.get("lot") or entry.get("volume") or 0) > 0:
                traded_prices.add(p)

    if any(g in traded_prices for g in gone):
        return "eaten"
    return "pulled"


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    delta = load_orderbook_delta(args.ticker)
    print(classify_wall_fate(ob, ob, delta))
