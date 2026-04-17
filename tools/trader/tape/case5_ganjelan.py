"""Case 5 — Ganjelan: fake queue (multiple 'thick' levels each from 1-2 accounts)."""
import sys, json, argparse
from pathlib import Path
from typing import Literal
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook, WALL_LOT_THRESHOLD

Risk = Literal["high", "med", "low"]


def detect_fake_queue(ob: dict) -> dict:
    fake_levels = []
    GANJELAN_FREQ_MAX = 3

    for side_key in ("bid", "offer"):
        for lvl in ob.get(side_key, []):
            lot = int(lvl.get("volume") or lvl.get("lot") or 0)
            freq = int(lvl.get("freq") or lvl.get("count") or lvl.get("queue") or 99)
            price = float(lvl.get("price", 0))
            # "thick" lot but very few accounts → fake depth
            if lot >= WALL_LOT_THRESHOLD and freq <= GANJELAN_FREQ_MAX:
                fake_levels.append({"price": price, "lot": lot, "freq": freq, "side": side_key})

    count = len(fake_levels)
    risk: Risk = "high" if count >= 3 else "med" if count >= 1 else "low"

    return {"fake_levels": fake_levels, "risk": risk}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    print(json.dumps(detect_fake_queue(ob), indent=2))
