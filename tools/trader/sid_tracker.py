"""
SID Tracker — Shareholder Intent Detection
============================================
Layer 2 skill: Is this stock being drained (accumulated) or spread out (distributed)?

Mr O's insight: "SID meskipun jarang berubah, bisa liat saham lagi dikeringin"

SID change patterns:
- Fewer shareholders = consolidation = someone accumulating (draining float)
- More shareholders = distribution = shares being spread to retail
- Stable = no significant activity

This is a SLOW signal — doesn't change daily. But it reveals INTENT
that broker flow can hide (bandar can fake broker flow, harder to fake SID).
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import api

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

DATA_DIR = Path("/home/lazywork/workspace/vault/data")
SID_FILE = DATA_DIR / "sid_history.json"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class SIDAnalysis:
    """SID analysis for a ticker."""
    ticker: str
    timestamp: str = ""
    sid_change_pct: float = 0.0     # from remora screener
    
    # Interpretation
    intent: str = ""                # "accumulation" / "distribution" / "stable" / "unknown"
    narrative: str = ""             # human-readable explanation
    signal: str = ""                # "bullish" / "bearish" / "neutral"
    
    # Confirmation with broker flow
    broker_confirms: Optional[bool] = None  # does broker flow agree with SID?
    confirmation_note: str = ""


# ─── Analysis ─────────────────────────────────────────────────────────────────

def _interpret_sid(change_pct: float) -> tuple[str, str, str]:
    """Interpret SID change percentage.
    
    Returns: (intent, narrative, signal)
    """
    if change_pct <= -10:
        return (
            "strong_accumulation",
            f"SID {change_pct:+.1f}% — significant consolidation. Float being drained hard. "
            f"Someone is aggressively accumulating.",
            "bullish",
        )
    elif change_pct <= -3:
        return (
            "accumulation",
            f"SID {change_pct:+.1f}% — moderate consolidation. Fewer holders = shares concentrating "
            f"into stronger hands.",
            "bullish",
        )
    elif change_pct <= 3:
        return (
            "stable",
            f"SID {change_pct:+.1f}% — no significant change in shareholder base.",
            "neutral",
        )
    elif change_pct <= 15:
        return (
            "distribution",
            f"SID {change_pct:+.1f}% — more shareholders entering. Shares spreading to retail. "
            f"Someone distributing.",
            "bearish",
        )
    else:
        return (
            "heavy_distribution",
            f"SID {change_pct:+.1f}% — heavy distribution. Shares flooding to retail holders. "
            f"Smart money likely exiting.",
            "bearish",
        )


def check_sid(ticker: str) -> SIDAnalysis:
    """
    Check SID for a ticker using waterseven screener output.
    
    This calls the remora screener for a single ticker to get sid_change_pct.
    It's slow (~30s) but SID only needs checking once per day/week.
    """
    now = datetime.now(WIB)
    
    analysis = SIDAnalysis(
        ticker=ticker,
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
    )
    
    # Get SID from waterseven screener
    result = api.run_waterseven_screener([ticker], min_score=0, top_n=1)
    
    candidates = result.get("candidates", result.get("results", []))
    if not candidates:
        analysis.intent = "unknown"
        analysis.narrative = "Could not fetch SID data."
        analysis.signal = "neutral"
        return analysis
    
    candidate = candidates[0] if isinstance(candidates, list) else candidates
    sid_pct = candidate.get("sid_change_pct", 0)
    analysis.sid_change_pct = sid_pct
    
    # Interpret
    analysis.intent, analysis.narrative, analysis.signal = _interpret_sid(sid_pct)
    
    # Cross-check with broker flow
    is_accum = candidate.get("is_accumulation", False)
    is_dist = candidate.get("is_distribution", False)
    
    if analysis.intent in ("accumulation", "strong_accumulation") and is_accum:
        analysis.broker_confirms = True
        analysis.confirmation_note = "✅ Broker flow confirms SID accumulation pattern."
    elif analysis.intent in ("distribution", "heavy_distribution") and is_dist:
        analysis.broker_confirms = True
        analysis.confirmation_note = "✅ Broker flow confirms SID distribution pattern."
    elif analysis.intent in ("accumulation", "strong_accumulation") and is_dist:
        analysis.broker_confirms = False
        analysis.confirmation_note = (
            "⚠️ SID shows accumulation but broker flow shows distribution. "
            "Possible hidden accumulation through multiple accounts, or SID data is lagging."
        )
    elif analysis.intent in ("distribution", "heavy_distribution") and is_accum:
        analysis.broker_confirms = False
        analysis.confirmation_note = (
            "⚠️ SID shows distribution but broker flow shows accumulation. "
            "Possible fake accumulation (bandar distributing through retail-coded brokers)."
        )
    else:
        analysis.broker_confirms = None
        analysis.confirmation_note = "No strong confirmation either way."
    
    # Save snapshot
    save_snapshot(ticker, analysis)
    
    return analysis


def check_sid_fast(ticker: str, screener_data: dict) -> SIDAnalysis:
    """
    Fast SID check using pre-fetched screener data.
    Use this when you already ran the screener and have the result.
    """
    now = datetime.now(WIB)
    sid_pct = screener_data.get("sid_change_pct", 0)
    
    analysis = SIDAnalysis(
        ticker=ticker,
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        sid_change_pct=sid_pct,
    )
    
    analysis.intent, analysis.narrative, analysis.signal = _interpret_sid(sid_pct)
    
    is_accum = screener_data.get("is_accumulation", False)
    is_dist = screener_data.get("is_distribution", False)
    
    if analysis.intent in ("accumulation", "strong_accumulation") and is_accum:
        analysis.broker_confirms = True
        analysis.confirmation_note = "✅ Broker flow confirms SID accumulation."
    elif analysis.intent in ("distribution", "heavy_distribution") and is_dist:
        analysis.broker_confirms = True
        analysis.confirmation_note = "✅ Broker flow confirms SID distribution."
    elif analysis.intent in ("accumulation", "strong_accumulation") and is_dist:
        analysis.broker_confirms = False
        analysis.confirmation_note = "⚠️ SID=accumulation but broker=distribution. Contradictory."
    elif analysis.intent in ("distribution", "heavy_distribution") and is_accum:
        analysis.broker_confirms = False
        analysis.confirmation_note = "⚠️ SID=distribution but broker=accumulation. Possible fake."
    
    return analysis


# ─── Persistence ──────────────────────────────────────────────────────────────

def save_snapshot(ticker: str, analysis: SIDAnalysis):
    """Save SID snapshot for historical tracking."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    history = {}
    if SID_FILE.exists():
        try:
            history = json.loads(SID_FILE.read_text())
        except:
            history = {}
    
    if ticker not in history:
        history[ticker] = []
    
    snapshot = {
        "timestamp": analysis.timestamp,
        "sid_change_pct": analysis.sid_change_pct,
        "intent": analysis.intent,
        "signal": analysis.signal,
        "broker_confirms": analysis.broker_confirms,
    }
    
    history[ticker].append(snapshot)
    history[ticker] = history[ticker][-20:]  # keep last 20
    
    SID_FILE.write_text(json.dumps(history, indent=2))


def get_sid_trend(ticker: str) -> list[dict]:
    """Get SID history for a ticker."""
    if not SID_FILE.exists():
        return []
    try:
        history = json.loads(SID_FILE.read_text())
        return history.get(ticker, [])
    except:
        return []


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_analysis(a: SIDAnalysis) -> str:
    """Format SID analysis for display."""
    signal_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(a.signal, "⚪")
    
    lines = []
    lines.append(f"📊 {a.ticker} SID Analysis — {a.timestamp}")
    lines.append(f"  {signal_icon} {a.narrative}")
    if a.confirmation_note:
        lines.append(f"  {a.confirmation_note}")
    
    return "\n".join(lines)
