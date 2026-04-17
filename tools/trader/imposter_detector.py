"""
Imposter detection — smart money hiding inside retail broker codes.
Composes: api.get_running_trades, api.classify_broker.
"""
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
import tools.trader.api as api

LARGE_LOT_THRESHOLD = 50_000   # lots per single trade


def score(ticker: str, window_trades: int = 200) -> dict:
    """
    Score likelihood that 'retail' coded trades are actually smart-money imposters.
    Returns imposter_score -10..+10 (positive = retail codes look suspicious).
    """
    t = ticker.upper()
    trades = api.get_running_trades(t, limit=window_trades)

    if not trades:
        return {
            "ticker": t,
            "imposter_score": 0,
            "large_lot_retail_trades": 0,
            "same_second_retail_cluster": 0,
            "one_retail_selling_into_many_retail_buying": False,
            "flagged_codes": [],
            "note": "no trade data",
        }

    imposter_score = 0
    large_lot_retail = 0
    flagged_codes: list[str] = []
    ts_groups: dict[str, list[dict]] = defaultdict(list)  # ts → [trade, ...]
    retail_buys: dict[str, int] = defaultdict(int)        # code → lot
    retail_sells: dict[str, int] = defaultdict(int)

    for tr in trades:
        code = (tr.get("broker_code") or tr.get("broker") or tr.get("code") or "??").upper()
        side = (tr.get("side") or tr.get("type") or "").upper()
        lot = int(tr.get("lot") or tr.get("volume") or 0)
        ts = str(tr.get("ts") or tr.get("time") or tr.get("timestamp") or "")

        if api.classify_broker(code) != "retail":
            continue

        # Signal 1: large lot from retail code
        if lot >= LARGE_LOT_THRESHOLD:
            large_lot_retail += 1
            flagged_codes.append(code)

        # For signal 2: same-second retail cluster
        if ts:
            ts_groups[ts].append({"code": code, "lot": lot, "side": side})

        # For signal 3: one heavy seller vs many buyers
        if "B" in side:
            retail_buys[code] += lot
        elif "S" in side:
            retail_sells[code] += lot

    # Signal 1: each large lot retail trade → +3 (cap at +6)
    imposter_score += min(large_lot_retail * 3, 6)

    # Signal 2: same-second retail clusters (2+ retail codes at identical ts)
    same_second = sum(1 for trades_at_ts in ts_groups.values() if len(trades_at_ts) >= 2)
    imposter_score += min(same_second * 2, 4)

    # Signal 3: many buyers + one heavy seller
    one_heavy_sell = False
    if retail_buys and retail_sells:
        total_buy_lots = sum(retail_buys.values())
        max_seller_lots = max(retail_sells.values())
        if len(retail_buys) >= 3 and max_seller_lots > total_buy_lots * 0.3:
            one_heavy_sell = True
            imposter_score += 4

    imposter_score = max(-10, min(10, imposter_score))
    flagged_codes = sorted(set(flagged_codes))

    return {
        "ticker": t,
        "imposter_score": imposter_score,
        "large_lot_retail_trades": large_lot_retail,
        "same_second_retail_cluster": same_second,
        "one_retail_selling_into_many_retail_buying": one_heavy_sell,
        "flagged_codes": flagged_codes,
        "note": _interpret(imposter_score, one_heavy_sell),
    }


def _interpret(s: int, heavy_sell: bool) -> str:
    if s >= 6 and heavy_sell:
        return "high suspicion: operator distributing via retail codes"
    if s >= 6:
        return "high suspicion: retail codes with institutional lot sizes"
    if s >= 3:
        return "moderate suspicion: some anomalies in retail flow"
    return "low suspicion: retail flow looks genuine"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--trades", type=int, default=200)
    args = p.parse_args()
    print(json.dumps(score(args.ticker, args.trades), indent=2))
