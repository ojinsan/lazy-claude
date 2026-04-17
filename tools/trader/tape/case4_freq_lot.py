"""Case 4 — Freq/lot mismatch: bandar vs retail queue classification."""
import sys, json, argparse
from pathlib import Path
from typing import Literal
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_orderbook, BANDAR_LOT_MIN, BANDAR_FREQ_MAX

QueueNature = Literal["bandar", "retail", "mixed"]


def queue_nature(level: dict) -> QueueNature:
    """level: dict with 'lot' (or 'volume') and 'freq' (or 'count') keys."""
    lot = int(level.get("lot") or level.get("volume") or 0)
    freq = int(level.get("freq") or level.get("count") or level.get("queue") or 99)
    if lot >= BANDAR_LOT_MIN and freq <= BANDAR_FREQ_MAX:
        return "bandar"
    if lot < BANDAR_LOT_MIN and freq > BANDAR_FREQ_MAX:
        return "retail"
    return "mixed"


def analyze_orderbook_nature(ob: dict) -> dict:
    result = {}
    for side_key, levels in [("bid", ob.get("bid", [])), ("offer", ob.get("offer", []))]:
        for lvl in levels:
            price = float(lvl.get("price", 0))
            nature = queue_nature(lvl)
            result[price] = nature
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    ob = load_orderbook(args.ticker)
    print(json.dumps(analyze_orderbook_nature(ob), indent=2))
