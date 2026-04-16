"""
Market Structure — Price Structure Analysis
============================================
Layer 2 skill: WHAT is the market doing?

Key concepts:
- Swing High/Low detection
- Trend structure (HH/HL = uptrend, LH/LL = downtrend)
- Support/Resistance from swing points
- Wyckoff phase estimation
- Break of Structure (BOS)
- Change of Character (CHoCH)

Mr O's principle: "Structure before indicator. Read the chart."
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json

import api

log = logging.getLogger(__name__)

DATA_DIR = Path("/home/lazywork/workspace/vault/data")


@dataclass
class SwingPoint:
    """A swing high or low point."""
    price: float
    time: str
    type: str  # "high" or "low"
    strength: int = 1  # 1-5, how significant


@dataclass
class MarketStructure:
    """Market structure analysis result."""
    ticker: str
    current_price: float = 0.0
    
    # Trend
    trend: str = "neutral"  # "uptrend" / "downtrend" / "neutral" / "ranging"
    trend_strength: int = 0  # 0-5
    
    # Structure
    last_swing_high: Optional[SwingPoint] = None
    last_swing_low: Optional[SwingPoint] = None
    higher_highs: bool = False
    higher_lows: bool = False
    lower_highs: bool = False
    lower_lows: bool = False
    
    # Key levels
    resistance: float = 0.0
    support: float = 0.0
    resistance_strength: int = 0  # 0-5
    support_strength: int = 0  # 0-5
    
    # Wyckoff phase
    wyckoff_phase: str = "unknown"  # "accumulation" / "markup" / "distribution" / "markdown"
    wyckoff_position: str = ""  # "spring" / "sos" / "lps" / "utad" etc.
    
    # Structure events
    bos_detected: bool = False  # Break of Structure
    bos_direction: str = ""  # "bullish" / "bearish"
    choch_detected: bool = False  # Change of Character
    choch_direction: str = ""  # "bullish" / "bearish"
    
    # Position relative to structure
    price_position: str = ""  # "above_resistance" / "below_support" / "in_range" / "at_resistance" / "at_support"
    distance_to_resistance_pct: float = 0.0
    distance_to_support_pct: float = 0.0
    
    # Summary
    structure_story: str = ""


def detect_swing_points(highs: list[float], lows: list[float], lookback: int = 3) -> tuple[list[SwingPoint], list[SwingPoint]]:
    """
    Detect swing highs and lows using simple fractal method.
    
    Swing High = high surrounded by lower highs on both sides
    Swing Low = low surrounded by higher lows on both sides
    """
    swing_highs = []
    swing_lows = []
    
    if len(highs) < lookback * 2 + 1 or len(lows) < lookback * 2 + 1:
        return swing_highs, swing_lows
    
    for i in range(lookback, len(highs) - lookback):
        # Check for swing high
        is_swing_high = True
        for j in range(1, lookback + 1):
            if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                is_swing_high = False
                break
        
        if is_swing_high:
            strength = min(5, lookback)
            swing_highs.append(SwingPoint(
                price=highs[i],
                time="",  # Would need timestamps
                type="high",
                strength=strength,
            ))
        
        # Check for swing low
        is_swing_low = True
        for j in range(1, lookback + 1):
            if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                is_swing_low = False
                break
        
        if is_swing_low:
            strength = min(5, lookback)
            swing_lows.append(SwingPoint(
                price=lows[i],
                time="",
                type="low",
                strength=strength,
            ))
    
    return swing_highs, swing_lows


def analyze_trend_structure(swing_highs: list[SwingPoint], swing_lows: list[SwingPoint]) -> tuple[str, int, bool, bool, bool, bool]:
    """
    Analyze trend structure from swing points.
    
    Uptrend = Higher Highs + Higher Lows
    Downtrend = Lower Highs + Lower Lows
    Ranging = mixed or not enough data
    """
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "neutral", 0, False, False, False, False
    
    # Check last 3 swing points each
    recent_highs = swing_highs[-3:]
    recent_lows = swing_lows[-3:]
    
    # Higher highs?
    higher_highs = all(recent_highs[i].price < recent_highs[i + 1].price for i in range(len(recent_highs) - 1))
    
    # Higher lows?
    higher_lows = all(recent_lows[i].price < recent_lows[i + 1].price for i in range(len(recent_lows) - 1))
    
    # Lower highs?
    lower_highs = all(recent_highs[i].price > recent_highs[i + 1].price for i in range(len(recent_highs) - 1))
    
    # Lower lows?
    lower_lows = all(recent_lows[i].price > recent_lows[i + 1].price for i in range(len(recent_lows) - 1))
    
    # Determine trend
    if higher_highs and higher_lows:
        trend = "uptrend"
        strength = 5
    elif lower_highs and lower_lows:
        trend = "downtrend"
        strength = 5
    elif higher_highs or higher_lows:
        trend = "uptrend"
        strength = 3 if (higher_highs and higher_lows) else 2
    elif lower_highs or lower_lows:
        trend = "downtrend"
        strength = 3 if (lower_highs and lower_lows) else 2
    else:
        trend = "ranging"
        strength = 1
    
    return trend, strength, higher_highs, higher_lows, lower_highs, lower_lows


def detect_bos_choch(swing_highs: list[SwingPoint], swing_lows: list[SwingPoint], current_price: float) -> tuple[bool, str, bool, str]:
    """
    Detect Break of Structure (BOS) and Change of Character (CHoCH).
    
    BOS = price breaks recent swing in trend direction (continuation)
    CHoCH = price breaks recent swing against trend (reversal signal)
    """
    bos_detected = False
    bos_direction = ""
    choch_detected = False
    choch_direction = ""
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return bos_detected, bos_direction, choch_detected, choch_direction
    
    last_high = swing_highs[-1].price
    prev_high = swing_highs[-2].price if len(swing_highs) >= 2 else last_high
    last_low = swing_lows[-1].price
    prev_low = swing_lows[-2].price if len(swing_lows) >= 2 else last_low
    
    # Trend direction
    was_uptrend = prev_high < last_high and prev_low < last_low
    was_downtrend = prev_high > last_high and prev_low > last_low
    
    # BOS: continuation
    if was_uptrend and current_price > last_high:
        bos_detected = True
        bos_direction = "bullish"
    elif was_downtrend and current_price < last_low:
        bos_detected = True
        bos_direction = "bearish"
    
    # CHoCH: reversal
    if was_uptrend and current_price < last_low:
        choch_detected = True
        choch_direction = "bearish"
    elif was_downtrend and current_price > last_high:
        choch_detected = True
        choch_direction = "bullish"
    
    return bos_detected, bos_direction, choch_detected, choch_direction


def estimate_wyckoff_phase(
    trend: str,
    higher_highs: bool,
    higher_lows: bool,
    lower_highs: bool,
    lower_lows: bool,
    price_position: str,
    vol_ratio: float = 1.0,
) -> tuple[str, str]:
    """
    Estimate Wyckoff phase based on structure and volume.
    
    Phases:
    - Accumulation: ranging after downtrend, decreasing vol, spring possible
    - Markup: uptrend with increasing vol
    - Distribution: ranging after uptrend, decreasing vol, UTAD possible
    - Markdown: downtrend with increasing vol
    """
    phase = "unknown"
    position = ""
    
    if trend == "uptrend":
        if higher_highs and higher_lows:
            if vol_ratio > 1.5:
                phase = "markup"
                position = "sos"  # Sign of Strength
            else:
                phase = "markup"
                position = "lps"  # Last Point of Support
        else:
            phase = "accumulation"
            position = "spring" if price_position == "below_support" else "sos"
    
    elif trend == "downtrend":
        if lower_highs and lower_lows:
            if vol_ratio > 1.5:
                phase = "markdown"
                position = "sos"  # Sign of Weakness (inverse)
            else:
                phase = "markdown"
                position = "lps"  # Last Point of Supply (inverse)
        else:
            phase = "distribution"
            position = "utad" if price_position == "above_resistance" else "sos"
    
    elif trend == "ranging":
        # Need more context - default to accumulation assumption
        phase = "accumulation"
        position = "trading_range"
    
    return phase, position


def calculate_price_position(current: float, support: float, resistance: float) -> tuple[str, float, float]:
    """
    Calculate price position relative to support/resistance.
    """
    if resistance <= 0 or support <= 0:
        return "unknown", 0.0, 0.0
    
    range_size = resistance - support
    if range_size <= 0:
        return "unknown", 0.0, 0.0
    
    dist_to_res = ((resistance - current) / current) * 100 if current > 0 else 0
    dist_to_sup = ((current - support) / current) * 100 if current > 0 else 0
    
    # Position classification
    if current > resistance:
        position = "above_resistance"
    elif current < support:
        position = "below_support"
    elif current >= resistance * 0.99:  # within 1% of resistance
        position = "at_resistance"
    elif current <= support * 1.01:  # within 1% of support
        position = "at_support"
    else:
        position = "in_range"
    
    return position, dist_to_res, dist_to_sup


def generate_structure_story(s: MarketStructure) -> str:
    """Generate human-readable structure story."""
    parts = []
    
    # Trend
    if s.trend == "uptrend":
        parts.append(f"📈 Uptrend ({s.trend_strength}/5)")
        if s.higher_highs and s.higher_lows:
            parts.append("HH+HL structure intact")
    elif s.trend == "downtrend":
        parts.append(f"📉 Downtrend ({s.trend_strength}/5)")
        if s.lower_highs and s.lower_lows:
            parts.append("LH+LL structure intact")
    else:
        parts.append(f"➡️ Ranging/Neutral")
    
    # BOS/CHoCH
    if s.bos_detected:
        parts.append(f"⚡ BOS {s.bos_direction.upper()}")
    if s.choch_detected:
        parts.append(f"🔄 CHoCH {s.choch_direction.upper()} (reversal signal)")
    
    # Position
    if s.price_position == "above_resistance":
        parts.append(f"🚀 Broke resistance {s.resistance:.0f}")
    elif s.price_position == "below_support":
        parts.append(f"⚠️ Below support {s.support:.0f}")
    elif s.price_position == "at_resistance":
        parts.append(f"🔷 At resistance {s.resistance:.0f}")
    elif s.price_position == "at_support":
        parts.append(f"🔹 At support {s.support:.0f}")
    
    # Wyckoff
    if s.wyckoff_phase != "unknown":
        parts.append(f"📊 Wyckoff: {s.wyckoff_phase.upper()} ({s.wyckoff_position})")
    
    return " | ".join(parts)


def analyze_market_structure(ticker: str, days: int = 30) -> MarketStructure:
    """
    Full market structure analysis.
    
    Returns trend, S/R levels, Wyckoff phase, BOS/CHoCH detection.
    """
    result = MarketStructure(ticker=ticker)
    
    # Get price history
    try:
        history = api.get_price_history(ticker, days=days)
        if not history or len(history) < 10:
            return result
        
        highs = [h.get("high", h.get("High", 0)) for h in history]
        lows = [l.get("low", l.get("Low", 0)) for l in history]
        closes = [c.get("close", c.get("Close", 0)) for c in history]
        
        if not highs or not lows:
            return result
        
        result.current_price = closes[-1] if closes else 0
        
        # Detect swing points
        swing_highs, swing_lows = detect_swing_points(highs, lows, lookback=3)
        
        if swing_highs:
            result.last_swing_high = swing_highs[-1]
            result.resistance = swing_highs[-1].price
            result.resistance_strength = swing_highs[-1].strength
        
        if swing_lows:
            result.last_swing_low = swing_lows[-1]
            result.support = swing_lows[-1].price
            result.support_strength = swing_lows[-1].strength
        
        # Analyze trend
        (result.trend, result.trend_strength, 
         result.higher_highs, result.higher_lows,
         result.lower_highs, result.lower_lows) = analyze_trend_structure(swing_highs, swing_lows)
        
        # BOS/CHoCH
        (result.bos_detected, result.bos_direction,
         result.choch_detected, result.choch_direction) = detect_bos_choch(
            swing_highs, swing_lows, result.current_price
        )
        
        # Price position
        (result.price_position, 
         result.distance_to_resistance_pct,
         result.distance_to_support_pct) = calculate_price_position(
            result.current_price, result.support, result.resistance
        )
        
        # Wyckoff phase
        result.wyckoff_phase, result.wyckoff_position = estimate_wyckoff_phase(
            result.trend,
            result.higher_highs, result.higher_lows,
            result.lower_highs, result.lower_lows,
            result.price_position,
        )
        
        # Generate story
        result.structure_story = generate_structure_story(result)
        
    except Exception as e:
        log.warning(f"Market structure analysis failed for {ticker}: {e}")
    
    return result


def format_analysis(s: MarketStructure) -> str:
    """Format market structure for display."""
    lines = []
    lines.append(f"📊 {s.ticker} Structure")
    lines.append("")
    lines.append(s.structure_story)
    lines.append("")
    lines.append(f"Support: {s.support:.0f} ({s.support_strength}/5)")
    lines.append(f"Resistance: {s.resistance:.0f} ({s.resistance_strength}/5)")
    
    if s.distance_to_resistance_pct != 0:
        lines.append(f"→ Resistance: {s.distance_to_resistance_pct:+.1f}%")
    if s.distance_to_support_pct != 0:
        lines.append(f"→ Support: {s.distance_to_support_pct:+.1f}%")
    
    return "\n".join(lines)


# ─── Persistence ──────────────────────────────────────────────────────────────

STRUCTURE_FILE = DATA_DIR / "market_structures.json"


def save_structure(ticker: str, structure: MarketStructure):
    """Save structure analysis for historical tracking."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    data = {}
    if STRUCTURE_FILE.exists():
        try:
            data = json.loads(STRUCTURE_FILE.read_text())
        except:
            data = {}
    
    data[ticker] = {
        "timestamp": structure.current_price,
        "trend": structure.trend,
        "trend_strength": structure.trend_strength,
        "support": structure.support,
        "resistance": structure.resistance,
        "wyckoff_phase": structure.wyckoff_phase,
        "bos_detected": structure.bos_detected,
        "choch_detected": structure.choch_detected,
        "structure_story": structure.structure_story,
    }
    
    STRUCTURE_FILE.write_text(json.dumps(data, indent=2))


def get_structure(ticker: str) -> Optional[dict]:
    """Get last saved structure for ticker."""
    if not STRUCTURE_FILE.exists():
        return None
    try:
        data = json.loads(STRUCTURE_FILE.read_text())
        return data.get(ticker)
    except:
        return None
