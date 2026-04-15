"""
Narrative — Story Generator
=============================
Combines broker_profile + psychology + sid_tracker + macro + wyckoff into a STORY.

NOT a score. A narrative that explains:
- WHO is playing (and their intent)
- WHAT they're doing at key levels
- WHY the stock should move (or not)
- WHAT layer it's at (L1/L2/L3)

Mr O's principle: "Thought process itu PENTING!"
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import api
from broker_profile import PlayerAnalysis
from psychology import PsychologyAnalysis
from sid_tracker import SIDAnalysis
from macro import MarketRegime, get_sector

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")


@dataclass
class StockNarrative:
    """Complete narrative for a stock."""
    ticker: str
    timestamp: str = ""
    sector: str = ""
    current_price: float = 0.0
    
    # Layer determination
    layer: int = 1                  # 1=thesis only, 2=analyzed, 3=trade-ready
    layer_reason: str = ""
    
    # Story components
    player_story: str = ""          # from broker_profile
    psychology_story: str = ""      # from psychology
    sid_story: str = ""             # from sid_tracker
    macro_context: str = ""         # from macro regime
    wyckoff_story: str = ""         # from wyckoff phase + SMI
    structure_story: str = ""       # from market_structure (NEW)
    monitor_story: str = ""         # from 30-min insights (NEW)
    
    # Combined narrative
    story: str = ""                 # the full narrative paragraph
    
    # Verdict
    verdict: str = ""               # BUY / WATCH / AVOID
    verdict_reason: str = ""
    conviction: str = ""            # HIGH / MEDIUM / LOW
    
    # Red flags
    red_flags: list[str] = field(default_factory=list)
    green_flags: list[str] = field(default_factory=list)


def generate(
    ticker: str,
    players: Optional[PlayerAnalysis] = None,
    psychology: Optional[PsychologyAnalysis] = None,
    sid: Optional[SIDAnalysis] = None,
    regime: Optional[MarketRegime] = None,
    wyckoff = None,  # WyckoffAnalysis
    structure = None,  # MarketStructure (NEW)
    monitor: Optional[dict] = None,  # 30-min insights (NEW)
) -> StockNarrative:
    """
    Generate a complete narrative for a stock.
    
    Pass pre-computed analysis results, or None to skip that component.
    The narrative adapts based on what data is available.
    """
    now = datetime.now(WIB)
    price = players.current_price if players else api.get_price(ticker)
    
    narrative = StockNarrative(
        ticker=ticker,
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        sector=get_sector(ticker),
        current_price=price,
    )
    
    story_parts = []
    
    # ── Player story ──
    if players:
        narrative.player_story = players.key_insight
        story_parts.append(players.key_insight)
        
        # Flags from players
        if players.trap_detected:
            if players.trap_type == "distribution_trap":
                narrative.red_flags.append("Distribution trap: retail buying, smart money selling")
            elif players.trap_type == "accumulation_setup":
                narrative.green_flags.append("Smart money absorbing retail panic")
        
        if players.conviction_signal == "smart_money_underwater_accumulating":
            narrative.green_flags.append("Smart money underwater — vested interest to push up")
        elif players.conviction_signal == "distribution_in_progress":
            narrative.red_flags.append("Distribution in progress")
    
    # ── Psychology story ──
    if psychology:
        narrative.psychology_story = psychology.summary
        story_parts.append(psychology.summary)
        
        # Flags from psychology
        if psychology.at_resistance and psychology.at_resistance.near_level:
            if psychology.at_resistance.signal == "bullish":
                narrative.green_flags.append(f"Bullish at resistance {psychology.resistance:.0f}")
            elif psychology.at_resistance.signal == "bearish":
                narrative.red_flags.append(f"Bearish at resistance {psychology.resistance:.0f}")
        
        if psychology.at_support and psychology.at_support.near_level:
            if psychology.at_support.signal == "bearish":
                narrative.red_flags.append(f"Support {psychology.support:.0f} not defended")
            elif psychology.at_support.signal == "bullish":
                narrative.green_flags.append(f"Support {psychology.support:.0f} defended")
    
    # ── SID story ──
    if sid:
        narrative.sid_story = sid.narrative
        story_parts.append(sid.narrative)
        
        if sid.signal == "bullish":
            narrative.green_flags.append(f"SID accumulation ({sid.sid_change_pct:+.1f}%)")
        elif sid.signal == "bearish":
            narrative.red_flags.append(f"SID distribution ({sid.sid_change_pct:+.1f}%)")
        
        if sid.broker_confirms is False:
            narrative.red_flags.append("SID and broker flow CONTRADICT each other")
    
    # ── Wyckoff story ──
    if wyckoff:
        narrative.wyckoff_story = f"Wyckoff: {wyckoff.phase} | SMI {wyckoff.smi_trend}"
        story_parts.append(narrative.wyckoff_story)
        
        # Flags from Wyckoff
        if wyckoff.phase == "ACCUMULATION" and wyckoff.smi_trend == "RISING":
            narrative.green_flags.append("Wyckoff: Accumulation + SMI rising")
        elif wyckoff.phase == "MARKUP" and wyckoff.structure == "HH-HL":
            narrative.green_flags.append("Wyckoff: Markup phase confirmed")
        elif wyckoff.phase == "DISTRIBUTION":
            narrative.red_flags.append("Wyckoff: Distribution detected — avoid entry")
        elif wyckoff.phase == "MARKDOWN":
            narrative.red_flags.append("Wyckoff: Markdown — wait for accumulation")
        
        # Spring detection
        if "Spring detected" in " ".join(wyckoff.signals):
            narrative.green_flags.append("Spring pattern (false break) — entry signal")
        
        # UTAD detection
        if "UTAD detected" in " ".join(wyckoff.signals):
            narrative.red_flags.append("UTAD pattern — distribution confirmed")
    
    # ── Macro context ──
    if regime:
        narrative.macro_context = f"Market: {regime.label} ({regime.confidence})"
        story_parts.append(narrative.macro_context)
        
        if regime.label in ("BEAR", "SIDEWAYS_BEARISH"):
            narrative.red_flags.append(f"Bearish market regime ({regime.label})")
    
    # ── Market Structure (NEW) ──
    if structure:
        narrative.structure_story = structure.structure_story
        story_parts.append(structure.structure_story)
        
        # Flags from structure
        if structure.bos_detected:
            if structure.bos_direction == "bullish":
                narrative.green_flags.append(f"BOS bullish — trend continuation")
            else:
                narrative.red_flags.append(f"BOS bearish — breakdown")
        
        if structure.choch_detected:
            if structure.choch_direction == "bullish":
                narrative.green_flags.append(f"CHoCH bullish — trend reversal up")
            else:
                narrative.red_flags.append(f"CHoCH bearish — trend reversal down")
        
        if structure.trend == "uptrend" and structure.trend_strength >= 4:
            narrative.green_flags.append(f"Strong uptrend ({structure.trend_strength}/5)")
        elif structure.trend == "downtrend" and structure.trend_strength >= 4:
            narrative.red_flags.append(f"Strong downtrend ({structure.trend_strength}/5)")
        
        if structure.price_position == "below_support":
            narrative.red_flags.append(f"Below support {structure.support:.0f}")
        elif structure.price_position == "at_support":
            narrative.green_flags.append(f"At support {structure.support:.0f}")
    
    # ── Monitor Insights (30-min data) (NEW) ──
    if monitor:
        pressure = monitor.get("pressure", "NEUTRAL")
        crossings = monitor.get("crossings", 0)
        breakout_prob = monitor.get("breakout_prob", 0)
        breakdown_prob = monitor.get("breakdown_prob", 0)
        fake_walls = monitor.get("fake_walls", 0)
        tektok = monitor.get("tektok_traps", 0)
        
        monitor_parts = []
        if pressure != "NEUTRAL":
            monitor_parts.append(f"Pressure: {pressure}")
        if crossings > 0:
            monitor_parts.append(f"Crossings: {crossings}")
        
        narrative.monitor_story = " | ".join(monitor_parts) if monitor_parts else ""
        if narrative.monitor_story:
            story_parts.append(narrative.monitor_story)
        
        # Flags from monitor
        if "STRONG_BUY" in pressure:
            narrative.green_flags.append("Strong buying pressure (30m)")
        elif "STRONG_SELL" in pressure:
            narrative.red_flags.append("Strong selling pressure (30m)")
        
        if breakout_prob >= 70:
            narrative.green_flags.append(f"Breakout probability {breakout_prob}%")
        if breakdown_prob >= 70:
            narrative.red_flags.append(f"Breakdown probability {breakdown_prob}%")
        
        if fake_walls >= 2:
            narrative.red_flags.append(f"{fake_walls} fake walls detected")
        if tektok >= 1:
            narrative.red_flags.append(f"Tektok trap detected — manipulation")
    
    # ── Combine into story ──
    narrative.story = " | ".join(story_parts) if story_parts else "No analysis data available."
    
    # ── Determine layer ──
    has_players = players is not None
    has_psychology = psychology is not None
    has_sid = sid is not None
    
    if has_players and has_psychology:
        narrative.layer = 3 if not narrative.red_flags else 2
        narrative.layer_reason = "Full analysis complete"
    elif has_players:
        narrative.layer = 2
        narrative.layer_reason = "Player analysis done, need psychology + SID"
    else:
        narrative.layer = 1
        narrative.layer_reason = "Thesis only, need full analysis"
    
    # ── Verdict ──
    green_count = len(narrative.green_flags)
    red_count = len(narrative.red_flags)
    
    if red_count >= 3:
        narrative.verdict = "AVOID"
        narrative.conviction = "HIGH"
        narrative.verdict_reason = f"{red_count} red flags. Too many risks."
    elif red_count >= 2 and green_count <= 1:
        narrative.verdict = "AVOID"
        narrative.conviction = "MEDIUM"
        narrative.verdict_reason = "More risk signals than opportunity."
    elif green_count >= 3 and red_count == 0:
        narrative.verdict = "BUY"
        narrative.conviction = "HIGH"
        narrative.verdict_reason = "Multiple green flags, no red flags."
    elif green_count >= 2 and red_count <= 1:
        narrative.verdict = "BUY"
        narrative.conviction = "MEDIUM" if red_count == 0 else "LOW"
        narrative.verdict_reason = "Opportunity outweighs risk."
    elif green_count >= 1 and red_count <= 1:
        narrative.verdict = "WATCH"
        narrative.conviction = "LOW"
        narrative.verdict_reason = "Mixed signals. Need more data or better entry."
    else:
        narrative.verdict = "WATCH"
        narrative.conviction = "LOW"
        narrative.verdict_reason = "Insufficient signals for conviction."
    
    # Override: distribution trap = always AVOID regardless of green flags
    if players and players.trap_detected and players.trap_type == "distribution_trap":
        if narrative.verdict == "BUY":
            narrative.verdict = "WATCH"
            narrative.verdict_reason = "Distribution trap detected. Don't chase."
    
    return narrative


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_narrative(n: StockNarrative) -> str:
    """Format narrative for display (Telegram-friendly)."""
    verdict_icon = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(n.verdict, "⚪")
    
    lines = []
    lines.append(f"━━━ {n.ticker} ━━━")
    lines.append(f"Layer {n.layer} | {n.sector} | {n.current_price:.0f}")
    lines.append("")
    
    # Story
    if n.player_story:
        lines.append(f"👥 {n.player_story}")
    if n.psychology_story:
        lines.append(f"🧠 {n.psychology_story}")
    if n.sid_story:
        lines.append(f"📊 {n.sid_story}")
    if n.macro_context:
        lines.append(f"🌍 {n.macro_context}")
    
    lines.append("")
    
    # Flags
    if n.green_flags:
        for f in n.green_flags:
            lines.append(f"  🟢 {f}")
    if n.red_flags:
        for f in n.red_flags:
            lines.append(f"  🔴 {f}")
    
    lines.append("")
    lines.append(f"{verdict_icon} {n.verdict} ({n.conviction}) — {n.verdict_reason}")
    
    return "\n".join(lines)


def format_compact(n: StockNarrative) -> str:
    """Compact one-liner format for lists."""
    verdict_icon = {"BUY": "🟢", "WATCH": "🟡", "AVOID": "🔴"}.get(n.verdict, "⚪")
    return f"{verdict_icon} {n.ticker} L{n.layer} ({n.conviction}) — {n.player_story[:80]}"
