"""
Lazyboy Trade Plan Generator
==============================
Layer 3: Generate actionable trade plan for a specific ticker.

Usage:
    python3 tradeplan.py ESSA
    python3 tradeplan.py ESSA --entry 750 --cl 720 --tp 830
    python3 tradeplan.py ESSA --portfolio 100000000 --risk 2

Outputs: entry zone, target, cut loss, position size, R:R, conviction.
Incorporates all Layer 2 analysis into the plan.
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from _lib import api
from _lib.broker_profile import analyze_players, format_analysis as fmt_players
from _lib.psychology import analyze_psychology, format_analysis as fmt_psych
from _lib.wyckoff import analyze_wyckoff, format_wyckoff
from _lib.narrative import generate, format_narrative
from _lib.journal import search_lessons

WIB = ZoneInfo("Asia/Jakarta")
from config import ensure_watchlist_file
WATCHLIST_FILE = ensure_watchlist_file()

# Default from SYSTEM.md
DEFAULT_PORTFOLIO = 100_000_000  # 100M IDR
DEFAULT_RISK_PCT = 2.0           # 2% risk per trade


def generate_plan(
    ticker: str,
    entry: float = None,
    cl: float = None,
    tp: float = None,
    portfolio: float = DEFAULT_PORTFOLIO,
    risk_pct: float = DEFAULT_RISK_PCT,
):
    """Generate a complete trade plan."""
    
    # Fetch data
    print(f"📋 Trade Plan: {ticker}", flush=True)
    print(f"{'='*40}", flush=True)
    
    # Layer 2 analysis
    print("Analyzing players...", flush=True)
    players = analyze_players(ticker)
    print("Analyzing psychology...", flush=True)
    psych = analyze_psychology(ticker)
    print("Analyzing Wyckoff phase...", flush=True)
    wyckoff = analyze_wyckoff(ticker)
    
    narr = generate(ticker, players=players, psychology=psych, wyckoff=wyckoff)
    
    current_price = narr.current_price
    sr = api.get_support_resistance(ticker)
    vol_ratio = api.get_volume_ratio(ticker)
    
    # Determine levels
    if entry is None:
        # Use current price or support zone
        if sr.support > 0 and current_price > sr.support:
            entry = round(sr.support * 1.01)  # slightly above support
        else:
            entry = current_price
    
    if cl is None:
        if sr.support > 0:
            cl = round(sr.support * 0.97)  # below support
        else:
            cl = round(entry * 0.95)  # 5% below entry
    
    if tp is None:
        if sr.resistance > 0:
            tp = sr.resistance
        else:
            tp = round(entry * 1.10)  # 10% above entry
    
    # Risk/Reward
    risk_per_share = entry - cl
    reward_per_share = tp - entry
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
    
    # Position sizing
    max_risk = portfolio * (risk_pct / 100)
    shares = int(max_risk / risk_per_share) if risk_per_share > 0 else 0
    shares = (shares // 100) * 100  # round to lots (100 shares)
    position_value = shares * entry
    
    # Conviction-based max from SYSTEM.md
    conviction_limits = {
        "HIGH": 30_000_000,
        "MEDIUM": 15_000_000,
        "LOW": 0,
    }
    max_size = conviction_limits.get(narr.conviction, 0)
    if position_value > max_size and max_size > 0:
        shares = int(max_size / entry)
        shares = (shares // 100) * 100
        position_value = shares * entry
    
    # Past lessons
    lessons = search_lessons(ticker)
    
    # Output
    print()
    print(format_narrative(narr))
    print()
    print(format_wyckoff(wyckoff))
    print()
    print(f"{'─'*40}")
    print(f"📌 TRADE PLAN")
    print(f"  Entry:    {entry:.0f}")
    print(f"  Target:   {tp:.0f} (+{((tp-entry)/entry*100):.1f}%)")
    print(f"  Cut Loss: {cl:.0f} (-{((entry-cl)/entry*100):.1f}%)")
    print(f"  R:R:      1:{rr_ratio:.1f}")
    print(f"  Volume:   {api.vol_label(vol_ratio)}")
    print()
    print(f"💰 POSITION SIZE")
    print(f"  Portfolio:  {portfolio/1e6:.0f}M IDR")
    print(f"  Risk:       {risk_pct}% = {max_risk/1e6:.1f}M IDR")
    print(f"  Shares:     {shares:,} ({shares//100} lots)")
    print(f"  Value:      {position_value/1e6:.1f}M IDR")
    print(f"  Conviction: {narr.conviction}")
    
    if narr.conviction == "LOW" or narr.verdict == "AVOID":
        print(f"  ⚠️ LOW conviction or AVOID verdict — consider skipping")
    
    # Past lessons
    if lessons:
        print()
        print(f"📝 PAST LESSONS ({ticker}):")
        for l in lessons[-3:]:
            print(f"  • [{l['category']}] {l['lesson'][:100]}")
    
    print()
    print(f"{'─'*40}")
    
    # Entry conditions checklist
    print("✅ ENTRY CHECKLIST:")
    print(f"  {'✓' if current_price <= entry * 1.02 else '✗'} Price in zone ({current_price:.0f} vs entry {entry:.0f})")
    print(f"  {'✓' if vol_ratio >= 1.3 else '✗'} Volume confirmed ({vol_ratio:.1f}x, need ≥1.3x)")
    print(f"  {'✓' if narr.verdict != 'AVOID' else '✗'} Narrative OK ({narr.verdict})")
    print(f"  {'✓' if rr_ratio >= 1.5 else '✗'} R:R acceptable (1:{rr_ratio:.1f}, need ≥1:1.5)")
    print(f"  {'✓' if not players.trap_detected or players.trap_type != 'distribution_trap' else '✗'} No distribution trap")
    
    all_ok = (
        current_price <= entry * 1.02 and
        vol_ratio >= 1.3 and
        narr.verdict != "AVOID" and
        rr_ratio >= 1.5 and
        not (players.trap_detected and players.trap_type == "distribution_trap")
    )
    
    print()
    if all_ok:
        print("🟢 ALL CHECKS PASSED — Ready to execute")
    else:
        print("🟡 NOT ALL CHECKS PASSED — Review before entry")
    
    # Save to watchlist
    _update_watchlist(ticker, narr, entry, cl, tp, shares)
    
    return {
        "ticker": ticker,
        "entry": entry,
        "target": tp,
        "cut_loss": cl,
        "rr": rr_ratio,
        "shares": shares,
        "value": position_value,
        "conviction": narr.conviction,
        "verdict": narr.verdict,
        "all_checks_passed": all_ok,
    }


def _update_watchlist(ticker, narr, entry, cl, tp, shares):
    """Update watchlist with trade plan."""
    if not WATCHLIST_FILE.exists():
        return
    
    data = json.loads(WATCHLIST_FILE.read_text())
    if ticker not in data:
        data[ticker] = {}
    
    data[ticker].update({
        "layer": 3,
        "last_updated": datetime.now(WIB).strftime("%Y-%m-%d"),
        "narrative": narr.story,
        "trade_plan": {
            "entry_zone": [entry * 0.98, entry],
            "target": tp,
            "cut_loss": cl,
            "conviction": narr.conviction,
            "shares": shares,
        },
        "status": "ready" if narr.verdict == "BUY" else "watching",
    })
    
    WATCHLIST_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    # M2.5 dual-write
    try:
        import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.fund_api import api as _api
        from datetime import datetime
        tp_plan = data[-1]
        _api.post_tradeplan({
            "plan_date": datetime.now().strftime("%Y-%m-%d"),
            "ticker": tp_plan.get("ticker", ""),
            "mode": "full",
            "entry_low": tp_plan.get("trade_plan", {}).get("entry_zone", [0, 0])[0],
            "entry_high": tp_plan.get("trade_plan", {}).get("entry_zone", [0, 0])[1],
            "stop": tp_plan.get("trade_plan", {}).get("cut_loss", 0),
            "target_1": tp_plan.get("trade_plan", {}).get("target", 0),
            "size_shares": tp_plan.get("trade_plan", {}).get("shares", 0),
            "conviction": tp_plan.get("trade_plan", {}).get("conviction", ""),
            "level": "local",
            "status": tp_plan.get("status", "draft"),
            "raw_md": str(tp_plan),
            "created_at": datetime.now().isoformat(),
        })
    except Exception as _e:
        pass


def main():
    parser = argparse.ArgumentParser(description="Lazyboy Trade Plan")
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument("--entry", type=float, help="Entry price")
    parser.add_argument("--cl", type=float, help="Cut loss price")
    parser.add_argument("--tp", type=float, help="Target price")
    parser.add_argument("--portfolio", type=float, default=DEFAULT_PORTFOLIO, help="Portfolio size (IDR)")
    parser.add_argument("--risk", type=float, default=DEFAULT_RISK_PCT, help="Risk per trade (%)")
    args = parser.parse_args()
    
    generate_plan(
        args.ticker,
        entry=args.entry,
        cl=args.cl,
        tp=args.tp,
        portfolio=args.portfolio,
        risk_pct=args.risk,
    )


if __name__ == "__main__":
    main()
