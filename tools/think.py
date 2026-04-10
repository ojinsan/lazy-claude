"""
Lazyboy Trade Thinker v2 — Enhanced with Full Skills Integration
==============================================================

Thinking layer yang menggabungkan semua skills modules:
    - macro.py → Market regime
    - broker_profile.py → WHO is playing + intent
    - psychology.py → Behavior at S/R
    - sid_tracker.py → Shareholder intent
    - wyckoff.py → Phase detection
    - narrative.py → Story generator
    - journal.py → Learning from past

Usage:
    python3 think.py                          # Full scan + think
    python3 think.py --ticker ESSA            # Think on specific ticker
    python3 think.py --from-screener          # Read screener JSON from stdin
"""

import sys
import json
import subprocess
import httpx
import argparse
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from pathlib import Path

# Import skills lazily (they use relative imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

def _get_skill(name: str):
    """Lazy import a skill module."""
    import importlib.util
    skill_path = Path(__file__).parent.parent / "skills" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, skill_path)
    module = importlib.util.module_from_spec(spec)
    # Add skills dir to path for relative imports within skills
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))
    spec.loader.exec_module(module)
    return module

# Lazy-load skills when needed
_macro = None
_broker_profile = None
_psychology = None
_sid_tracker = None
_wyckoff = None
_narrative = None
_journal = None

def get_macro():
    global _macro
    if _macro is None:
        _macro = _get_skill("macro")
    return _macro

def get_broker_profile():
    global _broker_profile
    if _broker_profile is None:
        _broker_profile = _get_skill("broker_profile")
    return _broker_profile

def get_psychology():
    global _psychology
    if _psychology is None:
        _psychology = _get_skill("psychology")
    return _psychology

def get_sid_tracker():
    global _sid_tracker
    if _sid_tracker is None:
        _sid_tracker = _get_skill("sid_tracker")
    return _sid_tracker

def get_wyckoff():
    global _wyckoff
    if _wyckoff is None:
        _wyckoff = _get_skill("wyckoff")
    return _wyckoff

def get_narrative():
    global _narrative
    if _narrative is None:
        _narrative = _get_skill("narrative")
    return _narrative

def get_journal():
    global _journal
    if _journal is None:
        _journal = _get_skill("journal")
    return _journal

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_URL = "http://43.173.164.222:8080"
TOKEN = "6697ed8a65e1bf92bdbe4cd1aa2d64dcbeb91a0d9c39a35d0a245b830524fe92"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
WATERSEVEN_DIR = "/home/lazywork/bitstock/waterseven"

# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class TickerAnalysis:
    """Complete analysis for a ticker combining all skills."""
    ticker: str
    price: float = 0.0
    support: float = 0.0
    resistance: float = 0.0
    volume: int = 0
    avg_volume: float = 0.0
    vol_ratio: float = 0.0
    
    # From skills
    broker_analysis: Optional[PlayerAnalysis] = None
    psychology: Optional[PsychologyAnalysis] = None
    sid: Optional[SIDAnalysis] = None
    wyckoff: Optional[WyckoffAnalysis] = None
    narrative: Optional[StockNarrative] = None
    
    # Screener data
    remora_score: int = 50
    raw_screener: dict = field(default_factory=dict)
    
    # Derived
    conviction: str = "SKIP"
    adjusted_score: int = 50


# ─── API Helpers ──────────────────────────────────────────────────────────────

def api_get(path: str) -> dict:
    try:
        r = httpx.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_watchlist() -> list[str]:
    """Get watchlist from backend."""
    data = api_get("/watchlist")
    tickers = []
    seen = set()
    for item in data.get("data", []):
        t = item.get("stock", "")
        if t and item.get("status", "").lower() in ("watchlist", "watching") and t not in seen:
            tickers.append(t)
            seen.add(t)
    return tickers


