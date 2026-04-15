#!/usr/bin/env python3
"""
Evaluation Mode Pipeline (persistent)

Flow:
1) Layer 1 context save (market/sector/narrative/news/MSCI notes)
2) Screening universe (default max 100)
3) Health check (min pass 30) with SID + trend
4) Layer 2 one-by-one checks
5) Top 10 shortlist
6) Deep thinking pick best 5
7) Save artifacts for heartbeat/monitoring
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import screener
from _lib import api
from _lib.broker_profile import analyze_players
from _lib.psychology import analyze_psychology
from _lib.sid_tracker import get_sid_trend, check_sid
from _lib.wyckoff import analyze_wyckoff

WIB = ZoneInfo("Asia/Jakarta")
DATA_DIR = Path("/home/lazywork/lazyboy/trade/data/eval")
CFG_PATH = DATA_DIR / "eval_config.json"
LATEST_PATH = DATA_DIR / "latest.json"


@dataclass
class HealthRow:
    ticker: str
    score: int
    passed: bool
    trend_ok: bool
    sid_dry_ok: bool
    liquidity_ok: bool
    flow_ok: bool
    trend_note: str
    sid_note: str
    flow_note: str


def load_config() -> dict:
    default = {
        "max_universe": 100,
        "min_health_pass": 30,
        "top_n": 10,
        "pick_n": 5,
        "enable_live_sid": False,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CFG_PATH.exists():
        CFG_PATH.write_text(json.dumps(default, indent=2))
        return default
    try:
        raw = json.loads(CFG_PATH.read_text())
        return {**default, **raw}
    except Exception:
        return default


def today_stamp() -> str:
    return datetime.now(WIB).strftime("%Y%m%d_%H%M")


def trend_signal(ticker: str) -> tuple[bool, str]:
    tr = api.get_trend(ticker)
    # backend payload varies; keep robust
    txt = json.dumps(tr).lower()
    if "uptrend" in txt or ("hh" in txt and "hl" in txt):
        return True, "trend up / HH-HL bias"
    if "downtrend" in txt or ("lh" in txt and "ll" in txt):
        return False, "trend down / LH-LL bias"

    wy = analyze_wyckoff(ticker)
    phase = str(getattr(wy, "phase", "")).lower()
    if "markup" in phase or "accum" in phase:
        return True, f"wyckoff {phase}"
    if "markdown" in phase:
        return False, f"wyckoff {phase}"
    return False, "trend unclear"


def sid_dry_signal(ticker: str, enable_live_sid: bool) -> tuple[bool, str]:
    hist = get_sid_trend(ticker)
    if hist:
        last = hist[-1]
        pct = float(last.get("sid_change_pct", 0))
        if pct <= -3:
            return True, f"SID drying {pct:+.1f}%"
        if pct > 3:
            return False, f"SID spreading {pct:+.1f}%"
        return False, f"SID flat {pct:+.1f}%"

    if enable_live_sid:
        try:
            sid = check_sid(ticker)
            pct = float(getattr(sid, "sid_change_pct", 0.0))
            if pct <= -3:
                return True, f"SID live drying {pct:+.1f}%"
            return False, f"SID live not drying {pct:+.1f}%"
        except Exception as e:
            return False, f"SID live fail: {e}"

    return False, "SID unknown (no history)"


def health_check(ticker: str, enable_live_sid: bool = False) -> HealthRow:
    trend_ok, trend_note = trend_signal(ticker)
    sid_ok, sid_note = sid_dry_signal(ticker, enable_live_sid)

    vr = api.get_volume_ratio(ticker)
    liquidity_ok = vr >= 0.4

    rt = api.analyze_running_trades(ticker, limit=80)
    pattern = str(rt.get("pattern", "unknown"))
    flow_ok = pattern in ("institutional_accumulation", "buying_pressure", "mixed")

    score = int(trend_ok) + int(sid_ok) + int(liquidity_ok) + int(flow_ok)
    passed = score >= 2 and (trend_ok or sid_ok)

    return HealthRow(
        ticker=ticker,
        score=score,
        passed=passed,
        trend_ok=trend_ok,
        sid_dry_ok=sid_ok,
        liquidity_ok=liquidity_ok,
        flow_ok=flow_ok,
        trend_note=trend_note,
        sid_note=sid_note,
        flow_note=f"{pattern}, vol_ratio={vr:.2f}",
    )


def layer2_eval(ticker: str) -> dict:
    players = analyze_players(ticker)
    psych = analyze_psychology(ticker)
    sr = api.get_support_resistance(ticker)
    rt = api.analyze_running_trades(ticker, limit=120)
    sb_rt = api.get_stockbit_running_trade(ticker, limit=120)
    rag = api.rag_search(f"{ticker} catalyst outlook rups dividen corporate action", ticker=ticker, top_n=3, min_confidence=20, max_days=45)

    negotiated = 0
    if isinstance(sb_rt, dict):
        negotiated = int(sb_rt.get("summary", {}).get("negotiated_count", 0))

    # simple behavior notes
    sr_behavior = f"S={sr.support:.0f}, R={sr.resistance:.0f}; {getattr(psych, 'story', '')[:120]}"
    bandar_behavior = getattr(players, "story", "")[:180]
    sponsor_intent = "unknown"
    if "underwater" in bandar_behavior.lower() or "vested interest" in bandar_behavior.lower():
        sponsor_intent = "push_up"
    elif "distrib" in bandar_behavior.lower():
        sponsor_intent = "distribute"

    catalyst = []
    for r in rag[:2]:
        txt = (r.get("ai_recap") or r.get("title") or "").strip()
        if txt:
            catalyst.append(txt[:140])

    score = 0
    score += 1 if sponsor_intent == "push_up" else 0
    score += 1 if rt.get("pattern") in ("institutional_accumulation", "buying_pressure") else 0
    score += 1 if sr.resistance > 0 and sr.support > 0 else 0
    score += 1 if len(catalyst) > 0 else 0
    score += 1 if negotiated > 0 else 0

    return {
        "ticker": ticker,
        "l2_score": score,
        "support_resistance_behavior": sr_behavior,
        "bandar_behavior": bandar_behavior,
        "running_trade_pattern": rt,
        "crossing_hint": f"negotiated_trades={negotiated}",
        "catalyst": catalyst,
        "sponsor_intent": sponsor_intent,
    }


def deep_pick(row: dict) -> dict:
    t = row["ticker"]
    sponsor = row.get("sponsor_intent", "unknown")
    rt_pat = row.get("running_trade_pattern", {}).get("pattern", "unknown")
    has_cat = len(row.get("catalyst", [])) > 0

    own_now = sponsor in ("push_up",) and rt_pat in ("institutional_accumulation", "buying_pressure")
    why_now = has_cat or "negotiated" in row.get("crossing_hint", "")
    momentum_quality = rt_pat not in ("selling_pressure", "retail_noise")

    verdict = "WATCH"
    if own_now and why_now and momentum_quality:
        verdict = "INVESTABLE"
    elif not momentum_quality:
        verdict = "REJECT"

    return {
        "ticker": t,
        "verdict": verdict,
        "thesis": f"{t}: sponsor={sponsor}, flow={rt_pat}",
        "why_now": "catalyst/crossing present" if why_now else "timing weak",
        "sponsor_intent": sponsor,
        "risk_invalidation": "flow shifts to selling_pressure or resistance rejection",
        "action": "starter" if verdict == "INVESTABLE" else ("watch" if verdict == "WATCH" else "pass"),
    }


def main():
    cfg = load_config()
    stamp = today_stamp()

    ok, preflight = screener.run_preflight_check()
    if not ok:
        out = {"status": "FAIL", "preflight": preflight, "ts": stamp}
        (DATA_DIR / f"eval_fail_{stamp}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        print("❌ Preflight failed")
        return

    regime, rotation = screener.run_layer1()
    layer1_ctx = {
        "ts": stamp,
        "market_conditions": {"label": regime.label, "confidence": regime.confidence, "risk_multiplier": regime.risk_multiplier, "notes": regime.notes},
        "sector_rotation": rotation,
        "interesting_narrative": api.rag_search("IDX catalyst narrative rups dividen msci rebalance", top_n=5, min_confidence=20, max_days=45),
        "news": api.rag_search("IDX today important market news", top_n=5, min_confidence=20, max_days=7),
        "msci": api.rag_search("MSCI Indonesia rebalance IDX", top_n=5, min_confidence=20, max_days=120),
        "preflight": preflight,
    }

    universe = screener.build_narrative_universe(max_n=int(cfg["max_universe"]))
    print(f"\nUniverse selected: {len(universe)}")

    health_rows = []
    for t in universe:
        hr = health_check(t, enable_live_sid=bool(cfg.get("enable_live_sid", False)))
        health_rows.append(asdict(hr))

    passed = [r for r in health_rows if r["passed"]]
    passed.sort(key=lambda x: (-x["score"], x["ticker"]))

    if len(passed) < int(cfg["min_health_pass"]):
        print(f"⚠️ Health pass {len(passed)} below target {cfg['min_health_pass']}")

    layer2_rows = []
    for r in passed[: max(int(cfg["min_health_pass"]), 30)]:
        t = r["ticker"]
        print(f"L2 → {t}")
        layer2_rows.append(layer2_eval(t))

    layer2_rows.sort(key=lambda x: (-x["l2_score"], x["ticker"]))
    top10 = layer2_rows[: int(cfg["top_n"])]

    deep = [deep_pick(x) for x in top10]
    deep.sort(key=lambda x: (0 if x["verdict"] == "INVESTABLE" else (1 if x["verdict"] == "WATCH" else 2), x["ticker"]))
    pick5 = deep[: int(cfg["pick_n"])]

    bundle = {
        "ts": stamp,
        "config": cfg,
        "layer1": layer1_ctx,
        "universe_count": len(universe),
        "health": {"count": len(health_rows), "passed": len(passed), "rows": health_rows},
        "top10": top10,
        "pick5": pick5,
    }

    (DATA_DIR / f"layer1_{stamp}.json").write_text(json.dumps(layer1_ctx, indent=2, ensure_ascii=False))
    (DATA_DIR / f"health_{stamp}.json").write_text(json.dumps({"rows": health_rows, "passed": len(passed)}, indent=2, ensure_ascii=False))
    (DATA_DIR / f"top10_{stamp}.json").write_text(json.dumps(top10, indent=2, ensure_ascii=False))
    (DATA_DIR / f"pick5_{stamp}.json").write_text(json.dumps(pick5, indent=2, ensure_ascii=False))
    LATEST_PATH.write_text(json.dumps(bundle, indent=2, ensure_ascii=False))

    print("\n✅ Evaluation pipeline complete")
    print(f"Health pass: {len(passed)}")
    print(f"Top10: {', '.join([x['ticker'] for x in top10])}")
    print(f"Pick5: {', '.join([x['ticker'] for x in pick5])}")


if __name__ == "__main__":
    main()
