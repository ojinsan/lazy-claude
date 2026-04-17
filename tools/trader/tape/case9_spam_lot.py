"""Case 9 — Spam lot: many small HAKA lots followed by large HAKI (distribution trap)."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.trader.tape._lib import load_running, SPAM_WINDOW_SEC, SPAM_HAKA_MIN

SPAM_HAKA_LOT_MAX = 5    # HAKA lots ≤ this count as spam
SPAM_HAKI_LOT_MIN = 500  # one HAKI trade this large confirms the dump


def detect_spam(running: list[dict], window_sec: int = SPAM_WINDOW_SEC) -> dict:
    """running: list of trade dicts with side, lot, ts fields."""
    if not running:
        return {"is_spam": False, "haka": 0, "haki": 0, "note": "no data"}

    haka_count = 0
    haki_count = 0
    haki_max_lot = 0

    for tr in running:
        side = (tr.get("side") or tr.get("type") or "").upper()
        lot = int(tr.get("lot") or tr.get("volume") or 0)

        if "B" in side:  # HAKA = buyer hits offer
            if lot <= SPAM_HAKA_LOT_MAX:
                haka_count += 1
        elif "S" in side:  # HAKI = seller hits bid
            haki_count += 1
            haki_max_lot = max(haki_max_lot, lot)

    is_spam = haka_count >= SPAM_HAKA_MIN and haki_max_lot >= SPAM_HAKI_LOT_MIN
    note = "spam detected: FOMO pump then large dump" if is_spam else "no spam pattern"

    return {
        "is_spam": is_spam,
        "haka": haka_count,
        "haki": haki_count,
        "haki_max_lot": haki_max_lot,
        "note": note,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("ticker"); args = p.parse_args()
    running = load_running(args.ticker)
    print(json.dumps(detect_spam(running), indent=2))
