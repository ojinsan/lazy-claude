"""
Psychology — Behavior at Key Price Levels
==========================================
Layer 2 skill: What's happening at resistance/support?

Mr O's examples:
1. Bandar sells at resist into retail bids → "ga pede" → expect fade
2. Retail sells at resist, bandar absorbs → "sini jual gw tampung" → bullish
3. +13% meleyot ke 4% = bandar jualan di resist, kentara banget

Key question: WHO is doing WHAT at this price level?
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import api

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class LevelBehavior:
    """Behavior analysis at a specific price level."""
    level_type: str = ""            # "resistance" / "support"
    level_price: float = 0.0
    current_price: float = 0.0
    distance_pct: float = 0.0       # how far price is from level (%)
    near_level: bool = False        # within 3% of level
    
    # WHO is doing WHAT at this level
    smart_money_action: str = ""    # "buying" / "selling" / "absent" / "mixed"
    retail_action: str = ""         # "buying" / "selling" / "absent" / "mixed"
    
    # Orderbook pressure
    bid_pressure: float = 0.0       # positive = more bids
    ask_pressure: float = 0.0       # positive = more asks
    pressure_side: str = ""         # "buyers" / "sellers" / "balanced"
    
    # Pattern classification
    pattern: str = ""               # see PATTERNS below
    psychology: str = ""            # human-readable interpretation
    signal: str = ""                # "bullish" / "bearish" / "neutral"
    confidence: str = ""            # "high" / "medium" / "low"


# Pattern classifications
PATTERNS = {
    "bandar_absorbs_at_resistance": {
        "description": "Smart money absorbs retail sells at resistance",
        "psychology": "Bandar tampung jualan retail. 'Sini lo jual, gw tampung. Lo pergi sana ga usah ikut naik.'",
        "signal": "bullish",
        "confidence": "high",
    },
    "bandar_distributes_at_resistance": {
        "description": "Smart money sells into retail bids at resistance",
        "psychology": "Bandar ga pede breakout. Jualan tiap ada yang bid. Expect fade.",
        "signal": "bearish",
        "confidence": "high",
    },
    "bandar_drives_through_resistance": {
        "description": "Smart money aggressively buys through resistance with volume",
        "psychology": "Bandar pede, push through. Strong conviction breakout.",
        "signal": "bullish",
        "confidence": "high",
    },
    "bandar_defends_support": {
        "description": "Smart money buys at support, absorbs selling pressure",
        "psychology": "Bandar jaga level support. Harga ga boleh turun lebih jauh.",
        "signal": "bullish",
        "confidence": "medium",
    },
    "bandar_abandons_support": {
        "description": "Smart money not buying at support, lets it break",
        "psychology": "Bandar ga mau defend. Support bisa jebol.",
        "signal": "bearish",
        "confidence": "medium",
    },
    "retail_panic_at_support": {
        "description": "Retail selling hard at support, possible capitulation",
        "psychology": "Retail panik jual. Watch for sweep — smart money might scoop.",
        "signal": "neutral",
        "confidence": "medium",
    },
    "no_activity_at_level": {
        "description": "Neither side active near key level",
        "psychology": "Sepi. Volume tipis di level kunci. Belum ada keputusan.",
        "signal": "neutral",
        "confidence": "low",
    },
    "mixed_battle": {
        "description": "Both sides fighting at level",
        "psychology": "Perang di level kunci. Belum ada pemenang.",
        "signal": "neutral",
        "confidence": "low",
    },
}


@dataclass
class PsychologyAnalysis:
    """Complete psychology analysis for a ticker."""
    ticker: str
    timestamp: str = ""
    current_price: float = 0.0
    
    # Nearest levels
    support: float = 0.0
    resistance: float = 0.0
    
    # Behavior at each level
    at_resistance: Optional[LevelBehavior] = None
    at_support: Optional[LevelBehavior] = None
    
    # Overall read
    dominant_pattern: str = ""      # which pattern is most relevant right now
    summary: str = ""               # one-liner
    

# ─── Analysis ─────────────────────────────────────────────────────────────────

def _classify_pressure(orderbook_delta: dict) -> tuple[float, float, str]:
    """Classify bid/ask pressure from orderbook delta."""
    bid = float(orderbook_delta.get("total_bid_value", orderbook_delta.get("bid_value", 0)))
    ask = float(orderbook_delta.get("total_ask_value", orderbook_delta.get("ask_value", 0)))
    
    if bid <= 0 and ask <= 0:
        return 0, 0, "no_data"
    
    total = bid + ask if (bid + ask) > 0 else 1
    bid_pct = bid / total
    ask_pct = ask / total
    
    if bid_pct > 0.6:
        side = "buyers"
    elif ask_pct > 0.6:
        side = "sellers"
    else:
        side = "balanced"
    
    return bid_pct, ask_pct, side


def _classify_level_pattern(
    level_type: str,
    smart_money_action: str,
    retail_action: str,
    pressure_side: str,
    volume_ratio: float,
) -> str:
    """Classify the behavior pattern at a price level."""
    
    if level_type == "resistance":
        # At resistance: key question = is bandar willing to break through?
        if smart_money_action == "buying" and retail_action == "selling":
            if volume_ratio >= 1.5:
                return "bandar_absorbs_at_resistance"
            return "bandar_absorbs_at_resistance"
        
        if smart_money_action == "selling" and retail_action == "buying":
            return "bandar_distributes_at_resistance"
        
        if smart_money_action == "buying" and volume_ratio >= 2.0:
            return "bandar_drives_through_resistance"
        
        if smart_money_action == "selling":
            return "bandar_distributes_at_resistance"
        
        if smart_money_action == "absent":
            return "no_activity_at_level"
    
    elif level_type == "support":
        # At support: key question = is bandar defending?
        if smart_money_action == "buying":
            return "bandar_defends_support"
        
        if smart_money_action == "selling" or smart_money_action == "absent":
            if retail_action == "selling" and volume_ratio >= 1.5:
                return "retail_panic_at_support"
            return "bandar_abandons_support"
    
    if smart_money_action == "mixed" or (smart_money_action == "buying" and retail_action == "buying"):
        return "mixed_battle"
    
    return "no_activity_at_level"


def _analyze_at_level(
    ticker: str,
    level_type: str,
    level_price: float,
    current_price: float,
    broker_dist: api.BrokerDistribution,
    orderbook_delta: dict,
    volume_ratio: float,
) -> LevelBehavior:
    """Analyze behavior at a specific price level."""
    
    behavior = LevelBehavior(
        level_type=level_type,
        level_price=level_price,
        current_price=current_price,
    )
    
    # Distance from level
    if level_price > 0:
        behavior.distance_pct = ((current_price - level_price) / level_price) * 100
        behavior.near_level = abs(behavior.distance_pct) <= 3.0
    
    # Orderbook pressure
    behavior.bid_pressure, behavior.ask_pressure, behavior.pressure_side = (
        _classify_pressure(orderbook_delta)
    )
    
    # WHO is doing WHAT — from broker distribution
    smart_buyers = [b for b in broker_dist.top_buyers if b.category == "smart_money"]
    smart_sellers = [s for s in broker_dist.top_sellers if s.category == "smart_money"]
    retail_buyers = [b for b in broker_dist.top_buyers if b.category == "retail"]
    retail_sellers = [s for s in broker_dist.top_sellers if s.category == "retail"]
    
    # Smart money action
    if smart_buyers and not smart_sellers:
        behavior.smart_money_action = "buying"
    elif smart_sellers and not smart_buyers:
        behavior.smart_money_action = "selling"
    elif smart_buyers and smart_sellers:
        buy_val = sum(b.inventory_val for b in smart_buyers)
        sell_val = sum(s.inventory_val for s in smart_sellers)
        behavior.smart_money_action = "buying" if buy_val > sell_val * 1.3 else (
            "selling" if sell_val > buy_val * 1.3 else "mixed"
        )
    else:
        behavior.smart_money_action = "absent"
    
    # Retail action
    if retail_buyers and not retail_sellers:
        behavior.retail_action = "buying"
    elif retail_sellers and not retail_buyers:
        behavior.retail_action = "selling"
    elif retail_buyers and retail_sellers:
        behavior.retail_action = "mixed"
    else:
        behavior.retail_action = "absent"
    
    # Classify pattern
    pattern_key = _classify_level_pattern(
        level_type, behavior.smart_money_action, behavior.retail_action,
        behavior.pressure_side, volume_ratio,
    )
    
    pattern_info = PATTERNS.get(pattern_key, PATTERNS["no_activity_at_level"])
    behavior.pattern = pattern_key
    behavior.psychology = pattern_info["psychology"]
    behavior.signal = pattern_info["signal"]
    behavior.confidence = pattern_info["confidence"]
    
    return behavior


def analyze_psychology(ticker: str) -> PsychologyAnalysis:
    """
    Full psychology analysis: what's happening at support/resistance?
    
    Combines broker flow + orderbook + S/R levels to determine
    bandar behavior and confidence at key price levels.
    """
    now = datetime.now(WIB)
    
    # Fetch data
    current_price = api.get_price(ticker)
    sr = api.get_support_resistance(ticker)
    broker_dist = api.get_broker_distribution(ticker)
    ob_delta = api.get_orderbook_delta(ticker)
    vol_ratio = api.get_volume_ratio(ticker)
    
    analysis = PsychologyAnalysis(
        ticker=ticker,
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        current_price=current_price,
        support=sr.support,
        resistance=sr.resistance,
    )
    
    # Analyze at resistance
    if sr.resistance > 0:
        analysis.at_resistance = _analyze_at_level(
            ticker, "resistance", sr.resistance, current_price,
            broker_dist, ob_delta, vol_ratio,
        )
    
    # Analyze at support
    if sr.support > 0:
        analysis.at_support = _analyze_at_level(
            ticker, "support", sr.support, current_price,
            broker_dist, ob_delta, vol_ratio,
        )
    
    # Determine dominant pattern (which level matters more right now)
    if analysis.at_resistance and analysis.at_resistance.near_level:
        analysis.dominant_pattern = analysis.at_resistance.pattern
        analysis.summary = (
            f"Near resistance {sr.resistance:.0f}: {analysis.at_resistance.psychology}"
        )
    elif analysis.at_support and analysis.at_support.near_level:
        analysis.dominant_pattern = analysis.at_support.pattern
        analysis.summary = (
            f"Near support {sr.support:.0f}: {analysis.at_support.psychology}"
        )
    else:
        # Between levels — note the range
        analysis.dominant_pattern = "between_levels"
        analysis.summary = (
            f"Between S:{sr.support:.0f} and R:{sr.resistance:.0f}. "
            f"No immediate level pressure."
        )
    
    return analysis


# ─── Psychology Shift Detection (for fastpace) ───────────────────────────────

def detect_shift(
    current: PsychologyAnalysis,
    previous: Optional[PsychologyAnalysis],
) -> Optional[str]:
    """
    Detect if psychology has shifted since last check.
    
    Returns alert message if shift detected, None otherwise.
    Used by fastpace.py for intraday alerts.
    """
    if previous is None:
        return None
    
    # Check resistance behavior shift
    if (current.at_resistance and previous.at_resistance and
        current.at_resistance.near_level):
        
        curr_pat = current.at_resistance.pattern
        prev_pat = previous.at_resistance.pattern
        
        if curr_pat != prev_pat:
            curr_info = PATTERNS.get(curr_pat, {})
            prev_info = PATTERNS.get(prev_pat, {})
            
            # Significant shifts
            if (prev_pat == "bandar_absorbs_at_resistance" and 
                curr_pat == "bandar_distributes_at_resistance"):
                return (
                    f"⚠️ {current.ticker} SHIFT at R:{current.resistance:.0f}: "
                    f"Bandar STOPPED absorbing, now distributing. Expect fade."
                )
            
            if (prev_pat == "bandar_distributes_at_resistance" and
                curr_pat == "bandar_absorbs_at_resistance"):
                return (
                    f"✅ {current.ticker} SHIFT at R:{current.resistance:.0f}: "
                    f"Bandar NOW absorbing retail sells. Breakout setup forming."
                )
            
            if curr_pat == "bandar_drives_through_resistance":
                return (
                    f"🔥 {current.ticker} BREAKOUT: "
                    f"Smart money driving through R:{current.resistance:.0f} with volume!"
                )
    
    # Check support behavior shift
    if (current.at_support and previous.at_support and
        current.at_support.near_level):
        
        curr_pat = current.at_support.pattern
        prev_pat = previous.at_support.pattern
        
        if curr_pat != prev_pat:
            if (prev_pat == "bandar_defends_support" and 
                curr_pat == "bandar_abandons_support"):
                return (
                    f"🔴 {current.ticker} DANGER at S:{current.support:.0f}: "
                    f"Bandar stopped defending support. May break down."
                )
            
            if curr_pat == "retail_panic_at_support":
                return (
                    f"👀 {current.ticker} CAPITULATION at S:{current.support:.0f}: "
                    f"Retail panic selling. Watch for sweep entry."
                )
    
    return None


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_analysis(a: PsychologyAnalysis) -> str:
    """Format psychology analysis for display."""
    lines = []
    lines.append(f"🧠 {a.ticker} Psychology — {a.timestamp}")
    lines.append(f"Price: {a.current_price:.0f} | S: {a.support:.0f} | R: {a.resistance:.0f}")
    lines.append("")
    
    if a.at_resistance:
        r = a.at_resistance
        near = "📍 NEAR" if r.near_level else f"  {r.distance_pct:+.1f}%"
        signal_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(r.signal, "⚪")
        lines.append(f"Resistance {r.level_price:.0f} ({near}):")
        lines.append(f"  Smart money: {r.smart_money_action} | Retail: {r.retail_action}")
        lines.append(f"  Orderbook: {r.pressure_side}")
        lines.append(f"  {signal_icon} {r.psychology}")
        lines.append(f"  Confidence: {r.confidence}")
        lines.append("")
    
    if a.at_support:
        s = a.at_support
        near = "📍 NEAR" if s.near_level else f"  {s.distance_pct:+.1f}%"
        signal_icon = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.signal, "⚪")
        lines.append(f"Support {s.level_price:.0f} ({near}):")
        lines.append(f"  Smart money: {s.smart_money_action} | Retail: {s.retail_action}")
        lines.append(f"  Orderbook: {s.pressure_side}")
        lines.append(f"  {signal_icon} {s.psychology}")
        lines.append(f"  Confidence: {s.confidence}")
        lines.append("")
    
    lines.append(f"📌 {a.summary}")
    
    return "\n".join(lines)
