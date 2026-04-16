"""
Broker Profile — Player Identification
========================================
Layer 2 skill: WHO is in this stock? What's their intent?

Key questions:
- Who are the players? Smart money or retail?
- What's their average price? Above or below current?
- Are they consistent buyers or hit-and-run?
- Same broker active in multiple tickers? (sector thesis)
- Is the data suggesting real accumulation or manipulation?

Mr O's principle: "Broker name != insight. Need context."
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import api

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

DATA_DIR = Path("/home/lazywork/workspace/vault/data")
PROFILES_FILE = DATA_DIR / "broker-profiles.json"


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class PlayerProfile:
    """A single player (broker) in a specific stock."""
    broker_code: str
    category: str                       # smart_money / retail / foreign / prajogo_group
    side: str                           # "buyer" or "seller"
    avg_price: float = 0.0
    current_price: float = 0.0
    price_position: str = ""            # "underwater" / "in_profit" / "at_cost"
    price_gap_pct: float = 0.0          # how far avg_price from current (%)
    inventory_vol: int = 0
    inventory_val: float = 0.0
    position_size: str = ""             # "large" / "medium" / "small"
    movement_pattern: list[str] = field(default_factory=list)
    buy_days: int = 0
    sell_days: int = 0
    consistency: float = 0.0            # 0-1, how consistent their buying/selling
    intent: str = ""                    # derived: "accumulating" / "distributing" / "scalping" / "mixed"
    horizon: str = ""                   # NEW: "long_term" / "short_term" / "swing"
    frequency: int = 0                  # NEW: total transaction frequency
    avg_lot_per_trade: float = 0.0      # NEW: average lot size per trade


@dataclass
class PlayerAnalysis:
    """Complete player analysis for a ticker."""
    ticker: str
    timestamp: str = ""
    current_price: float = 0.0
    
    # Key narratives
    smart_money_side: str = ""          # "buying" / "selling" / "mixed" / "absent"
    retail_side: str = ""               # "buying" / "selling" / "mixed"
    
    # Player details
    buyers: list[PlayerProfile] = field(default_factory=list)
    sellers: list[PlayerProfile] = field(default_factory=list)
    
    # Broker summary
    smart_money_buyers: list[str] = field(default_factory=list)   # broker codes
    smart_money_sellers: list[str] = field(default_factory=list)
    long_term_players: list[str] = field(default_factory=list)    # committed
    short_term_players: list[str] = field(default_factory=list)   # scalpers
    
    # Retail participation
    retail_participation_pct: float = 0.0    # % of total volume from retail
    retail_fomo: bool = False                # retail buying aggressively
    retail_panic: bool = False               # retail selling aggressively
    retail_avg_lot: float = 0.0              # avg retail lot size
    
    # Derived insights
    trap_detected: bool = False         # retail buying + smart money selling
    trap_type: str = ""                 # "distribution_trap" / "accumulation_trap"
    
    conviction_signal: str = ""         # "smart_money_accumulating" / "distribution_in_progress" / "unclear"
    key_insight: str = ""               # one-liner summary
    
    # Bandar P/L summary
    smart_money_avg_cost: float = 0.0
    smart_money_pl_pct: float = 0.0     # aggregate P/L %
    smart_money_underwater: bool = False


# ─── Analysis ─────────────────────────────────────────────────────────────────

def _classify_intent(entry: api.BrokerEntry) -> str:
    """Classify broker intent from movement pattern."""
    if entry.consistency >= 0.7:
        return "accumulating" if entry.buy_days > entry.sell_days else "distributing"
    if entry.consistency >= 0.4:
        return "building" if entry.buy_days > entry.sell_days else "reducing"
    if entry.buy_days <= 2 and entry.sell_days <= 2:
        return "scalping"
    return "mixed"


def _classify_horizon(buy_days: int, sell_days: int, consistency: float) -> str:
    """
    Classify broker time horizon.
    
    Long-term: Active 10+ days with high consistency
    Short-term: Active <=3 days, low consistency
    Swing: In between
    """
    total_days = buy_days + sell_days
    if total_days >= 10 and consistency >= 0.6:
        return "long_term"
    elif total_days <= 3:
        return "short_term"
    else:
        return "swing"


def _classify_position_size(inventory_val: float) -> str:
    """Classify position size by inventory value."""
    if inventory_val >= 50_000_000_000:    # 50B+
        return "whale"
    if inventory_val >= 10_000_000_000:    # 10B+
        return "large"
    if inventory_val >= 2_000_000_000:     # 2B+
        return "medium"
    return "small"


def _price_position(avg_price: float, current_price: float) -> tuple[str, float]:
    """Determine if broker is underwater, in profit, or at cost."""
    if avg_price <= 0 or current_price <= 0:
        return "unknown", 0.0
    gap_pct = ((current_price - avg_price) / avg_price) * 100
    if gap_pct < -3:
        return "underwater", gap_pct
    if gap_pct > 3:
        return "in_profit", gap_pct
    return "at_cost", gap_pct


def _build_profile(entry: api.BrokerEntry, side: str, current_price: float) -> PlayerProfile:
    """Build a PlayerProfile from a BrokerEntry."""
    pos, gap = _price_position(entry.avg_price, current_price)
    horizon = _classify_horizon(entry.buy_days, entry.sell_days, entry.consistency)
    frequency = len(entry.movement) if entry.movement else (entry.buy_days + entry.sell_days)
    avg_lot = entry.inventory_vol / max(1, frequency)
    
    return PlayerProfile(
        broker_code=entry.code,
        category=entry.category,
        side=side,
        avg_price=entry.avg_price,
        current_price=current_price,
        price_position=pos,
        price_gap_pct=round(gap, 1),
        inventory_vol=entry.inventory_vol,
        inventory_val=entry.inventory_val,
        position_size=_classify_position_size(entry.inventory_val),
        movement_pattern=entry.movement,
        buy_days=entry.buy_days,
        sell_days=entry.sell_days,
        consistency=round(entry.consistency, 2),
        intent=_classify_intent(entry),
        horizon=horizon,
        frequency=frequency,
        avg_lot_per_trade=round(avg_lot, 0),
    )


def analyze_players(ticker: str) -> PlayerAnalysis:
    """
    Full player analysis for a ticker.
    
    Returns WHO is playing, their avg price, consistency, position size, and intent.
    Also detects traps (retail buying while smart money sells).
    """
    now = datetime.now(WIB)
    current_price = api.get_price(ticker)
    dist = api.get_broker_distribution(ticker)
    
    analysis = PlayerAnalysis(
        ticker=ticker,
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        current_price=current_price,
    )
    
    # Build profiles for buyers
    for entry in dist.top_buyers:
        profile = _build_profile(entry, "buyer", current_price)
        analysis.buyers.append(profile)
    
    # Build profiles for sellers
    for entry in dist.top_sellers:
        profile = _build_profile(entry, "seller", current_price)
        analysis.sellers.append(profile)
    
    # ── Derive: who is on which side? ──
    
    smart_buyers = [b for b in analysis.buyers if b.category == "smart_money"]
    smart_sellers = [s for s in analysis.sellers if s.category == "smart_money"]
    retail_buyers = [b for b in analysis.buyers if b.category == "retail"]
    retail_sellers = [s for s in analysis.sellers if s.category == "retail"]
    
    # Smart money side
    if smart_buyers and not smart_sellers:
        analysis.smart_money_side = "buying"
    elif smart_sellers and not smart_buyers:
        analysis.smart_money_side = "selling"
    elif smart_buyers and smart_sellers:
        # Compare total inventory
        buy_val = sum(b.inventory_val for b in smart_buyers)
        sell_val = sum(s.inventory_val for s in smart_sellers)
        analysis.smart_money_side = "buying" if buy_val > sell_val * 1.3 else (
            "selling" if sell_val > buy_val * 1.3 else "mixed"
        )
    else:
        analysis.smart_money_side = "absent"
    
    # Retail side
    if retail_buyers and not retail_sellers:
        analysis.retail_side = "buying"
    elif retail_sellers and not retail_buyers:
        analysis.retail_side = "selling"
    elif retail_buyers and retail_sellers:
        analysis.retail_side = "mixed"
    else:
        analysis.retail_side = "absent"
    
    # ── Broker Summary ──
    # Smart money buyers/sellers
    analysis.smart_money_buyers = [b.broker_code for b in smart_buyers]
    analysis.smart_money_sellers = [s.broker_code for s in smart_sellers]
    
    # Long-term vs short-term classification
    for b in analysis.buyers:
        if b.horizon == "long_term":
            analysis.long_term_players.append(b.broker_code)
        elif b.horizon == "short_term":
            analysis.short_term_players.append(b.broker_code)
    
    for s in analysis.sellers:
        if s.horizon == "long_term":
            if s.broker_code not in analysis.long_term_players:
                analysis.long_term_players.append(s.broker_code)
        elif s.horizon == "short_term":
            if s.broker_code not in analysis.short_term_players:
                analysis.short_term_players.append(s.broker_code)
    
    # ── Retail Participation Analysis ──
    total_val = sum(b.inventory_val for b in analysis.buyers) + sum(s.inventory_val for s in analysis.sellers)
    retail_val = sum(b.inventory_val for b in retail_buyers) + sum(s.inventory_val for s in retail_sellers)
    
    if total_val > 0:
        analysis.retail_participation_pct = round((retail_val / total_val) * 100, 1)
    
    # Retail avg lot size
    retail_all = retail_buyers + retail_sellers
    if retail_all:
        total_retail_lots = sum(r.inventory_vol for r in retail_all)
        total_retail_freq = sum(r.frequency for r in retail_all)
        analysis.retail_avg_lot = round(total_retail_lots / max(1, total_retail_freq), 0)
    
    # FOMO detection: retail buying high frequency + small lots
    if retail_buyers:
        retail_buy_freq = sum(b.frequency for b in retail_buyers)
        smart_buy_freq = sum(b.frequency for b in smart_buyers) if smart_buyers else 0
        if retail_buy_freq > smart_buy_freq * 2 and analysis.retail_avg_lot < 10:
            analysis.retail_fomo = True
    
    # Panic detection: retail selling high frequency
    if retail_sellers:
        retail_sell_freq = sum(s.frequency for s in retail_sellers)
        smart_sell_freq = sum(s.frequency for s in smart_sellers) if smart_sellers else 0
        if retail_sell_freq > smart_sell_freq * 2:
            analysis.retail_panic = True
    
    # ── Smart Money P/L Summary ──
    if smart_buyers:
        # Weighted average cost
        total_val_sm = sum(b.inventory_val for b in smart_buyers)
        total_vol_sm = sum(b.inventory_vol for b in smart_buyers)
        if total_vol_sm > 0:
            analysis.smart_money_avg_cost = total_val_sm / total_vol_sm
            if analysis.smart_money_avg_cost > 0:
                analysis.smart_money_pl_pct = ((current_price - analysis.smart_money_avg_cost) / analysis.smart_money_avg_cost) * 100
                analysis.smart_money_underwater = analysis.smart_money_pl_pct < -5
    
    # ── Trap detection ──
    # Classic trap: retail excited buying, smart money quietly selling
    if analysis.retail_side == "buying" and analysis.smart_money_side == "selling":
        analysis.trap_detected = True
        analysis.trap_type = "distribution_trap"
    # Reverse trap: retail panicking out, smart money absorbing
    elif analysis.retail_side == "selling" and analysis.smart_money_side == "buying":
        analysis.trap_detected = True
        analysis.trap_type = "accumulation_setup"  # this is actually GOOD
    
    # ── Conviction signal ──
    if analysis.smart_money_side == "buying":
        # Check if they're underwater (vested interest to push up)
        underwater_sm = [b for b in smart_buyers if b.price_position == "underwater"]
        if underwater_sm:
            analysis.conviction_signal = "smart_money_underwater_accumulating"
        else:
            analysis.conviction_signal = "smart_money_accumulating"
    elif analysis.smart_money_side == "selling":
        analysis.conviction_signal = "distribution_in_progress"
    else:
        analysis.conviction_signal = "unclear"
    
    # ── Key insight ──
    analysis.key_insight = _generate_key_insight(analysis)
    
    return analysis


def _generate_key_insight(a: PlayerAnalysis) -> str:
    """Generate the one-liner insight that matters."""
    parts = []
    
    if a.trap_detected:
        if a.trap_type == "distribution_trap":
            smart_sellers = [s.broker_code for s in a.sellers if s.category == "smart_money"]
            retail_buyers = [b.broker_code for b in a.buyers if b.category == "retail"]
            parts.append(
                f"⚠️ TRAP: Retail ({','.join(retail_buyers[:3])}) buying, "
                f"but smart money ({','.join(smart_sellers[:3])}) distributing."
            )
        elif a.trap_type == "accumulation_setup":
            smart_buyers = [b.broker_code for b in a.buyers if b.category == "smart_money"]
            parts.append(
                f"✅ Smart money ({','.join(smart_buyers[:3])}) absorbing retail panic. "
                f"Accumulation setup."
            )
    
    # Underwater smart money = vested interest
    underwater = [b for b in a.buyers if b.category == "smart_money" and b.price_position == "underwater"]
    if underwater:
        codes = [b.broker_code for b in underwater]
        avg_prices = [f"{b.avg_price:.0f}" for b in underwater]
        parts.append(
            f"💡 {','.join(codes)} bought avg {','.join(avg_prices)} (above current {a.current_price:.0f}). "
            f"Vested interest to push up."
        )
    
    # Smart money in profit = may distribute
    in_profit = [s for s in a.sellers if s.category == "smart_money" and s.price_position == "in_profit"]
    if in_profit:
        codes = [s.broker_code for s in in_profit]
        parts.append(f"⚠️ {','.join(codes)} in profit, distributing.")
    
    if not parts:
        if a.smart_money_side == "absent":
            parts.append("No smart money activity detected.")
        else:
            parts.append(f"Smart money {a.smart_money_side}. Retail {a.retail_side}.")
    
    return " ".join(parts)


# ─── Cross-ticker analysis ───────────────────────────────────────────────────

def detect_cross_ticker(tickers: list[str]) -> dict[str, list[str]]:
    """
    Find brokers active in multiple tickers → sector play signal.
    
    Returns: {broker_code: [ticker1, ticker2, ...]}
    """
    broker_tickers: dict[str, list[str]] = {}
    
    for ticker in tickers:
        dist = api.get_broker_distribution(ticker)
        for entry in dist.top_buyers:
            if entry.category == "smart_money":
                broker_tickers.setdefault(entry.code, []).append(ticker)
    
    # Only return brokers active in 2+ tickers
    return {b: ts for b, ts in broker_tickers.items() if len(ts) >= 2}


# ─── Persistence ──────────────────────────────────────────────────────────────

def save_snapshot(ticker: str, analysis: PlayerAnalysis):
    """Save player analysis snapshot for historical tracking."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing
    profiles = {}
    if PROFILES_FILE.exists():
        try:
            profiles = json.loads(PROFILES_FILE.read_text())
        except:
            profiles = {}
    
    # Append to ticker history
    if ticker not in profiles:
        profiles[ticker] = []
    
    snapshot = {
        "timestamp": analysis.timestamp,
        "price": analysis.current_price,
        "smart_money_side": analysis.smart_money_side,
        "retail_side": analysis.retail_side,
        "conviction_signal": analysis.conviction_signal,
        "trap_detected": analysis.trap_detected,
        "trap_type": analysis.trap_type,
        "key_insight": analysis.key_insight,
        "top_buyers": [
            {"code": b.broker_code, "cat": b.category, "avg": b.avg_price, 
             "intent": b.intent, "consistency": b.consistency}
            for b in analysis.buyers[:5]
        ],
        "top_sellers": [
            {"code": s.broker_code, "cat": s.category, "avg": s.avg_price,
             "intent": s.intent, "consistency": s.consistency}
            for s in analysis.sellers[:5]
        ],
    }
    
    profiles[ticker].append(snapshot)
    
    # Keep last 30 snapshots per ticker
    profiles[ticker] = profiles[ticker][-30:]
    
    PROFILES_FILE.write_text(json.dumps(profiles, indent=2))
    log.info(f"Saved broker profile snapshot for {ticker}")


