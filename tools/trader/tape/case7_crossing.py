"""Case 7 — Cross-trade detection: large same-price transactions between two counterparties."""
import sys, json, argparse
from pathlib import Path
from typing import Optional
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_running, load_orderbook_delta, CROSSING_LOT_MIN


def detect_crossing(running: list[dict], tb_delta: dict, level: float = 0.0) -> dict:
    """
    Crossing = same price, same second, buyer + seller with large lot.
    Returns is_crossing, seller code, buyer code, lot.
    """
    # Group by (price, ts)
    by_pt: dict[tuple, list[dict]] = defaultdict(list)
    for tr in running:
        price = float(tr.get("price") or tr.get("p") or 0)
        ts = str(tr.get("ts") or tr.get("time") or "")
        lot = int(tr.get("lot") or tr.get("volume") or 0)
        side = (tr.get("side") or tr.get("type") or "").upper()
        code = (tr.get("broker_code") or tr.get("broker") or "??").upper()
        by_pt[(price, ts)].append({"code": code, "side": side, "lot": lot})

    for (price, ts), trades in by_pt.items():
        if level and abs(price - level) > level * 0.01:
            continue
        buyers = [t for t in trades if "B" in t["side"]]
        sellers = [t for t in trades if "S" in t["side"]]
        if buyers and sellers:
            total_lot = sum(t["lot"] for t in trades)
            if total_lot >= CROSSING_LOT_MIN:
                return {
                    "is_crossing": True,
                    "price": price,
                    "ts": ts,
                    "seller": sellers[0]["code"],
                    "buyer": buyers[0]["code"],
                    "lot": total_lot,
                }

    return {"is_crossing": False, "seller": "", "buyer": "", "lot": 0}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    running = load_running(args.ticker)
    delta = load_orderbook_delta(args.ticker)
    print(json.dumps(detect_crossing(running, delta), indent=2))
