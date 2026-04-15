"""
Lazyboy Screener — Morning/Evening Pipeline
=============================================
Layer 1 + Layer 2 screening with thought process.

Usage:
    python3 screener.py                        # Full scan (watchlist + sector rotation)
    python3 screener.py --tickers VKTR ESSA    # Specific tickers only
    python3 screener.py --layer1               # Layer 1 only (macro + sector)
    python3 screener.py --deep VKTR            # Deep dive single ticker (includes SID)

Flow:
    Layer 1: Macro regime → Sector rotation → Active theses
    Layer 2: For each candidate:
             → Player identification (broker profile)
             → Psychology at S/R levels
             → SID check (deep mode only, slow)
             → Narrative generation
    Output:  Ranked list with stories, not just scores

Note: SID is slow (~30s per ticker). Only used in --deep mode.
      For daily screening, broker_profile + psychology is enough.
"""

import sys
import os
import json
import csv
import re
import argparse
import logging
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent dir to path for skills imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from _lib import api
from _lib.broker_profile import analyze_players, format_analysis as fmt_players, save_snapshot
from _lib.psychology import analyze_psychology, format_analysis as fmt_psych
from _lib.sid_tracker import check_sid, format_analysis as fmt_sid
from _lib.wyckoff import analyze_wyckoff, format_wyckoff
from _lib.macro import (
    assess_regime, detect_sector_rotation, get_active_theses,
    save_thesis, SectorThesis, get_sector,
    format_regime, format_sector_rotation,
)
from _lib.market_structure import analyze_market_structure, format_analysis as fmt_structure
from _lib.narrative import generate, format_narrative, format_compact

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
WATCHLIST_FILE = Path("/home/lazywork/lazyboy/trade/watchlist/active.json")
STOCKLIST_FILE = Path("/home/lazywork/bitstock/waterseven/stocklist.csv")
OUTPUT_DIR = Path("/home/lazywork/lazyboy/trade/data")
MONITOR_INSIGHTS_FILE = OUTPUT_DIR / "monitor_insights.jsonl"

# Alert queue for sending to Mr O via heartbeat
ALERT_QUEUE = "/tmp/lazyboy_alert_queue.jsonl"


def load_watchlist() -> list[str]:
    """Load tickers from active watchlist."""
    if WATCHLIST_FILE.exists():
        data = json.loads(WATCHLIST_FILE.read_text())
        return [k for k in data.keys() if not k.startswith("_")]
    return []


