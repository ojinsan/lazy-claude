"""L2 per-ticker dim gatherers (spec #4).

Each `gather_*` returns a compact dict for the openclaude judge prompt. No AI.
Graceful degrade on missing data: returns `{"status": "unavailable", "reason": ...}`.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
from typing import Any, Optional

from tools.trader import api, wyckoff, spring_detector, vp_analyzer, relative_strength
from tools.trader import sid_tracker, broker_profile, konglo_loader

WORKSPACE = pathlib.Path(__file__).resolve().parents[2]
ORDERBOOK_STATE_DIR = WORKSPACE / "runtime" / "monitoring" / "orderbook_state"
NOTES_DIR = WORKSPACE / "runtime" / "monitoring" / "notes"
WIB = _dt.timezone(_dt.timedelta(hours=7))


# ─── dim 1: price / volume / wyckoff / spring / vp / RS ──────────────────────

def _rs_rank(ticker: str, sector: Optional[str]) -> Optional[int]:
    """Rank of ticker among sector peers (1-indexed); None if unavailable."""
    if not sector:
        return None
    try:
        peers = relative_strength._load_universe_tickers(sector)
        if ticker not in peers:
            peers = [ticker] + peers
        rows = relative_strength.rank(peers, days=20)
        for i, r in enumerate(rows, start=1):
            if r["ticker"] == ticker:
                return i
    except Exception:
        return None
    return None


def gather_price(ticker: str, sector: Optional[str] = None) -> dict:
    try:
        bars = api.get_price_history(ticker, days=60)
    except Exception as e:
        return {"status": "unavailable", "reason": f"price_history: {e}"}

    last_close = bars[-1]["close"] if bars else None

    try:
        wyck = wyckoff.analyze_wyckoff(ticker)
        phase = getattr(wyck, "phase", None)
        structure = getattr(wyck, "structure", None)
        vol_pattern = getattr(wyck, "volume_pattern", None)
        confidence = getattr(wyck, "confidence", None)
        signals = getattr(wyck, "signals", [])
    except Exception:
        phase = structure = vol_pattern = confidence = None
        signals = []

    try:
        spring = spring_detector.detect(ticker)
        spring_hit = bool(spring.get("is_spring"))
        spring_conf = spring.get("confidence")
    except Exception:
        spring_hit = False
        spring_conf = None

    try:
        vp = vp_analyzer.classify(ticker, "1d")
        vp_state = vp.get("state") if isinstance(vp, dict) else None
    except Exception:
        vp_state = None

    try:
        rs_result = relative_strength.rank([ticker], days=20)
        rs_value = rs_result[0]["rs"] if rs_result else None
    except Exception:
        rs_value = None

    rs_rank = _rs_rank(ticker, sector)

    judge_floor = "strong" if (spring_hit and spring_conf in {"med", "medium", "high"}) else None
    vp_redflag = vp_state in {"weak_rally", "distribution"} and not spring_hit

    return {
        "bars_len": len(bars),
        "last_close": last_close,
        "wyckoff_phase": phase,
        "structure": structure,
        "volume_pattern": vol_pattern,
        "wyckoff_confidence": confidence,
        "wyckoff_signals": signals,
        "spring_hit": spring_hit,
        "spring_confidence": spring_conf,
        "vp_state": vp_state,
        "rs": rs_value,
        "rs_rank": rs_rank,
        "judge_floor": judge_floor,
        "vp_redflag": vp_redflag,
    }


# ─── dim 2: broker + SID + konglo ────────────────────────────────────────────

def _find_in_calcs(calcs: list, ticker: str) -> Optional[dict]:
    for row in calcs or []:
        if row.get("ticker") == ticker:
            return row
    return None


def gather_broker(ticker: str, hapcu_cache: dict, retail_cache: dict, l1_sectors: list[str]) -> dict:
    hapcu_row = _find_in_calcs((hapcu_cache or {}).get("calcs", []), ticker)
    retail_row = _find_in_calcs((retail_cache or {}).get("tickers", []), ticker)

    try:
        sid = sid_tracker.check_sid(ticker)
        sid_direction = getattr(sid, "direction", None) or getattr(sid, "intent", None)
        sid_streak = getattr(sid, "streak_days", None)
        sid_change = getattr(sid, "change_pct", None) or getattr(sid, "sid_change_pct", None)
    except Exception:
        sid_direction = None
        sid_streak = None
        sid_change = None

    try:
        bp = broker_profile.analyze_players(ticker)
        bp_insight = getattr(bp, "key_insight", None)
        top_buyers = getattr(bp, "top_buyers", None)
        if top_buyers:
            top_buyer_code = getattr(top_buyers[0], "code", None)
        else:
            smb = getattr(bp, "smart_money_buyers", []) or []
            top_buyer_code = smb[0] if smb else None
        top_sellers = getattr(bp, "top_sellers", None)
        if top_sellers:
            top_seller_code = getattr(top_sellers[0], "code", None)
        else:
            sms = getattr(bp, "smart_money_sellers", []) or []
            top_seller_code = sms[0] if sms else None
    except Exception:
        bp_insight = None
        top_buyer_code = None
        top_seller_code = None

    try:
        kgl = konglo_loader.group_for(ticker)
    except Exception:
        kgl = None
    kgl_sector = (kgl or {}).get("sector") if kgl else None
    sectors_norm = {s.lower() for s in (l1_sectors or [])}
    konglo_in_l1 = bool(kgl_sector and kgl_sector.lower() in sectors_norm)

    return {
        "hapcu_net_buy": hapcu_row.get("hapcu_net_buy") if hapcu_row else None,
        "foreign_net_buy": hapcu_row.get("foreign_net_buy") if hapcu_row else None,
        "retail_net_sell": retail_row.get("retail_net_sell") if retail_row else None,
        "smart_net_buy": retail_row.get("smart_net_buy") if retail_row else None,
        "retail_ratio": retail_row.get("ratio") if retail_row else None,
        "sid_direction": sid_direction,
        "sid_streak_days": sid_streak,
        "sid_change_pct": sid_change,
        "broker_insight": bp_insight,
        "top_buyer_code": top_buyer_code,
        "top_seller_code": top_seller_code,
        "konglo_group": (kgl or {}).get("name") if kgl else None,
        "konglo_sector": kgl_sector,
        "konglo_in_l1_sectors": konglo_in_l1,
    }


# ─── dim 3: yesterday bid / offer ────────────────────────────────────────────

def _orderbook_state_path(ticker: str) -> str:
    return str(ORDERBOOK_STATE_DIR / f"{ticker}.json")


def _latest_notes_path() -> Optional[str]:
    if not NOTES_DIR.exists():
        return None
    files = sorted(NOTES_DIR.glob("10m-*.jsonl"))
    return str(files[-1]) if files else None


def _top_walls(price_map: dict, k: int = 3) -> list[dict]:
    items = sorted(price_map.items(), key=lambda kv: float(kv[1]), reverse=True)[:k]
    return [{"price": float(p), "volume": int(v)} for p, v in items]


def gather_book(ticker: str) -> dict:
    state_path = _orderbook_state_path(ticker)
    p = pathlib.Path(state_path)
    if not p.exists():
        return {"status": "unavailable", "reason": f"no orderbook_state for {ticker}"}

    try:
        state = json.loads(p.read_text())
    except Exception as e:
        return {"status": "unavailable", "reason": f"state parse: {e}"}

    out = {
        "last_price": state.get("current_price"),
        "total_bid_volume": state.get("total_bid_volume"),
        "total_offer_volume": state.get("total_offer_volume"),
        "bid_walls_top3": _top_walls(state.get("bid_map", {}) or {}),
        "offer_walls_top3": _top_walls(state.get("offer_map", {}) or {}),
        "pressure_side": None,
        "stance": None,
        "score": None,
        "summary": None,
    }

    tbv = out["total_bid_volume"] or 0
    tov = out["total_offer_volume"] or 0
    if tbv and tov:
        out["pressure_side"] = "buyers" if tbv > tov else "sellers"

    notes_path = _latest_notes_path()
    if notes_path:
        try:
            with open(notes_path) as f:
                last_line = None
                for line in f:
                    if line.strip():
                        last_line = line
                if last_line:
                    data = json.loads(last_line)
                    for r in data.get("records", []):
                        if r.get("ticker") == ticker:
                            out["stance"] = r.get("stance")
                            out["score"] = r.get("score")
                            out["summary"] = r.get("summary")
                            break
        except Exception:
            pass

    return out


# ─── dim 4: narrative ────────────────────────────────────────────────────────

def gather_narrative(ticker: str, narratives: list[dict]) -> dict:
    for n in narratives or []:
        if (isinstance(n, dict) and n.get("ticker") == ticker) or getattr(n, "ticker", None) == ticker:
            get = n.get if isinstance(n, dict) else lambda k, d=None: getattr(n, k, d)
            return {
                "hit": True,
                "content": get("content"),
                "source": get("source"),
                "confidence": get("confidence"),
                "thesis_snippet": None,
            }
    return {"hit": False, "content": None, "source": None, "confidence": None, "thesis_snippet": None}
