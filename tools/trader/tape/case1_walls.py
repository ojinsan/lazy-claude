"""Case 1 — Thick bid/offer walls as S/R levels."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook, WALL_LOT_THRESHOLD


def detect_walls(ob: dict) -> dict:
    support, resistance = [], []
    wall_lot: dict[float, int] = {}

    for level in ob.get("bid", []):
        price = float(level.get("price", 0))
        lot = int(level.get("volume") or level.get("lot") or 0)
        if lot >= WALL_LOT_THRESHOLD:
            support.append(price)
            wall_lot[price] = lot

    for level in ob.get("offer", []):
        price = float(level.get("price", 0))
        lot = int(level.get("volume") or level.get("lot") or 0)
        if lot >= WALL_LOT_THRESHOLD:
            resistance.append(price)
            wall_lot[price] = lot

    return {"support": sorted(support, reverse=True), "resistance": sorted(resistance), "wall_lot": wall_lot}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    print(json.dumps(detect_walls(ob), indent=2))