def run_screener(tickers: Optional[list[str]] = None, top_n: int = 20, min_score: int = 50) -> list[dict]:
    """Run Remoratrader screener."""
    cmd = [
        "python3", "-m", "remoratrader.cli_runner",
        "screener",
        "--top-n", str(top_n),
        "--min-score", str(min_score),
    ]
    if tickers:
        cmd += ["--tickers", ",".join(tickers)]
    
    print(f"🔍 Running screener... ({len(tickers) if tickers else 'all'} tickers)", flush=True)
    result = subprocess.run(
        cmd,
        cwd=WATERSEVEN_DIR,
        capture_output=True,
        text=True,
        timeout=300
    )
    
    output = result.stdout.strip()
    if not output:
        print(f"⚠️  Screener produced no output. stderr: {result.stderr[:300]}")
        return []
    
    try:
        data = json.loads(output)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("results", data.get("tickers", [data]))
    except json.JSONDecodeError:
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("[") or line.strip().startswith("{"):
                try:
                    return json.loads("\n".join(lines[i:]))
                except:
                    pass
    
    print("⚠️  Could not parse screener output as JSON.")
    return []


def get_price_data(ticker: str) -> tuple[float, float, float, int, float]:
    """Fetch price, support, resistance, volume, avg_volume."""
    # Price
    price_data = api_get(f"/data/signal/current-price?ticker={ticker}")
    price = price_data.get("kwargs-after", {}).get("current_price", 0)
    
    # S/R
    sr_data = api_get(f"/data/signal/support-resistance?ticker={ticker}")
    sr = sr_data.get("kwargs-after", {})
    support = sr.get("current_support_value", 0)
    resistance = sr.get("current_resistance_value", 0)
    
    # Volume
    vol_data = api_get(f"/data/signal/volume?ticker={ticker}")
    volume = vol_data.get("kwargs-after", {}).get("volume", 0)
    
    # Avg volume
    avg_data = api_get(f"/data/signal/average-volume?ticker={ticker}")
    avg_volume = 0
    for k in ["average_volume", "avg_volume", "volume_avg", "avg"]:
        if k in avg_data.get("kwargs-after", {}):
            avg_volume = float(avg_data["kwargs-after"][k])
            break
    
    return price, support, resistance, volume, avg_volume


# ─── Full Analysis Pipeline ─────────────────────────────────────────────────────

def analyze_ticker(ticker: str, screener_data: dict = None, regime: MarketRegime = None) -> TickerAnalysis:
    """
    Run full analysis pipeline for a ticker using all skills.
    
    Pipeline:
    1. Fetch price data
    2. Broker profile analysis (WHO is playing)
    3. Psychology analysis (behavior at S/R)
    4. SID tracking (shareholder intent)
    5. Wyckoff analysis (phase detection)
    6. Generate narrative (combine all into story)
    7. Search past lessons (learning)
    """
    print(f"  → {ticker}", flush=True, end=" ")
    
    analysis = TickerAnalysis(ticker=ticker)
    
    # 1. Price data
    price, support, resistance, volume, avg_volume = get_price_data(ticker)
    analysis.price = price
    analysis.support = support
    analysis.resistance = resistance
    analysis.volume = volume
    analysis.avg_volume = avg_volume
    analysis.vol_ratio = volume / avg_volume if avg_volume > 0 else 0
    
    if screener_data:
        analysis.remora_score = screener_data.get("remora_score", 50)
        analysis.raw_screener = screener_data
    
    # 2. Broker profile (Layer 2)
    try:
        broker = get_broker_profile()
        analysis.broker_analysis = broker.analyze_players(ticker)
    except Exception as e:
        print(f"[broker error: {e}]", end=" ")
    
    # 3. Psychology at levels (Layer 2)
    try:
        psych = get_psychology()
        analysis.psychology = psych.analyze_psychology(ticker)
    except Exception as e:
        print(f"[psych error: {e}]", end=" ")
    
    # 4. SID tracking (Layer 2)
    try:
        sid_mod = get_sid_tracker()
        if screener_data:
            analysis.sid = sid_mod.check_sid_fast(ticker, screener_data)
        else:
            analysis.sid = sid_mod.check_sid(ticker)
    except Exception as e:
        print(f"[sid error: {e}]", end=" ")
    
    # 5. Wyckoff analysis (Layer 2)
    try:
        wyck = get_wyckoff()
        analysis.wyckoff = wyck.analyze_wyckoff(ticker, support, resistance)
    except Exception as e:
        print(f"[wyckoff error: {e}]", end=" ")
    
    # 6. Generate narrative (Layer 2→3)
    try:
        narr = get_narrative()
        analysis.narrative = narr.generate(
            ticker=ticker,
            broker_data=analysis.broker_analysis,
            psychology=analysis.psychology,
            sid=analysis.sid,
            wyckoff=analysis.wyckoff,
            macro_context=regime,
            price=price,
            support=support,
            resistance=resistance,
            volume_ratio=analysis.vol_ratio,
        )
    except Exception as e:
        print(f"[narrative error: {e}]", end=" ")
    
    # 7. Calculate conviction
    analysis.adjusted_score = int(analysis.remora_score * (regime.risk_multiplier if regime else 1.0))
    
    if analysis.adjusted_score >= 70:
        analysis.conviction = "HIGH"
    elif analysis.adjusted_score >= 58:
        analysis.conviction = "MEDIUM"
    elif analysis.adjusted_score >= 48:
        analysis.conviction = "WATCH"
    else:
        analysis.conviction = "SKIP"
    
    print(f"score={analysis.remora_score}→{analysis.adjusted_score} [{analysis.conviction}]", flush=True)
    
    return analysis