def get_profile_history(ticker: str) -> list[dict]:
    """Get historical broker profiles for a ticker."""
    if not PROFILES_FILE.exists():
        return []
    try:
        profiles = json.loads(PROFILES_FILE.read_text())
        return profiles.get(ticker, [])
    except:
        return []


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_analysis(a: PlayerAnalysis) -> str:
    """Format player analysis for display (Telegram-friendly)."""
    lines = []
    lines.append(f"👥 {a.ticker} Players — {a.timestamp}")
    lines.append("")
    
    # Key insight first
    lines.append(a.key_insight)
    lines.append("")
    
    # Buyers
    if a.buyers:
        lines.append("🟢 Top Buyers:")
        for b in a.buyers[:5]:
            cat = {"smart_money": "🏦", "retail": "👤", "foreign": "🌍", "prajogo_group": "🏢"}.get(b.category, "❓")
            underwater = " ⬆️" if b.price_position == "underwater" else ""
            lines.append(
                f"  {cat} {b.broker_code} — avg {b.avg_price:.0f} ({b.price_gap_pct:+.1f}%){underwater} "
                f"| {b.intent} | size:{b.position_size}"
            )
    
    # Sellers
    if a.sellers:
        lines.append("🔴 Top Sellers:")
        for s in a.sellers[:5]:
            cat = {"smart_money": "🏦", "retail": "👤", "foreign": "🌍", "prajogo_group": "🏢"}.get(s.category, "❓")
            lines.append(
                f"  {cat} {s.broker_code} — avg {s.avg_price:.0f} ({s.price_gap_pct:+.1f}%) "
                f"| {s.intent} | size:{s.position_size}"
            )
    
    lines.append("")
    lines.append(f"Signal: {a.conviction_signal}")
    
    return "\n".join(lines)