def load_monitoring_insights() -> dict[str, dict]:
    """
    Load monitoring insights from 30-min batch data.
    
    Returns: {ticker: {price, pressure, pattern, signals, ...}}
    """
    insights = {}
    if not MONITOR_INSIGHTS_FILE.exists():
        return insights
    
    try:
        with open(MONITOR_INSIGHTS_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    ticker = entry.get("ticker", "")
                    if ticker:
                        # Keep the most recent entry per ticker
                        insights[ticker] = entry
                except:
                    continue
        
        if insights:
            print(f"📊 Loaded monitoring insights: {len(insights)} tickers", flush=True)
    except Exception as e:
        log.warning(f"Failed loading monitoring insights: {e}")
    
    return insights


def get_ticker_insight(ticker: str, insights: dict) -> dict:
    """Get insight for specific ticker, with defaults."""
    if not insights or ticker not in insights:
        return {}
    
    data = insights[ticker]
    return {
        "pressure": data.get("dominant_pressure", "NEUTRAL"),
        "orderbook": data.get("dominant_orderbook", "BALANCED"),
        "crossings": data.get("total_crossings", 0),
        "manipulation_count": data.get("manipulation_count", 0),
        "panic_count": data.get("panic_count", 0),
        "fomo_count": data.get("fomo_count", 0),
        "breakout_prob": data.get("max_breakout_prob", 0),
        "breakdown_prob": data.get("max_breakdown_prob", 0),
        "fake_walls": data.get("fake_wall_count", 0),
        "tektok_traps": data.get("tektok_trap_count", 0),
        "liquidity_sweeps": data.get("liquidity_sweep_count", 0),
        "sr_activity": data.get("dominant_sr_activity", ""),
    }


def load_stocklist_codes() -> set[str]:
    """Load valid ticker universe from stocklist.csv (waterseven reference)."""
    codes: set[str] = set()
    if not STOCKLIST_FILE.exists():
        return codes
    try:
        with open(STOCKLIST_FILE, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                code = str(row.get("code", "")).upper().strip()
                if re.fullmatch(r"[A-Z]{4}", code):
                    codes.add(code)
    except Exception as e:
        log.warning(f"Failed loading stocklist.csv: {e}")
    return codes


def load_api_watchlist() -> list[str]:
    """Load watchlist from backend API (/data/waterseven/strategy, /watchlist fallback)."""
    out: list[str] = []
    seen: set[str] = set()
    try:
        rows = api.get_watchlist()
        for row in rows:
            if not isinstance(row, dict):
                continue

            # Support multiple backend schemas
            t = (
                row.get("ticker")
                or row.get("stock")
                or row.get("symbol")
                or row.get("code")
                or row.get("emitten")
                or row.get("name")
                or ""
            )
            t = str(t).upper().strip()

            if not re.fullmatch(r"[A-Z]{4}", t):
                continue
            if t in seen:
                continue
            seen.add(t)
            out.append(t)
    except Exception as e:
        log.warning(f"Failed loading API watchlist: {e}")
    return out


def load_group_talk_tickers(days: int = 7, limit: int = 1200, top_n: int = 40) -> list[str]:
    """Get most talked tickers from insight feed (group chatter pulse)."""
    counter: Counter[str] = Counter()
    try:
        data = api._backend_get("/data/insight", {"limit": limit, "days": days})
        rows = data.get("data", data.get("results", [])) if isinstance(data, dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            t = str(row.get("ticker", "")).upper().strip()
            if re.fullmatch(r"[A-Z]{4}", t):
                counter[t] += 1
    except Exception as e:
        log.warning(f"Failed loading group talk tickers: {e}")
    return [t for t, _ in counter.most_common(top_n)]


def load_superlist_tickers() -> list[str]:
    """
    Load superlist tickers from Redis via waterseven CLI.

    Uses:
      python -m remoratrader.superlist_cli list <status>
    Statuses pulled: interesting, watching
    """
    out: list[str] = []
    base_cmd = ["python3", "-m", "remoratrader.superlist_cli", "list"]
    cwd = "/home/lazywork/bitstock/waterseven"

    # Host runtime uses Docker-published Redis on localhost by default.
    # If upstream env points to redis://redis:6379 (docker internal hostname),
    # CLI from host may fail with DNS error. Force safe host default here.
    env = os.environ.copy()
    env.setdefault("SUPERLIST_REDIS_URL", "redis://127.0.0.1:6379/0")

    for status in ("interesting", "watching"):
        try:
            cp = subprocess.run(
                [*base_cmd, status],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if cp.returncode != 0:
                err = (cp.stderr or cp.stdout or '').strip()
                log.warning(f"Superlist {status} unavailable: {err[:220]}")
                continue
            data = json.loads(cp.stdout or "{}")
            entries = data.get("entries", []) if isinstance(data, dict) else []
            for e in entries:
                if not isinstance(e, dict):
                    continue
                t = str(e.get("ticker", "")).upper().strip()
                if re.fullmatch(r"[A-Z]{4}", t):
                    out.append(t)
        except Exception as e:
            log.warning(f"Failed loading superlist {status}: {e}")

    return out


def build_narrative_universe(max_n: int = 100, min_new_ratio: float = 0.30) -> list[str]:
    """
    Build efficient universe (not all stocks) with anti-bias blending.

    Sources:
    1) Manual active watchlist
    2) API watchlist
    3) Group-talk hot tickers
    4) Superlist Redis (interesting + watching)

    Rule:
    - Keep continuity from active watchlist
    - Ensure at least `min_new_ratio` are "new" tickers
      (new = not in active watchlist)
    """
    active = [t.upper().strip() for t in load_watchlist() if t]
    active_set = set(active)

    api_wl = [t.upper().strip() for t in load_api_watchlist() if t]
    talked = [t.upper().strip() for t in load_group_talk_tickers() if t]
    superlist = [t.upper().strip() for t in load_superlist_tickers() if t]

    valid_codes = load_stocklist_codes()

    # Candidate pools
    new_pool = []
    old_pool = []
    seen_new = set()
    seen_old = set()

    # New candidates prioritized by discovery signal first
    for t in talked + api_wl + superlist:
        if valid_codes and t not in valid_codes:
            continue
        if t in active_set:
            if t not in seen_old:
                old_pool.append(t)
                seen_old.add(t)
        else:
            if t not in seen_new:
                new_pool.append(t)
                seen_new.add(t)

    # Ensure active watchlist continuity
    for t in active:
        if valid_codes and t not in valid_codes:
            continue
        if t not in seen_old:
            old_pool.append(t)
            seen_old.add(t)

    target_new = int(round(max_n * min_new_ratio))
    target_new = max(0, min(max_n, target_new))

    selected: list[str] = []
    selected_set = set()

    # 1) Fill mandatory new quota first
    for t in new_pool:
        if len(selected) >= target_new:
            break
        if t in selected_set:
            continue
        selected.append(t)
        selected_set.add(t)

    # 2) Fill remaining with old_pool (continuity)
    for t in old_pool:
        if len(selected) >= max_n:
            break
        if t in selected_set:
            continue
        selected.append(t)
        selected_set.add(t)

    # 3) If still not full, top-up from new_pool
    for t in new_pool:
        if len(selected) >= max_n:
            break
        if t in selected_set:
            continue
        selected.append(t)
        selected_set.add(t)

    if selected:
        actual_new = sum(1 for t in selected if t not in active_set)
        print(
            f"🧭 Universe source: active({len(active)}), api({len(api_wl)}), talk({len(talked)}), superlist({len(superlist)}) → {len(selected)} tickers | new: {actual_new}/{len(selected)} ({(actual_new/len(selected))*100:.0f}%)",
            flush=True,
        )

    return selected


def send_alert(message: str):
    """Write alert to queue for heartbeat delivery to Mr O."""
    import time
    try:
        with open(ALERT_QUEUE, "a") as f:
            f.write(json.dumps({
                "ts": time.time(),
                "ticker": "SCREENER",
                "key": "scan_result",
                "message": message,
                "read": False,
            }) + "\n")
    except Exception as e:
        print(f"Alert queue write failed: {e}", file=sys.stderr)


def run_layer1():
    """Layer 1: Macro regime + Sector rotation."""
    print("━━━ LAYER 1: MACRO & SECTOR ━━━", flush=True)
    print()
    
    # Market regime
    print("📊 Assessing market regime...", flush=True)
    regime = assess_regime()
    print(format_regime(regime))
    print()
    
    # Sector rotation (check key sectors)
    print("🔄 Scanning sector rotation...", flush=True)
    rotation = detect_sector_rotation([
        "COAL", "NICKEL", "OIL_GAS", "BANK", "PROPERTY",
        "SHIPPING", "CPO_AGRI", "ENERGY", "MINING_SERVICES",
    ])
    print(format_sector_rotation(rotation))
    print()
    
    # Hot sectors
    hot = {s: d for s, d in rotation.items() if d["hot"]}
    if hot:
        print("🔥 HOT SECTORS:")
        for sector, data in hot.items():
            print(f"  {sector}: {data['tickers_up']}/{data['tickers_checked']} trending up, vol {data['avg_volume_ratio']:.1f}x")
    else:
        print("⚠️ No clearly hot sectors detected.")
    
    print()
    
    # Active theses
    theses = get_active_theses()
    if theses:
        print("📋 Active Theses:")
        for t in theses:
            print(f"  • {t.sector} ({t.conviction}): {t.narrative[:100]}")
    
    return regime, rotation


def run_layer2(tickers: list[str], regime=None, include_sid: bool = False, insights: dict = None):
    """Layer 2: Full analysis for each ticker."""
    print()
    print("━━━ LAYER 2: STOCK ANALYSIS ━━━", flush=True)
    print(f"Analyzing {len(tickers)} tickers...", flush=True)
    print()
    
    results = []
    
    for ticker in tickers:
        print(f"▸ {ticker}...", flush=True, end=" ")
        
        # Player identification (enhanced)
        players = analyze_players(ticker)
        save_snapshot(ticker, players)
        
        # Psychology at S/R
        psych = analyze_psychology(ticker)
        
        # Market structure (NEW)
        structure = analyze_market_structure(ticker)
        
        # Wyckoff phase + SMI
        wyckoff = analyze_wyckoff(ticker)
        
        # SID (only in deep mode — slow)
        sid = None
        if include_sid:
            print("(SID...)", flush=True, end=" ")
            sid = check_sid(ticker)
        
        # Monitoring insights (NEW)
        monitor_data = get_ticker_insight(ticker, insights) if insights else {}
        
        # Generate narrative with all data
        narr = generate(
            ticker, 
            players=players, 
            psychology=psych, 
            sid=sid, 
            regime=regime, 
            wyckoff=wyckoff,
            structure=structure,
            monitor=monitor_data,
        )
        results.append(narr)
        
        print(f"→ {narr.verdict} ({narr.conviction})", flush=True)
    
    # Sort: BUY first, then WATCH, then AVOID. Within each, HIGH conviction first.
    verdict_order = {"BUY": 0, "WATCH": 1, "AVOID": 2}
    conviction_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    results.sort(key=lambda n: (verdict_order.get(n.verdict, 3), conviction_order.get(n.conviction, 3)))
    
    return results


def print_results(results, regime=None):
    """Print formatted results."""
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    now = datetime.now(WIB).strftime("%Y-%m-%d %H:%M WIB")
    print(f"🛋️ LAZYBOY SCAN — {now}", flush=True)
    
    if regime:
        emoji = {"BULL": "🟢", "SIDEWAYS": "🟡", "SIDEWAYS_BEARISH": "🟠", "BEAR": "🔴"}.get(regime.label, "⚪")
        print(f"Market: {emoji} {regime.label}", flush=True)
    
    print()
    
    buys = [r for r in results if r.verdict == "BUY"]
    watches = [r for r in results if r.verdict == "WATCH"]
    avoids = [r for r in results if r.verdict == "AVOID"]
    
    if buys:
        print("🟢 BUY CANDIDATES:", flush=True)
        for n in buys:
            print()
            print(format_narrative(n), flush=True)
    
    if watches:
        print()
        print("🟡 WATCHLIST:", flush=True)
        for n in watches:
            print()
            print(format_narrative(n), flush=True)
    
    if avoids:
        print()
        print("🔴 AVOID:", flush=True)
        for n in avoids:
            print(f"  {format_compact(n)}", flush=True)
    
    if not buys and not watches:
        print("⚠️ Nothing actionable today. Cash is a position.", flush=True)
    
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    
    return buys, watches, avoids


def save_results(results, regime=None):
    """Save scan results to file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now(WIB)
    output = {
        "timestamp": now.isoformat(),
        "regime": regime.label if regime else "UNKNOWN",
        "results": [
            {
                "ticker": n.ticker,
                "sector": n.sector,
                "layer": n.layer,
                "verdict": n.verdict,
                "conviction": n.conviction,
                "story": n.story,
                "green_flags": n.green_flags,
                "red_flags": n.red_flags,
            }
            for n in results
        ],
    }
    
    path = OUTPUT_DIR / "last_scan.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    
    # Also save human-readable
    lines = []
    for n in results:
        lines.append(format_narrative(n))
        lines.append("")
    
    text_path = OUTPUT_DIR / "last_scan.txt"
    text_path.write_text("\n".join(lines))


def run_preflight_check() -> tuple[bool, dict]:
    """
    Validate critical data sources before screening.
    
    Hard fail if core sources are unavailable so we don't run partial/biased scans.
    
    4-Group Watchlist Validation (MANDATORY):
    1. Local tracked watchlist
    2. API backend watchlist
    3. RAG search
    4. Stocklist market-attractive
    
    Additional: Superlist Redis (optional)
    """
    report = {}
    
    # Group 1: Local tracked
    local = load_watchlist()
    
    # Group 2: API watchlist backend
    api_wl = load_api_watchlist()
    
    # Group 3: RAG search
    rag_probe = api.rag_search(
        "idx market catalyst rups dividen akumulasi",
        top_n=5,
        min_confidence=0,
        max_days=90,
    )
    
    # Group 4: Stocklist (market-attractive tickers)
    stock_codes = load_stocklist_codes()
    
    # Build market-attractive subset (top 50 by volume/momentum)
    market_attractive = []
    if stock_codes:
        # For now, just use the stocklist as potential candidates
        market_attractive = list(stock_codes)[:50]  # Limit to 50
    
    # Additional discovery sources
    superlist = load_superlist_tickers()
    
    report["group1_local_count"] = len(local)
    report["group2_api_count"] = len(api_wl)
    report["group3_rag_count"] = len(rag_probe)
    report["group4_stocklist_count"] = len(stock_codes)
    report["superlist_count"] = len(superlist)
    
    # Check each group
    fails = []
    
    if len(local) == 0:
        fails.append("Group 1 (local watchlist) empty")
    if len(api_wl) == 0:
        fails.append("Group 2 (api watchlist) empty/unreachable")
    if len(rag_probe) == 0:
        fails.append("Group 3 (RAG search) returned 0")
    if len(stock_codes) == 0:
        fails.append("Group 4 (stocklist.csv) unavailable/empty")
    
    ok = len(fails) == 0
    report["status"] = "PASS" if ok else "FAIL"
    report["fails"] = fails
    
    print("🧪 Preflight Check — 4-Group Validation")
    print(f"  Group 1 (local):   {report['group1_local_count']}")
    print(f"  Group 2 (api):     {report['group2_api_count']}")
    print(f"  Group 3 (rag):     {report['group3_rag_count']}")
    print(f"  Group 4 (stocklist): {report['group4_stocklist_count']}")
    print(f"  Superlist (redis): {report['superlist_count']}")
    
    if not ok:
        print("❌ Preflight FAILED:")
        for f in fails:
            print(f"  - {f}")
        print("🛑 Screening stopped to avoid partial/biased output.")
    else:
        print("✅ Preflight PASSED — All 4 groups available")
    
    print()
    return ok, report


def main():
    parser = argparse.ArgumentParser(description="Lazyboy Screener")
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to analyze")
    parser.add_argument("--layer1", action="store_true", help="Layer 1 only (macro + sector)")
    parser.add_argument("--deep", nargs="+", help="Deep dive (includes SID, slow)")
    parser.add_argument("--max-universe", type=int, default=100, help="Max tickers for dynamic universe (default: 100)")
    parser.add_argument("--min-new-ratio", type=float, default=0.30, help="Minimum ratio of new tickers in dynamic universe")
    parser.add_argument("--alert", action="store_true", help="Send results to alert queue")
    parser.add_argument("--no-preflight", action="store_true", help="Skip preflight checks (not recommended)")
    args = parser.parse_args()
    
    print("🛋️ Lazyboy Screener starting...", flush=True)
    print()

    if not args.no_preflight:
        ok, _ = run_preflight_check()
        if not ok:
            return
    
    # Layer 1 (always)
    regime, rotation = run_layer1()
    
    if args.layer1:
        return
    
    # Determine tickers
    if args.deep:
        tickers = args.deep
        include_sid = True
    elif args.tickers:
        tickers = args.tickers
        include_sid = False
    else:
        # Default = efficient dynamic universe (not full stocklist)
        tickers = build_narrative_universe(
            max_n=max(10, min(300, args.max_universe)),
            min_new_ratio=max(0.0, min(0.9, args.min_new_ratio)),
        )
        include_sid = False

        # Fallback to active watchlist if dynamic sources are empty
        if not tickers:
            tickers = load_watchlist()
    
    if not tickers:
        print("⚠️ No tickers to analyze. Use --tickers or add to watchlist.", flush=True)
        return
    
    # Load monitoring insights (30-min batch data)
    insights = load_monitoring_insights()
    
    # Layer 2
    results = run_layer2(tickers, regime=regime, include_sid=include_sid, insights=insights)
    
    # Output
    buys, watches, avoids = print_results(results, regime=regime)
    save_results(results, regime=regime)
    
    # Alert if requested
    if args.alert and buys:
        summary_lines = [f"🛋️ Scan Complete — {len(buys)} BUY candidates:"]
        for n in buys:
            summary_lines.append(f"  🟢 {n.ticker} ({n.conviction}): {n.player_story[:80]}")
        send_alert("\n".join(summary_lines))


if __name__ == "__main__":
    main()


# ─── Daily Recap Integration ─────────────────────────────────────────────────

def load_yesterday_recap() -> dict:
    """
    Load yesterday's daily recap from monitor.
    
    Returns: {ticker: {pattern, signals, ...}}
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    
    WIB = ZoneInfo("Asia/Jakarta")
    yesterday = (datetime.now(WIB) - timedelta(days=1)).strftime("%Y-%m-%d")
    
    recap_file = f"/home/lazywork/lazyboy/trade/data/daily_recap_{yesterday}.json"
    
    if not Path(recap_file).exists():
        print(f"⚠️ No daily recap found for {yesterday}", flush=True)
        return {}
    
    try:
        with open(recap_file) as f:
            data = json.load(f)
        
        tickers = data.get("tickers", {})
        print(f"📖 Loaded yesterday's recap: {len(tickers)} tickers, {len(data.get('highlights', []))} highlights", flush=True)
        
        return tickers
    except Exception as e:
        print(f"⚠️ Failed to load recap: {e}", flush=True)
        return {}


def get_recap_signal_score(ticker: str, recap: dict) -> int:
    """
    Calculate signal score from yesterday's recap.
    
    Returns: 0-100 score based on recap signals.
    """
    if not recap or ticker not in recap:
        return 0
    
    data = recap[ticker]
    summary = data.get("session_summary", {})
    
    score = 0
    
    # Pattern bonuses
    pattern = summary.get("pattern", "")
    confidence = summary.get("pattern_confidence", "")
    
    if pattern == "ACCUMULATION":
        score += 30 if confidence == "HIGH" else 20
    elif pattern == "DISTRIBUTION":
        score -= 30 if confidence == "HIGH" else -20
    elif pattern == "MANIPULATION":
        score -= 20
    
    # Smart money behavior
    sm = summary.get("smart_money_behavior", "")
    if sm == "BUYING_INTO_WEAKNESS":
        score += 25
    elif sm == "PASSIVE_ACCUMULATION":
        score += 20
    elif sm == "SELLING_INTO_STRENGTH":
        score -= 25
    elif sm == "AGGRESSIVE_DISTRIBUTION":
        score -= 30
    
    # Next-day signals
    signals = summary.get("next_day_signals", [])
    for sig in signals:
        if sig == "WATCH_BREAKOUT":
            score += 15
        elif sig == "WATCH_BOUNCE":
            score += 10
        elif sig == "FOLLOW_SMART_MONEY_LONG":
            score += 20
        elif sig == "AVOID_LONG":
            score -= 25
        elif sig == "EXTRA_CAUTIOUS":
            score -= 10
    
    # Failed moves
    failed = summary.get("failed_moves", [])
    if "FAILED_BREAKDOWN" in failed:
        score += 15  # Failed breakdown = potential bounce
    if "FAILED_BREAKOUT" in failed:
        score -= 10  # Failed breakout = weakness
    
    return max(-50, min(50, score))  # Clamp to -50 to 50


# ─── End of screener.py additions ─────────────────────────────────────────────