# ─── Report Formatting ────────────────────────────────────────────────────────

def format_full_report(
    analyses: List[TickerAnalysis],
    regime: MarketRegime,
    sector_rotation: dict = None
) -> str:
    """Format full analysis report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")
    
    lines = []
    lines.append(f"🧠 LAZYBOY DEEP THINK — {now}")
    lines.append("")
    
    # Market regime
    regime_emoji = {
        "BULL": "🟢", 
        "SIDEWAYS": "🟡", 
        "SIDEWAYS-BEARISH": "🟠", 
        "BEAR": "🔴", 
        "UNKNOWN": "⚪"
    }.get(regime.label, "⚪")
    lines.append(f"📊 MARKET: {regime_emoji} {regime.label} ({regime.confidence})")
    lines.append(f"   {regime.notes}")
    lines.append(f"   Risk multiplier: {regime.risk_multiplier:.2f}x")
    lines.append("")
    
    # Sector rotation
    if sector_rotation:
        hot = {s: d for s, d in sector_rotation.items() if d.get("trending")}
        if hot:
            lines.append("🎯 SECTOR ROTATION:")
            for sector, data in hot.items():
                lines.append(f"   • {sector}: {data.get('direction', 'neutral')}")
            lines.append("")
    
    # Group by conviction
    high = [a for a in analyses if a.conviction == "HIGH"]
    medium = [a for a in analyses if a.conviction == "MEDIUM"]
    watch = [a for a in analyses if a.conviction == "WATCH"]
    
    # HIGH CONVICTION
    if high:
        lines.append("━━━━━ 🔥 HIGH CONVICTION ━━━━━")
        for a in high:
            lines.append("")
            lines.append(f"📌 {a.ticker} — Score {a.remora_score} → {a.adjusted_score}")
            lines.append(f"   Price: {a.price:,.0f} | S: {a.support:,.0f} | R: {a.resistance:,.0f}")
            lines.append(f"   Vol: {a.vol_ratio:.1f}x")
            
            # Narrative (story)
            if a.narrative:
                lines.append(f"   💡 {a.narrative.story}")
                lines.append(f"   📖 {a.narrative.verdict}")
            
            # Broker key insight
            if a.broker_analysis and a.broker_analysis.key_insight:
                lines.append(f"   👥 {a.broker_analysis.key_insight}")
            
            # Psychology
            if a.psychology and a.psychology.summary:
                lines.append(f"   🧠 {a.psychology.summary}")
            
            # Wyckoff
            if a.wyckoff:
                lines.append(f"   📈 Phase: {a.wyckoff.phase}")
            
            # Trade plan if narrative exists
            if a.narrative and a.narrative.trade_plan:
                tp = a.narrative.trade_plan
                lines.append(f"   📋 PLAN: Entry {tp.entry_zone} | CL {tp.stop_loss} | Target {tp.target}")
    
    # MEDIUM CONVICTION
    if medium:
        lines.append("")
        lines.append("━━━━━ 👀 MEDIUM CONVICTION ━━━━━")
        for a in medium:
            lines.append(f"")
            lines.append(f"📌 {a.ticker} — Score {a.remora_score} → {a.adjusted_score}")
            lines.append(f"   Price: {a.price:,.0f} | S: {a.support:,.0f} | R: {a.resistance:,.0f}")
            if a.narrative:
                lines.append(f"   💡 {a.narrative.story}")
    
    # WATCH
    if watch:
        lines.append("")
        lines.append("━━━━━ 🕐 WATCH (not yet) ━━━━━")
        for a in watch:
            story = a.narrative.story[:60] if a.narrative else "No narrative"
            lines.append(f"• {a.ticker} ({a.remora_score}) — {story}")
    
    # No picks
    if not high and not medium:
        lines.append("")
        lines.append("⚠️ No high/medium conviction picks today.")
        lines.append("Market regime suppressing scores. Cash is a position.")
    
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚡ Lazyboy v2 | All Skills Integrated")
    
    return "\n".join(lines)


def format_thought_process(a: TickerAnalysis) -> str:
    """Format detailed thought process for a single ticker."""
    lines = []
    lines.append(f"🧠 THOUGHT PROCESS: {a.ticker}")
    lines.append("")
    
    # Data
    lines.append("📊 DATA:")
    lines.append(f"   Price: {a.price:,.0f} | Support: {a.support:,.0f} | Resistance: {a.resistance:,.0f}")
    lines.append(f"   Volume: {a.vol_ratio:.1f}x avg | Score: {a.remora_score} → {a.adjusted_score}")
    lines.append("")
    
    # Broker (WHO)
    if a.broker_analysis:
        lines.append("👥 BROKER FLOW:")
        lines.append(f"   {a.broker_analysis.key_insight}")
        if a.broker_analysis.smart_money_buyers:
            lines.append(f"   Smart buying: {', '.join(a.broker_analysis.smart_money_buyers[:3])}")
        if a.broker_analysis.retail_sellers:
            lines.append(f"   Retail selling: {', '.join(a.broker_analysis.retail_sellers[:3])}")
        lines.append("")
    
    # Psychology (BEHAVIOR)
    if a.psychology:
        lines.append("🧠 PSYCHOLOGY:")
        lines.append(f"   {a.psychology.summary}")
        if a.psychology.nearest_level:
            lines.append(f"   Nearest level: {a.psychology.nearest_level}")
        lines.append("")
    
    # SID (INTENT)
    if a.sid:
        lines.append("📜 SHAREHOLDER INTENT:")
        lines.append(f"   SID change: {a.sid.change_pct:+.1f}% → {a.sid.interpretation}")
        lines.append("")
    
    # Wyckoff (PHASE)
    if a.wyckoff:
        lines.append("📈 WYCKOFF:")
        lines.append(f"   Phase: {a.wyckoff.phase}")
        lines.append(f"   {a.wyckoff.interpretation}")
        lines.append("")
    
    # NARRATIVE (STORY)
    if a.narrative:
        lines.append("💡 NARRATIVE:")
        lines.append(f"   {a.narrative.story}")
        lines.append(f"   Verdict: {a.narrative.verdict}")
        if a.narrative.trade_plan:
            tp = a.narrative.trade_plan
            lines.append(f"   Entry: {tp.entry_zone} | Stop: {tp.stop_loss} | Target: {tp.target}")
        lines.append("")
    
    # LESSONS (LEARNING)
    try:
        journal = get_journal()
        lessons = journal.search_lessons(a.ticker)
        if lessons:
            lines.append("📚 PAST LESSONS:")
            for lesson in lessons[:2]:
                lines.append(f"   • {lesson.get('lesson', '')[:80]}")
            lines.append("")
    except:
        pass
    
    lines.append(f"━━━━ CONVICTION: {a.conviction} ━━━━")
    
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lazyboy Think Layer v2")
    parser.add_argument("--ticker", nargs="+", help="Specific tickers to analyze")
    parser.add_argument("--top-n", type=int, default=15, help="Top N from screener")
    parser.add_argument("--min-score", type=int, default=52, help="Min Remora score")
    parser.add_argument("--screener-json", type=str, help="Path to pre-run screener JSON")
    parser.add_argument("--thought", action="store_true", help="Output detailed thought process")
    args = parser.parse_args()
    
    print("🛋️  Lazyboy Thinker v2 starting...", flush=True)
    
    # 1. Get watchlist
    all_tickers = get_watchlist()
    target_tickers = args.ticker if args.ticker else None
    
    # 2. Run screener
    if args.screener_json:
        with open(args.screener_json) as f:
            screener_results = json.load(f)
    else:
        screener_results = run_screener(
            tickers=target_tickers,
            top_n=args.top_n,
            min_score=args.min_score
        )
    
    if not screener_results:
        print("❌ No screener results. Cannot proceed.")
        sys.exit(1)
    
    print(f"✅ Got {len(screener_results)} screener results", flush=True)
    
    # 3. Assess market regime (Layer 1)
    print("📊 Assessing market regime...", flush=True)
    try:
        macro = get_macro()
        regime = macro.assess_regime()
    except Exception as e:
        print(f"⚠️ Regime assessment failed: {e}, using last cached")
        try:
            macro = get_macro()
            regime = macro.get_last_regime()
        except:
            regime = type('MarketRegime', (), {
                'label': 'UNKNOWN',
                'confidence': 'LOW', 
                'risk_multiplier': 1.0,
                'notes': ''
            })()
    
    print(f"   → {regime.label} ({regime.confidence}) — {regime.notes}", flush=True)
    
    # 4. Detect sector rotation
    print("🎯 Detecting sector rotation...", flush=True)
    try:
        macro = get_macro()
        sector_rotation = macro.detect_sector_rotation()
    except Exception as e:
        print(f"⚠️ Sector rotation failed: {e}")
        sector_rotation = {}
    
    # 5. Analyze each ticker with full pipeline
    print(f"🔎 Running full analysis pipeline on {len(screener_results)} tickers...", flush=True)
    
    analyses = []
    for item in screener_results:
        ticker = item.get("ticker", item.get("stock", ""))
        if not ticker:
            continue
        
        analysis = analyze_ticker(ticker, screener_data=item, regime=regime)
        analyses.append(analysis)
    
    # 6. Sort by adjusted score
    analyses.sort(key=lambda a: a.adjusted_score, reverse=True)
    
    # 7. Output
    if args.thought and len(analyses) > 0:
        # Detailed thought process for first ticker
        print("\n" + format_thought_process(analyses[0]))
    else:
        # Full report
        report = format_full_report(analyses, regime, sector_rotation)
        print("\n" + "="*60)
        print(report)
        print("="*60)
    
    # 8. Save
    output_path = Path(__file__).parent / "last_think.txt"
    if args.thought and analyses:
        output = format_thought_process(analyses[0])
    else:
        output = format_full_report(analyses, regime, sector_rotation)
    
    with open(output_path, "w") as f:
        f.write(output)
    print(f"\n💾 Saved to {output_path}")


if __name__ == "__main__":
    main()
