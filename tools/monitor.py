"""
Lazyboy Monitor v3.2 — Hybrid (WebSocket + Polling)
====================================================
- WebSocket: Orderbook bid/offer (real-time via Redis)
- Polling 60s: Running trade (last 1 min transactions)
- Evaluation 10 min: Trade history + orderbook analysis
- Backend API only for: token refresh + RAG + watchlist
- HIGH priority = immediate Telegram push
- MED/LOW = batch queue for heartbeat

Architecture:
  orderbook_ws.py (background) → Redis → monitor.py
  monitor.py → Poll running trade → Store history → Evaluate 10 min
"""

import time
import httpx
import logging
import json as _json
import os
import shutil
import math
import asyncio

from stockbit_headers import stockbit_headers
from tick_walls import analyze_tick_walls, compare_tick_walls, compare_wall_series

from datetime import datetime
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Backend API (only for token)
BACKEND_URL = "http://43.173.164.222:8080"
BACKEND_TOKEN = "6697ed8a65e1bf92bdbe4cd1aa2d64dcbeb91a0d9c39a35d0a245b830524fe92"
BACKEND_HEADERS = {"Authorization": f"Bearer {BACKEND_TOKEN}"}

# Stockbit API (direct)
STOCKBIT_BASE_URL = "https://exodus.stockbit.com"

WIB = ZoneInfo("Asia/Jakarta")

# Alert queues
ALERT_QUEUE = "/tmp/lazyboy_alert_queue.jsonl"
BATCH_QUEUE = "/tmp/lazyboy_batch_queue.jsonl"
SENT_FILE = "/tmp/lazyboy_alert_sent.txt"
FALLBACK_SENT_FILE = "/tmp/lazyboy_fallback_sent.txt"

# OpenClaw targets
OPENCLAW_TARGET_CHATS = ["7649943712", "1139649438"]
OPENCLAW_BIN = shutil.which("openclaw") or "/home/lazywork/.npm-global/bin/openclaw"

# Runtime behavior
ALERT_COOLDOWN = 240
PULSE_INTERVAL_CYCLES = 4
FALLBACK_STALE_SECONDS = 600
BATCH_INTERVAL = 1800  # 30 min

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
ORDERBOOK_KEY_PREFIX = "lazyboy:orderbook:"
RUNNING_TRADE_KEY_PREFIX = "lazyboy:running_trade:"
RUNNING_TRADE_TTL = 600  # 10 minutes

# Redis client (lazy init)
_redis_client = None

def get_redis():
    """Get Redis client (lazy initialization)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    
    try:
        import redis
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        log.warning(f"Redis not available: {e}")
        return None


# ─── Insight Generation ───────────────────────────────────────────────────────

def generate_session_summary(ticker: str, insights_list: list) -> dict:
    """
    Generate comprehensive session summary for a ticker.
    
    Analyzes all 30-min snapshots to detect:
    - Intraday pattern (accumulation/distribution/sideways)
    - Smart money behavior
    - Failed moves
    - Time-of-day patterns
    - Next-day signals
    
    Returns: Session summary dict
    """
    if not insights_list:
        return {"pattern": "NO_DATA"}
    
    # Aggregate data
    total_samples = len(insights_list)
    
    # Price action
    first_price = insights_list[0].get("price", 0)
    last_price = insights_list[-1].get("price", 0)
    session_change = ((last_price - first_price) / first_price * 100) if first_price else 0
    
    # High/low
    prices = [i.get("price", 0) for i in insights_list if i.get("price")]
    session_high = max(prices) if prices else 0
    session_low = min(prices) if prices else 0
    
    # Volume
    vol_ratios = [i.get("vol_ratio", 0) for i in insights_list]
    avg_vol_ratio = sum(vol_ratios) / len(vol_ratios) if vol_ratios else 0
    
    # Big player activity
    big_player_pcts = [i.get("big_player_pct", 0) for i in insights_list]
    avg_big_player = sum(big_player_pcts) / len(big_player_pcts) if big_player_pcts else 0
    
    # Pressure distribution
    pressures = [i.get("pressure") for i in insights_list if i.get("pressure")]
    buy_pressure_count = sum(1 for p in pressures if p and "BUY" in p)
    sell_pressure_count = sum(1 for p in pressures if p and "SELL" in p)
    
    # Morning vs Afternoon (split at 12:00)
    morning_insights = [i for i in insights_list if i.get("cycle", 0) < 18]  # Before 12:00
    afternoon_insights = [i for i in insights_list if i.get("cycle", 0) >= 18]  # After 12:00
    
    morning_buy = sum(1 for i in morning_insights if i.get("pressure") and "BUY" in i.get("pressure", ""))
    afternoon_buy = sum(1 for i in afternoon_insights if i.get("pressure") and "BUY" in i.get("pressure", ""))
    
    # Detections
    tektok_count = sum(i.get("tektok_trap_count", 0) for i in insights_list)
    sweep_count = sum(i.get("liquidity_sweep_count", 0) for i in insights_list)
    fake_wall_count = sum(i.get("fake_wall_count", 0) for i in insights_list)
    panic_count = sum(i.get("panic_detected", 0) for i in insights_list)
    fomo_count = sum(i.get("fomo_detected", 0) for i in insights_list)
    manipulation_count = sum(i.get("manipulation_count", 0) for i in insights_list)
    
    # Breakout attempts
    max_breakout_prob = max(i.get("breakout_prob", 0) for i in insights_list)
    max_breakdown_prob = max(i.get("breakdown_prob", 0) for i in insights_list)
    
    # ─── PATTERN CLASSIFICATION ─────────────────────────────────────────
    
    pattern = "SIDEWAYS"
    pattern_confidence = "LOW"
    
    # Accumulation pattern
    if session_change >= 0 and sell_pressure_count > buy_pressure_count and avg_big_player >= 40:
        pattern = "ACCUMULATION"
        pattern_confidence = "HIGH" if avg_big_player >= 50 else "MEDIUM"
    
    # Distribution pattern
    elif session_change <= 0 and buy_pressure_count > sell_pressure_count and avg_big_player >= 40:
        pattern = "DISTRIBUTION"
        pattern_confidence = "HIGH" if avg_big_player >= 50 else "MEDIUM"
    
    # Strong trend
    elif abs(session_change) >= 3:
        if session_change > 0:
            pattern = "UPTREND"
        else:
            pattern = "DOWNTREND"
        pattern_confidence = "HIGH" if avg_vol_ratio >= 1.5 else "MEDIUM"
    
    # Manipulation detected
    if manipulation_count >= 2:
        pattern = "MANIPULATION"
        pattern_confidence = "HIGH"
    
    # ─── SMART MONEY BEHAVIOR ───────────────────────────────────────────
    
    smart_money_behavior = None
    
    if avg_big_player >= 40:
        # Check if buying into weakness
        if sell_pressure_count > buy_pressure_count and session_change >= 0:
            smart_money_behavior = "BUYING_INTO_WEAKNESS"
        # Check if selling into strength
        elif buy_pressure_count > sell_pressure_count and session_change <= 0:
            smart_money_behavior = "SELLING_INTO_STRENGTH"
        # Passive accumulation
        elif session_change >= 0 and avg_big_player >= 50:
            smart_money_behavior = "PASSIVE_ACCUMULATION"
        # Aggressive distribution
        elif session_change <= 0 and avg_big_player >= 50:
            smart_money_behavior = "AGGRESSIVE_DISTRIBUTION"
    
    # ─── FAILED MOVES ───────────────────────────────────────────────────
    
    failed_moves = []
    
    # Failed breakout (high breakout prob but price ended down)
    if max_breakout_prob >= 60 and session_change < 0:
        failed_moves.append("FAILED_BREAKOUT")
    
    # Failed breakdown (high breakdown prob but price ended up)
    if max_breakdown_prob >= 60 and session_change > 0:
        failed_moves.append("FAILED_BREAKDOWN")
    
    # Fake sweep (sweep detected but price reversed)
    if sweep_count > 0 and tektok_count > 0:
        failed_moves.append("FAKE_SWEEP")
    
    # ─── TIME-OF-DAY PATTERN ─────────────────────────────────────────────
    
    time_pattern = None
    
    if morning_insights and afternoon_insights:
        morning_change = 0
        afternoon_change = 0
        
        if len(morning_insights) >= 2:
            m_first = morning_insights[0].get("price", 0)
            m_last = morning_insights[-1].get("price", 0)
            morning_change = ((m_last - m_first) / m_first * 100) if m_first else 0
        
        if len(afternoon_insights) >= 2:
            a_first = afternoon_insights[0].get("price", 0)
            a_last = afternoon_insights[-1].get("price", 0)
            afternoon_change = ((a_last - a_first) / a_first * 100) if a_first else 0
        
        # Morning rally, afternoon fade
        if morning_change >= 1.5 and afternoon_change <= -0.5:
            time_pattern = "MORNING_RALLY_FADE"
        # Morning weak, afternoon strong
        elif morning_change <= -0.5 and afternoon_change >= 1.5:
            time_pattern = "AFTERNOON_RALLY"
        # All day strength
        elif morning_change >= 1 and afternoon_change >= 1:
            time_pattern = "ALL_DAY_STRENGTH"
        # All day weakness
        elif morning_change <= -1 and afternoon_change <= -1:
            time_pattern = "ALL_DAY_WEAKNESS"
    
    # ─── NEXT-DAY SIGNALS ────────────────────────────────────────────────
    
    next_day_signals = []
    
    # Near resistance + failed breakout = watch for breakdown
    if max_breakout_prob >= 60 and "FAILED_BREAKOUT" in failed_moves:
        next_day_signals.append("WATCH_BREAKDOWN")
    
    # Near support + failed breakdown = watch for bounce
    if max_breakdown_prob >= 60 and "FAILED_BREAKDOWN" in failed_moves:
        next_day_signals.append("WATCH_BOUNCE")
    
    # Accumulation detected = watch for breakout
    if pattern == "ACCUMULATION":
        next_day_signals.append("WATCH_BREAKOUT")
    
    # Distribution detected = avoid or short
    if pattern == "DISTRIBUTION":
        next_day_signals.append("AVVOID_OR_SHORT")
    
    # Smart money buying = follow
    if smart_money_behavior in ("BUYING_INTO_WEAKNESS", "PASSIVE_ACCUMULATION"):
        next_day_signals.append("FOLLOW_SMART_MONEY_LONG")
    
    # Smart money selling = avoid
    if smart_money_behavior in ("SELLING_INTO_STRENGTH", "AGGRESSIVE_DISTRIBUTION"):
        next_day_signals.append("AVOID_LONG")
    
    # Manipulation detected = extra cautious
    if pattern == "MANIPULATION":
        next_day_signals.append("EXTRA_CAUTIOUS")
    
    # ─── COMPILE SUMMARY ─────────────────────────────────────────────────
    
    return {
        "pattern": pattern,
        "pattern_confidence": pattern_confidence,
        "session_change_pct": round(session_change, 2),
        "session_high": session_high,
        "session_low": session_low,
        "avg_vol_ratio": round(avg_vol_ratio, 2),
        "avg_big_player_pct": round(avg_big_player, 1),
        "buy_pressure_count": buy_pressure_count,
        "sell_pressure_count": sell_pressure_count,
        "smart_money_behavior": smart_money_behavior,
        "time_pattern": time_pattern,
        "failed_moves": failed_moves,
        "detections": {
            "tektok_trap": tektok_count,
            "liquidity_sweep": sweep_count,
            "fake_wall": fake_wall_count,
            "panic": panic_count,
            "fomo": fomo_count,
            "manipulation": manipulation_count,
        },
        "max_breakout_prob": max_breakout_prob,
        "max_breakdown_prob": max_breakdown_prob,
        "next_day_signals": next_day_signals,
        "sample_count": total_samples,
    }


def generate_session_insight(ticker: str, summary: dict) -> str:
    """
    Generate human-readable insight from session summary.
    
    Returns: 2-3 sentence insight for screener.
    """
    parts = []
    
    # Pattern
    pattern = summary.get("pattern", "")
    confidence = summary.get("pattern_confidence", "")
    
    if pattern != "SIDEWAYS":
        parts.append(f"Pattern: {pattern} ({confidence})")
    
    # Smart money
    sm = summary.get("smart_money_behavior")
    if sm:
        parts.append(f"Smart money: {sm.replace('_', ' ').lower()}")
    
    # Time pattern
    tp = summary.get("time_pattern")
    if tp:
        parts.append(f"Timing: {tp.replace('_', ' ').lower()}")
    
    # Failed moves
    failed = summary.get("failed_moves", [])
    if failed:
        parts.append(f"Failed: {', '.join(failed)}")
    
    # Next-day signals
    signals = summary.get("next_day_signals", [])
    if signals:
        parts.append(f"Next day: {', '.join(signals[:3])}")
    
    # Detections
    det = summary.get("detections", {})
    interesting = []
    if det.get("tektok_trap", 0) > 0:
        interesting.append("tektok trap")
    if det.get("liquidity_sweep", 0) > 0:
        interesting.append("liquidity sweep")
    if det.get("manipulation", 0) > 0:
        interesting.append("manipulation")
    
    if interesting:
        parts.append(f"Detected: {', '.join(interesting)}")
    
    if not parts:
        return "Normal session, no significant signals."
    
    return " | ".join(parts)


def write_daily_recap(insights_data: dict):
    """
    Write end-of-day recap for screener.
    
    Called at market close (15:30 WIB).
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    WIB = ZoneInfo("Asia/Jakarta")
    now = datetime.now(WIB)
    date_str = now.strftime("%Y-%m-%d")
    
    recap_file = f"/home/lazywork/lazyboy/trade/data/daily_recap_{date_str}.json"
    
    # Build recap
    recap = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "tickers": {},
        "highlights": [],
        "summary": {
            "total_tickers": len(insights_data),
            "accumulation_count": 0,
            "distribution_count": 0,
            "manipulation_count": 0,
            "failed_breakouts": 0,
            "failed_breakdowns": 0,
        },
    }
    
    for ticker, data in insights_data.items():
        # Generate session summary
        summary = generate_session_summary(ticker, data.get("insights", []))
        
        # Generate insight text
        insight = generate_session_insight(ticker, summary)
        
        recap["tickers"][ticker] = {
            **data,
            "session_summary": summary,
            "insight": insight,
        }
        
        # Update global summary
        if summary.get("pattern") == "ACCUMULATION":
            recap["summary"]["accumulation_count"] += 1
        elif summary.get("pattern") == "DISTRIBUTION":
            recap["summary"]["distribution_count"] += 1
        elif summary.get("pattern") == "MANIPULATION":
            recap["summary"]["manipulation_count"] += 1
        
        if "FAILED_BREAKOUT" in summary.get("failed_moves", []):
            recap["summary"]["failed_breakouts"] += 1
        if "FAILED_BREAKDOWN" in summary.get("failed_moves", []):
            recap["summary"]["failed_breakdowns"] += 1
        
        # Check for highlights
        if any([
            abs(summary.get("session_change_pct", 0)) >= 3,
            summary.get("pattern") in ("ACCUMULATION", "DISTRIBUTION", "MANIPULATION"),
            len(summary.get("failed_moves", [])) > 0,
            summary.get("smart_money_behavior") is not None,
            len(summary.get("next_day_signals", [])) > 0,
        ]):
            recap["highlights"].append({
                "ticker": ticker,
                "pattern": summary.get("pattern"),
                "insight": insight,
                "next_day_signals": summary.get("next_day_signals", []),
            })
    
    # Write recap
    try:
        with open(recap_file, "w") as f:
            _json.dump(recap, f, indent=2)
        log.info(f"✅ Daily recap written to {recap_file}")
        log.info(f"   Total: {recap['summary']['total_tickers']} tickers")
        log.info(f"   Accumulation: {recap['summary']['accumulation_count']}")
        log.info(f"   Distribution: {recap['summary']['distribution_count']}")
        log.info(f"   Manipulation: {recap['summary']['manipulation_count']}")
        log.info(f"   Highlights: {len(recap['highlights'])} tickers with signals")
    except Exception as e:
        log.error(f"Failed to write daily recap: {e}")


# ─── Insight Generation ───────────────────────────────────────────────────────

def generate_ticker_insight(ticker: str, data: dict) -> str:
    """
    Generate human-readable insight for a ticker based on 30-min data.
    
    Returns: Insight string (1-2 sentences)
    """
    insights = []
    
    # Price action
    change = data.get("avg_change_pct", 0)
    if abs(change) >= 3:
        direction = "naik" if change > 0 else "turun"
        insights.append(f"Significant move {direction} {abs(change):.1f}%")
    
    # Pressure
    pressure = data.get("dominant_pressure")
    big_player_pct = data.get("avg_big_player_pct", 0)
    
    if pressure in ("STRONG_BUY", "STRONG_SELL"):
        if big_player_pct >= 50:
            actor = "bandar"
        else:
            actor = "retail"
        
        if "BUY" in pressure:
            insights.append(f"{actor} strong buying ({big_player_pct:.0f}% big player)")
        else:
            insights.append(f"{actor} panic selling")
    
    # Orderbook
    ob = data.get("dominant_orderbook")
    if ob in ("THICK_BID_NEAR", "DISTRIBUTION_WARNING"):
        insights.append(f"orderbook: {ob.replace('_', ' ').lower()}")
    
    # Crossings
    crossings = data.get("total_crossings", 0)
    if crossings >= 10:
        insights.append(f"{crossings} large trades (crossing)")
    
    # Detections
    tektok = data.get("tektok_trap_count", 0)
    sweep = data.get("liquidity_sweep_count", 0)
    fake_wall = data.get("fake_wall_count", 0)
    
    if tektok > 0:
        insights.append("⚠️ jebakan tektok detected")
    if sweep > 0:
        sweep_type = data.get("dominant_sweep_type", "")
        if "bullish" in sweep_type:
            insights.append(" liquidity sweep (bullish)")
        elif "bearish" in sweep_type:
            insights.append(" liquidity sweep (bearish)")
    if fake_wall > 0:
        insights.append("fake wall detected")
    
    # Breakout/breakdown probability
    breakout = data.get("max_breakout_prob", 0)
    breakdown = data.get("max_breakdown_prob", 0)
    
    if breakout >= 60:
        insights.append(f"breakout probability: {breakout}%")
    if breakdown >= 60:
        insights.append(f"breakdown probability: {breakdown}%")
    
    # S/R activity
    sr = data.get("dominant_sr_activity")
    if sr:
        insights.append(sr.replace("_", " ").lower())
    
    if not insights:
        return "Normal trading, no significant signals."
    
    return " | ".join(insights)


def write_daily_recap(insights_data: dict):
    """
    Write end-of-day recap for screener.
    
    Called at market close (15:30 WIB).
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    WIB = ZoneInfo("Asia/Jakarta")
    now = datetime.now(WIB)
    date_str = now.strftime("%Y-%m-%d")
    
    recap_file = f"/home/lazywork/lazyboy/trade/data/daily_recap_{date_str}.json"
    
    # Build recap
    recap = {
        "date": date_str,
        "generated_at": now.isoformat(),
        "tickers": {},
        "highlights": [],
    }
    
    for ticker, data in insights_data.items():
        insight = generate_ticker_insight(ticker, data)
        
        recap["tickers"][ticker] = {
            **data,
            "insight": insight,
        }
        
        # Check for highlights (interesting events)
        if any([
            abs(data.get("avg_change_pct", 0)) >= 3,
            data.get("tektok_trap_count", 0) > 0,
            data.get("liquidity_sweep_count", 0) > 0,
            data.get("panic_count", 0) >= 2,
            data.get("fomo_count", 0) >= 2,
            data.get("max_breakout_prob", 0) >= 70,
            data.get("max_breakdown_prob", 0) >= 70,
        ]):
            recap["highlights"].append({
                "ticker": ticker,
                "insight": insight,
            })
    
    # Write recap
    try:
        with open(recap_file, "w") as f:
            _json.dump(recap, f, indent=2)
        log.info(f"✅ Daily recap written to {recap_file}")
        log.info(f"   Highlights: {len(recap['highlights'])} tickers with interesting events")
    except Exception as e:
        log.error(f"Failed to write daily recap: {e}")


# ─── History storage for 10-minute window ─────────────────────────────────────
_orderbook_history: dict = {}  # {ticker: [orderbook_snapshots...]}
_price_history: dict = {}  # {ticker: [(ts, price), ...]}
_trade_history: dict = {}  # {ticker: [trade_snapshots...]}

# ─── Fake Wall Detection ─────────────────────────────────────────────────────

def detect_fake_wall(ticker: str, ob_data: dict, prev_ob: dict = None) -> dict:
    """
    Detect fake walls that disappear when price approaches.
    
    Fake wall = large bid/offer that vanishes as price gets close.
    """
    if not ob_data or not prev_ob:
        return {"detected": False}
    
    current_price = 0
    bids = ob_data.get("bids", [])
    offers = ob_data.get("offers", [])
    
    if bids and offers:
        best_bid = bids[0].get("price", 0)
        best_offer = offers[0].get("price", 0)
        current_price = (best_bid + best_offer) / 2
    
    prev_bids = prev_ob.get("bids", [])
    prev_offers = prev_ob.get("offers", [])
    
    # Check for bid wall that disappeared
    fake_bid_wall = False
    for prev_bid in prev_bids[:5]:
        prev_lot = prev_bid.get("lot", 0)
        prev_price = prev_bid.get("price", 0)
        
        # Large wall (>= 100 lots)
        if prev_lot >= 100:
            # Check if it disappeared in current ob
            still_exists = False
            for curr_bid in bids[:5]:
                if curr_bid.get("price") == prev_price and curr_bid.get("lot", 0) >= 50:
                    still_exists = True
                    break
            
            # Wall disappeared + price approaching = FAKE
            if not still_exists and current_price > 0:
                distance_pct = abs(current_price - prev_price) / current_price * 100
                if distance_pct <= 2.0:  # Within 2% = price approaching
                    fake_bid_wall = True
                    break
    
    # Check for offer wall that disappeared
    fake_offer_wall = False
    for prev_offer in prev_offers[:5]:
        prev_lot = prev_offer.get("lot", 0)
        prev_price = prev_offer.get("price", 0)
        
        if prev_lot >= 100:
            still_exists = False
            for curr_offer in offers[:5]:
                if curr_offer.get("price") == prev_price and curr_offer.get("lot", 0) >= 50:
                    still_exists = True
                    break
            
            if not still_exists and current_price > 0:
                distance_pct = abs(current_price - prev_price) / current_price * 100
                if distance_pct <= 2.0:
                    fake_offer_wall = True
                    break
    
    return {
        "detected": fake_bid_wall or fake_offer_wall,
        "fake_bid_wall": fake_bid_wall,
        "fake_offer_wall": fake_offer_wall,
    }


# ─── Bot Pattern Detection ───────────────────────────────────────────────────

def detect_bot_pattern(trades: list) -> dict:
    """
    Detect bot trading patterns from running trade data.
    
    Bot pattern = same lot size + same broker (if available) + repetitive timing.
    """
    if not trades or len(trades) < 5:
        return {"detected": False}
    
    # Group by lot size
    lot_groups = {}
    for trade in trades:
        lot = trade.get("lot", 0)
        if lot not in lot_groups:
            lot_groups[lot] = []
        lot_groups[lot].append(trade)
    
    # Find repetitive patterns
    for lot, group in lot_groups.items():
        if len(group) >= 5:  # Same lot size 5+ times
            # Check timing pattern
            timestamps = [t.get("_ts", 0) for t in group if t.get("_ts")]
            if len(timestamps) >= 5:
                # Calculate intervals
                intervals = []
                for i in range(1, len(timestamps)):
                    intervals.append(timestamps[i] - timestamps[i-1])
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    # Consistent timing (within 50% variance) = bot
                    variance = max(abs(i - avg_interval) for i in intervals) if intervals else 0
                    if avg_interval > 0 and variance / avg_interval < 0.5:
                        return {
                            "detected": True,
                            "lot_size": lot,
                            "count": len(group),
                            "avg_interval": round(avg_interval, 1),
                            "pattern": "repetitive_lot_timing",
                        }
    
    return {"detected": False}


# ─── Jebakan Tektok Detection ────────────────────────────────────────────────

def detect_jebakan_tektok(ticker: str, minutes: int = 30) -> dict:
    """
    Detect "jebakan tektok" pattern:
    - Slow grind up with small volume (retail FOMO)
    - Then sudden large sell + price drop (distribution)
    
    Jebakan = trap, tektok = slow tick up
    """
    trades = get_running_trade_history(ticker, minutes)
    if not trades or len(trades) < 10:
        return {"detected": False}
    
    # Split into first half (grind phase) and second half (dump phase)
    mid = len(trades) // 2
    first_half = trades[:mid]
    second_half = trades[mid:]
    
    # First half: slow grind?
    first_buy_lots = sum(t.get("lot", 0) for t in first_half if t.get("type") == "buy")
    first_sell_lots = sum(t.get("lot", 0) for t in first_half if t.get("type") == "sell")
    first_avg_lot = sum(t.get("lot", 0) for t in first_half) / len(first_half) if first_half else 0
    
    # Second half: sudden dump?
    second_buy_lots = sum(t.get("lot", 0) for t in second_half if t.get("type") == "buy")
    second_sell_lots = sum(t.get("lot", 0) for t in second_half if t.get("type") == "sell")
    second_avg_lot = sum(t.get("lot", 0) for t in second_half) / len(second_half) if second_half else 0
    
    # Pattern detection
    grind_up = first_buy_lots > first_sell_lots * 1.3 and first_avg_lot < 50  # Retail buying, small lots
    sudden_dump = second_sell_lots > second_buy_lots * 2.0 and second_avg_lot > first_avg_lot * 2  # Large sells
    
    if grind_up and sudden_dump:
        return {
            "detected": True,
            "grind_buy_lots": first_buy_lots,
            "grind_avg_lot": round(first_avg_lot, 1),
            "dump_sell_lots": second_sell_lots,
            "dump_avg_lot": round(second_avg_lot, 1),
            "dump_ratio": round(second_sell_lots / second_buy_lots, 1) if second_buy_lots > 0 else 0,
        }
    
    return {"detected": False}


# ─── Liquidity Sweep Detection ───────────────────────────────────────────────

def detect_liquidity_sweep(ticker: str, support: float, resistance: float) -> dict:
    """
    Detect liquidity sweep pattern:
    - Price briefly breaks S/R
    - Then reverses sharply
    - Volume spike on the break
    
    This indicates fake breakdown/breakout to trigger stops.
    """
    trades = get_running_trade_history(ticker, minutes=10)
    if not trades or len(trades) < 5:
        return {"detected": False}
    
    if not support and not resistance:
        return {"detected": False}
    
    prices = [t.get("price", 0) for t in trades if t.get("price")]
    if not prices:
        return {"detected": False}
    
    min_price = min(prices)
    max_price = max(prices)
    latest_price = prices[-1]
    
    # Bullish sweep: dip below support, close above
    if support > 0:
        broke_support = min_price < support * 0.99  # Broke 1% below
        recovered = latest_price > support  # Back above
        
        if broke_support and recovered:
            # Check volume spike on the break
            break_trades = [t for t in trades if t.get("price", 0) < support]
            break_volume = sum(t.get("lot", 0) for t in break_trades)
            total_volume = sum(t.get("lot", 0) for t in trades)
            
            if break_volume > total_volume * 0.3:  # 30%+ volume at break
                return {
                    "detected": True,
                    "type": "bullish_sweep",
                    "support": support,
                    "low": min_price,
                    "recovery": latest_price,
                    "break_volume_pct": round(break_volume / total_volume * 100, 1),
                }
    
    # Bearish sweep: spike above resistance, close below
    if resistance > 0:
        broke_resistance = max_price > resistance * 1.01  # Broke 1% above
        rejected = latest_price < resistance  # Back below
        
        if broke_resistance and rejected:
            break_trades = [t for t in trades if t.get("price", 0) > resistance]
            break_volume = sum(t.get("lot", 0) for t in break_trades)
            total_volume = sum(t.get("lot", 0) for t in trades)
            
            if break_volume > total_volume * 0.3:
                return {
                    "detected": True,
                    "type": "bearish_sweep",
                    "resistance": resistance,
                    "high": max_price,
                    "rejection": latest_price,
                    "break_volume_pct": round(break_volume / total_volume * 100, 1),
                }
    
    return {"detected": False}

def store_running_trade(ticker: str, trades: list):
    """Store running trades to history (10 min window)."""
    now = time.time()
    cutoff = now - 600  # 10 minutes ago
    
    # Initialize if needed
    if ticker not in _trade_history:
        _trade_history[ticker] = []
    
    # Add new trades
    for trade in trades:
        trade["_ts"] = now
        _trade_history[ticker].append(trade)
    
    # Remove old trades
    _trade_history[ticker] = [t for t in _trade_history[ticker] if t.get("_ts", 0) >= cutoff]
    
    # Also store to Redis if available
    r = get_redis()
    if r:
        try:
            key = f"{RUNNING_TRADE_KEY_PREFIX}{ticker}"
            # Append to Redis list
            for trade in trades:
                r.rpush(key, _json.dumps(trade))
            # Trim to keep only last 10 minutes
            r.expire(key, RUNNING_TRADE_TTL)
        except Exception as e:
            log.debug(f"Redis store failed: {e}")


def get_running_trade_history(ticker: str, minutes: int = 10) -> list:
    """Get running trades from last N minutes."""
    now = time.time()
    cutoff = now - (minutes * 60)
    
    # Try memory first
    if ticker in _trade_history:
        trades = [t for t in _trade_history[ticker] if t.get("_ts", 0) >= cutoff]
        # Convert values to proper types
        for t in trades:
            if "lot" in t:
                t["lot"] = int(str(t["lot"]).replace(",", "")) if t["lot"] else 0
            if "freq" in t:
                t["freq"] = int(str(t["freq"]).replace(",", "")) if t["freq"] else 1
            if "price" in t:
                t["price"] = float(str(t["price"]).replace(",", "")) if t["price"] else 0.0
        return trades
    
    # Try Redis
    r = get_redis()
    if r:
        try:
            key = f"{RUNNING_TRADE_KEY_PREFIX}{ticker}"
            data = r.lrange(key, 0, -1)
            trades = []
            for item in data:
                try:
                    trade = _json.loads(item)
                    trade["_ts"] = trade.get("_ts", cutoff)  # Fallback
                    # Convert values to proper types
                    if "lot" in trade:
                        trade["lot"] = int(str(trade["lot"]).replace(",", "")) if trade["lot"] else 0
                    if "freq" in trade:
                        trade["freq"] = int(str(trade["freq"]).replace(",", "")) if trade["freq"] else 1
                    if "price" in trade:
                        trade["price"] = float(str(trade["price"]).replace(",", "")) if trade["price"] else 0.0
                    trades.append(trade)
                except:
                    pass
            return [t for t in trades if t.get("_ts", 0) >= cutoff]
        except Exception as e:
            log.debug(f"Redis read failed: {e}")
    
    return []


def get_orderbook_from_redis(ticker: str) -> dict:
    """Get latest orderbook from Redis (populated by WebSocket)."""
    r = get_redis()
    if not r:
        return {}
    
    try:
        key = f"{ORDERBOOK_KEY_PREFIX}{ticker}"
        data = r.get(key)
        if data:
            return _json.loads(data)
    except Exception as e:
        log.debug(f"Redis orderbook read failed: {e}")
    
    return {}

# Thresholds
PANIC_DROP_PCT = -8.0
REVERSAL_RECOVERY_PCT = 4.0
REVERSAL_MIN_VOL = 1.5
CROSSING_VOL_THRESHOLD = 3.0
LARGE_LOT_THRESHOLD = 100  # lots

# Priority levels
PRIORITY_HIGH = "HIGH"
PRIORITY_MED = "MED"
PRIORITY_LOW = "LOW"

# Data types for batch queue
DATA_PRICE_VOL = "price_vol"
DATA_ORDERBOOK = "orderbook"
DATA_CROSSING = "crossing"

# Stockbit token cache
STOCKBIT_TOKEN = None
STOCKBIT_TOKEN_EXPIRES = 0
STOCKBIT_TOKEN_FILE = "/tmp/stockbit_token.json"

# ─── Trade Plans ──────────────────────────────────────────────────────────────

TRADE_PLANS = {
    "ESSA": {
        "levels": [
            {"price": 810, "direction": "above", "key": "tp2_810", "priority": PRIORITY_HIGH,
             "message": "💰 ACTION: SELL ALL ESSA\nPrice hit TP2 zone (810)\nTake profit NOW. Plan complete."},
            {"price": 790, "direction": "above", "key": "tp1_790", "priority": PRIORITY_HIGH,
             "message": "💰 ACTION: SELL 40% ESSA\nPrice hit TP1 zone (790)\nPartial take profit. Move stop to breakeven."},
            {"price": 755, "direction": "below", "key": "reduce_755", "priority": PRIORITY_HIGH,
             "message": "⚠️ ACTION: REDUCE 50% ESSA\nPrice broke below 755\nDefensive reduce. Protect capital."},
            {"price": 745, "direction": "below", "key": "cut_745", "priority": PRIORITY_HIGH,
             "message": "🚨 ACTION: SELL ALL ESSA\nPrice hit hard stop 745\nCUT ALL. Thesis invalidated at this level."},
            {"price": 720, "direction": "below", "key": "emergency_720", "priority": PRIORITY_HIGH,
             "message": "🔴 EMERGENCY: ESSA below 720\nIf still holding — EXIT IMMEDIATELY.\nThis is well past stop loss."},
        ],
    },
    "ITMG": {
        "levels": [
            {"price": 28500, "direction": "above", "key": "tp_28500", "priority": PRIORITY_HIGH,
             "message": "💰 ACTION: CONSIDER TP ITMG\nPrice at 28,500 resistance zone.\nPartial profit if holding."},
            {"price": 25500, "direction": "below", "key": "entry_pullback", "priority": PRIORITY_MED,
             "message": "📥 ITMG pullback to entry zone 25,500\nCheck volume before entering."},
            {"price": 24000, "direction": "below", "key": "stoploss_24000", "priority": PRIORITY_HIGH,
             "message": "🚨 ACTION: CUT ITMG\nPrice broke stop loss 24,000.\nExit if holding."},
        ],
    },
    "PTRO": {
        "levels": [
            {"price": 5500, "direction": "above", "key": "extended_5500", "priority": PRIORITY_MED,
             "message": "⚡ PTRO extended above 5,500 — DO NOT CHASE.\nWait for pullback if no position."},
        ],
    },
}

# ─── Watchlist config ─────────────────────────────────────────────────────────

WATCHLIST = {
    "ESSA": {
        "entry_breakout": 792,
        "entry_pullback": 762,
        "stop_loss": 720,
        "target": 830,
        "min_vol_ratio": 1.3,
    },
    "ITMG": {
        "entry_breakout": None,
        "entry_pullback": 25500,
        "stop_loss": 24000,
        "target": 27500,
        "min_vol_ratio": 1.2,
    },
    "BUMI":  {"alert_move_pct": 2.5, "min_vol_ratio": 1.5},
    "PTRO":  {"alert_move_pct": 2.5, "min_vol_ratio": 1.3},
    "BULL":  {"alert_move_pct": 2.5, "min_vol_ratio": 1.3},
    "VKTR":  {"alert_move_pct": 2.5, "entry_breakout": 892, "stop_loss": 860, "target": 960, "min_vol_ratio": 1.5},
    "ENRG":  {"alert_move_pct": 3.0, "min_vol_ratio": 1.5},
    "BIPI":  {"alert_move_pct": 3.0, "min_vol_ratio": 1.5},
}

# Runtime state
STATE = {t: {
    "price": 0.0,
    "volume": 0,
    "avg_volume": 0,
    "open_price": 0.0,
    "prev_price": 0.0,
    "support": 0.0,
    "resistance": 0.0,
    "alerted": set(),
    "vol_history": [],
    "intraday_low_pct": 999.0,
    "intraday_high_pct": -999.0,
    "trade_plan_triggered": set(),
    "last_orderbook_check": 0,
    "orderbook_signal": None,
} for t in WATCHLIST}

LAST_ALERT = {}

# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_batch_id(ts=None):
    if ts is None:
        ts = time.time()
    return math.floor(ts / BATCH_INTERVAL) * BATCH_INTERVAL


def vol_label(ratio):
    if ratio >= 2.0:
        return f"🔥 VOL {ratio:.1f}x (STRONG)"
    if ratio >= 1.3:
        return f"📈 VOL {ratio:.1f}x (GOOD)"
    if ratio >= 0.8:
        return f"➡️  VOL {ratio:.1f}x (NORMAL)"
    return f"💤 VOL {ratio:.1f}x (THIN)"


def vol_ok(ratio, min_ratio):
    return ratio >= min_ratio


def _load_lines(path):
    if not os.path.exists(path):
        return set()
    try:
        with open(path) as f:
            return {ln.strip() for ln in f if ln.strip()}
    except:
        return set()


def _append_line(path, line):
    try:
        with open(path, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        log.error(f"Append failed ({path}): {e}")


# ─── Stockbit Token Management ────────────────────────────────────────────────

def get_stockbit_token():
    """Get Stockbit token from backend or local cache."""
    global STOCKBIT_TOKEN, STOCKBIT_TOKEN_EXPIRES
    
    now = int(time.time() * 1000)
    skew = 5 * 60 * 1000  # 5 min
    
    # Check if token still valid
    if STOCKBIT_TOKEN and STOCKBIT_TOKEN_EXPIRES > now + skew:
        return STOCKBIT_TOKEN
    
    # Try local cache first
    if os.path.exists(STOCKBIT_TOKEN_FILE):
        try:
            with open(STOCKBIT_TOKEN_FILE) as f:
                data = _json.load(f)
            token = data.get("token")
            expires = data.get("expires_at", 0)
            if token and expires > now + skew:
                STOCKBIT_TOKEN = token
                STOCKBIT_TOKEN_EXPIRES = expires
                log.info("Stockbit token loaded from cache")
                return token
        except:
            pass
    
    # Fetch from backend
    try:
        r = httpx.get(f"{BACKEND_URL}/token-store/stockbit",
                      headers=BACKEND_HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            token = data.get("token")
            expires = data.get("expires_at", 0)
            if token:
                STOCKBIT_TOKEN = token
                STOCKBIT_TOKEN_EXPIRES = expires
                # Cache locally
                try:
                    with open(STOCKBIT_TOKEN_FILE, "w") as f:
                        _json.dump(data, f)
                except:
                    pass
                log.info("Stockbit token refreshed from backend")
                return token
    except Exception as e:
        log.warning(f"Failed to fetch Stockbit token: {e}")
    
    return None


# ─── Stockbit API Calls ───────────────────────────────────────────────────────

def get_price_stockbit(ticker):
    """Get current price from Stockbit orderbook (best bid/offer mid)."""
    token = get_stockbit_token()
    if not token:
        return 0.0
    
    try:
        r = httpx.get(
            f"{STOCKBIT_BASE_URL}/company-price-feed/v2/orderbook/companies/{ticker}",
            headers=stockbit_headers(token),
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            bids = data.get("bid", [])
            offers = data.get("offer", [])
            if bids and offers:
                best_bid = float(bids[0].get("price", 0) or 0)
                best_offer = float(offers[0].get("price", 0) or 0)
                if best_bid and best_offer:
                    return (best_bid + best_offer) / 2
    except Exception as e:
        log.warning(f"Stockbit orderbook fetch failed for {ticker}: {e}")
    
    return 0.0


def get_orderbook_stockbit(ticker):
    """Get full orderbook from Stockbit."""
    token = get_stockbit_token()
    if not token:
        return None
    
    try:
        r = httpx.get(
            f"{STOCKBIT_BASE_URL}/company-price-feed/v2/orderbook/companies/{ticker}",
            headers=stockbit_headers(token),
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception as e:
        log.warning(f"Stockbit orderbook fetch failed for {ticker}: {e}")
    
    return None


def get_running_trade_stockbit(ticker, limit=50):
    """Get running trades from Stockbit (no broker codes during market hours)."""
    token = get_stockbit_token()
    if not token:
        return []
    
    try:
        r = httpx.get(
            f"{STOCKBIT_BASE_URL}/order-trade/running-trade",
            params={
                "symbols[]": ticker,
                "order_by": "RUNNING_TRADE_ORDER_BY_TIME",
                "limit": limit,
                "sort": "DESC",
            },
            headers=stockbit_headers(token),
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            return data.get("running_trade", [])
    except Exception as e:
        log.warning(f"Stockbit running trade fetch failed for {ticker}: {e}")
    
    return []


# Fallback: Use backend API for volume (no choice, Stockbit doesn't expose vol easily)
def get_volume_backend(ticker):
    """Get volume from backend API (fallback)."""
    try:
        r = httpx.get(f"{BACKEND_URL}/data/signal/volume?ticker={ticker}",
                      headers=BACKEND_HEADERS, timeout=8)
        return int(r.json().get("kwargs-after", {}).get("volume", 0))
    except:
        return 0


def get_avg_volume_backend(ticker):
    """Get avg volume from backend API (fallback)."""
    try:
        r = httpx.get(f"{BACKEND_URL}/data/signal/average-volume?ticker={ticker}",
                      headers=BACKEND_HEADERS, timeout=8)
        d = r.json().get("kwargs-after", {})
        for k in ["average_volume", "avg_volume", "volume_avg", "avg"]:
            if k in d:
                return float(d[k])
        return 0.0
    except:
        return 0.0


# ─── Alerting ─────────────────────────────────────────────────────────────────

def send_telegram_direct(message):
    import subprocess
    for chat_id in OPENCLAW_TARGET_CHATS:
        try:
            result = subprocess.run(
                [OPENCLAW_BIN, "message", "send",
                 "--channel", "telegram",
                 "--target", chat_id,
                 "--message", f"🔔 LAZYBOY ALERT\n\n{message}"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                log.info(f"OPENCLAW→{chat_id} OK")
            else:
                log.warning(f"OPENCLAW→{chat_id} FAIL: {result.stderr[:80]}")
        except Exception as e:
            log.warning(f"OpenClaw push {chat_id} failed: {e}")


def write_batch_data(ticker, data_type, data, priority=PRIORITY_LOW):
    now = time.time()
    batch_id = get_batch_id(now)
    
    entry = {
        "ts": now,
        "batch_id": batch_id,
        "ticker": ticker,
        "data_type": data_type,
        "data": data,
        "priority": priority,
    }
    
    try:
        with open(BATCH_QUEUE, "a") as f:
            f.write(_json.dumps(entry) + "\n")
    except Exception as e:
        log.error(f"Batch queue write failed: {e}")


def send_alert(ticker, alert_key, message, priority=PRIORITY_MED, data_type=DATA_PRICE_VOL):
    now = time.time()
    key = f"{ticker}:{alert_key}"
    if now - LAST_ALERT.get(key, 0) < ALERT_COOLDOWN:
        return
    LAST_ALERT[key] = now
    log.info(f"ALERT [{priority}] [{ticker}] {message[:60]}...")

    batch_id = get_batch_id(now)

    # Write to alert queue
    try:
        with open(ALERT_QUEUE, "a") as f:
            f.write(_json.dumps({
                "ts": now,
                "batch_id": batch_id,
                "ticker": ticker,
                "key": alert_key,
                "message": message,
                "priority": priority,
                "data_type": data_type,
            }) + "\n")
    except Exception as e:
        log.error(f"Queue write failed: {e}")

    # HIGH priority: push directly
    if priority == PRIORITY_HIGH:
        send_telegram_direct(message)
        write_batch_data(ticker, data_type, {"key": alert_key, "message": message}, priority)
    else:
        write_batch_data(ticker, data_type, {"key": alert_key, "message": message}, priority)


def request_analysis(ticker, reason):
    now = time.time()
    analyze_key = f"ANALYZE:{ticker}"
    
    if now - LAST_ALERT.get(analyze_key, 0) < 1800:
        return
    
    LAST_ALERT[analyze_key] = now
    log.info(f"ANALYSIS REQUEST: {ticker} — {reason}")
    
    batch_id = get_batch_id(now)
    
    try:
        with open(ALERT_QUEUE, "a") as f:
            f.write(_json.dumps({
                "ts": now,
                "batch_id": batch_id,
                "ticker": ticker,
                "key": f"ANALYZE:{ticker}",
                "message": f"🔍 ANALYSIS REQUEST: {ticker}\nReason: {reason}\nAuto-analysis triggered.",
                "priority": PRIORITY_HIGH,
                "data_type": "analysis_request",
            }) + "\n")
    except Exception as e:
        log.error(f"Analysis request write failed: {e}")


# ─── Running Trade Analysis ───────────────────────────────────────────────────

def analyze_running_trade_history(ticker: str, minutes: int = 10) -> dict:
    """
    Analyze running trades from last N minutes.
    
    Detects:
    - Retail vs big player activity (by lot size and freq)
    - Buy/sell pressure
    - Crossing detection (large aggressive trades)
    - Panic/FOMO patterns
    - Activity at S/R levels
    - Breakout/breakdown probability
    
    Based on waterseven skills/tape_reading.py (reference only).
    """
    trades = get_running_trade_history(ticker, minutes)
    
    if not trades:
        return {"status": "no_data"}
    
    # Get S/R levels from state
    state = STATE.get(ticker, {})
    support = state.get("support", 0)
    resistance = state.get("resistance", 0)
    
    # Classify trades
    retail_trades = []
    big_player_trades = []
    crossings = []
    
    # Thresholds
    RETAIL_LOT_MAX = 50  # <= 50 lots = retail
    BIG_PLAYER_LOT_MIN = 100  # >= 100 lots = big player
    CROSSING_LOT_MIN = 200  # >= 200 lots = crossing
    
    buy_lots = 0
    sell_lots = 0
    buy_freq = 0
    sell_freq = 0
    buy_count = 0
    sell_count = 0
    
    # S/R activity tracking
    trades_near_support = []
    trades_near_resistance = []
    SR_THRESHOLD_PCT = 1.0  # Within 1% of S/R
    
    # Panic/FOMO detection
    panic_sells = []  # Large sells at loss
    fomo_buys = []    # Large buys at high
    
    for trade in trades:
        lot_str = str(trade.get("lot", 0) or 0)
        lot = int(lot_str.replace(",", "")) if lot_str else 0
        trade_type = trade.get("type", "unknown")
        freq_str = str(trade.get("freq", 1) or 1)
        freq = int(freq_str.replace(",", "")) if freq_str else 1
        price_str = str(trade.get("price", 0) or 0)
        price = float(price_str.replace(",", "")) if price_str else 0.0
        
        # Update trade dict with converted values
        trade["lot"] = lot
        trade["freq"] = freq
        trade["price"] = price
        
        # Aggregate
        if trade_type == "buy":
            buy_lots += lot
            buy_freq += freq
            buy_count += 1
        elif trade_type == "sell":
            sell_lots += lot
            sell_freq += freq
            sell_count += 1
        
        # Classify by size
        if lot >= CROSSING_LOT_MIN:
            crossings.append(trade)
        
        if lot >= BIG_PLAYER_LOT_MIN:
            big_player_trades.append(trade)
        elif lot <= RETAIL_LOT_MAX:
            retail_trades.append(trade)
        
        # Check S/R proximity
        if support > 0 and price > 0:
            support_dist_pct = abs(price - support) / support * 100
            if support_dist_pct <= SR_THRESHOLD_PCT:
                trades_near_support.append(trade)
        
        if resistance > 0 and price > 0:
            res_dist_pct = abs(price - resistance) / resistance * 100
            if res_dist_pct <= SR_THRESHOLD_PCT:
                trades_near_resistance.append(trade)
    
    # Calculate ratios
    total_lots = buy_lots + sell_lots
    buy_pct = (buy_lots / total_lots * 100) if total_lots > 0 else 50
    
    # Retail vs big player ratio
    retail_lot_count = sum(t.get("lot", 0) for t in retail_trades)
    big_lot_count = sum(t.get("lot", 0) for t in big_player_trades)
    big_player_pct = (big_lot_count / total_lots * 100) if total_lots > 0 else 0
    
    # Pressure detection
    if buy_pct >= 70:
        pressure = "STRONG_BUY"
        fomo_detected = buy_count > sell_count * 2 and big_player_pct < 30
    elif buy_pct >= 55:
        pressure = "BUY"
        fomo_detected = False
    elif buy_pct <= 30:
        pressure = "STRONG_SELL"
        panic_detected = sell_count > buy_count * 2 and big_player_pct < 30
    elif buy_pct <= 45:
        pressure = "SELL"
        panic_detected = False
    else:
        pressure = "NEUTRAL"
        fomo_detected = False
        panic_detected = False
    
    # Check for panic (large sells, retail dominated)
    panic_detected = False
    if pressure in ("STRONG_SELL", "SELL") and big_player_pct < 40:
        panic_detected = True
    
    # Check for FOMO (large buys, retail dominated)
    fomo_detected = False
    if pressure in ("STRONG_BUY", "BUY") and big_player_pct < 40:
        fomo_detected = True
    
    # Dominance detection
    if big_player_pct >= 60:
        dominance = "BIG_PLAYER"
    elif big_player_pct <= 30:
        dominance = "RETAIL"
    else:
        dominance = "MIXED"
    
    # Bandar manipulation detection
    manipulation_detected = False
    manipulation_type = None
    
    # Pattern 1: Large orders but price not moving (spoofing/layering)
    if len(big_player_trades) >= 3 and abs(buy_pct - 50) < 10:
        manipulation_detected = True
        manipulation_type = "SUSPECTED_SPOOFING"
    
    # Pattern 2: Big player buying while retail selling (accumulation trap)
    if big_player_pct > 50 and buy_pct < 45:
        manipulation_detected = True
        manipulation_type = "ACCUMULATION_TRAP"
    
    # Pattern 3: Big player selling while retail buying (distribution trap)
    if big_player_pct > 50 and buy_pct > 55:
        manipulation_detected = True
        manipulation_type = "DISTRIBUTION_TRAP"
    
    # S/R activity analysis
    sr_activity = None
    if len(trades_near_support) >= 5:
        support_buy_lots = sum(t.get("lot", 0) for t in trades_near_support if t.get("type") == "buy")
        support_sell_lots = sum(t.get("lot", 0) for t in trades_near_support if t.get("type") == "sell")
        if support_buy_lots > support_sell_lots * 1.5:
            sr_activity = "SUPPORT_ACCUMULATION"
        elif support_sell_lots > support_buy_lots * 1.5:
            sr_activity = "SUPPORT_DISTRIBUTION"
        else:
            sr_activity = "SUPPORT_CONTESTED"
    
    if len(trades_near_resistance) >= 5:
        res_buy_lots = sum(t.get("lot", 0) for t in trades_near_resistance if t.get("type") == "buy")
        res_sell_lots = sum(t.get("lot", 0) for t in trades_near_resistance if t.get("type") == "sell")
        if res_buy_lots > res_sell_lots * 1.5:
            sr_activity = "RESISTANCE_ATTACK"
        elif res_sell_lots > res_buy_lots * 1.5:
            sr_activity = "RESISTANCE_DEFENDED"
        else:
            sr_activity = "RESISTANCE_CONTESTED"
    
    # Breakout/breakdown probability
    breakout_prob = 0
    breakdown_prob = 0
    
    # Breakout signals
    if resistance > 0:
        latest_price = trades[-1].get("price", 0) if trades else 0
        if latest_price > 0:
            # Near resistance + high buy pressure + crossings
            if trades_near_resistance and buy_pct > 60 and len(crossings) >= 3:
                breakout_prob = 70
            elif trades_near_resistance and buy_pct > 55:
                breakout_prob = 50
            elif buy_pct > 65 and dominance == "BIG_PLAYER":
                breakout_prob = 40
    
    # Breakdown signals
    if support > 0:
        latest_price = trades[-1].get("price", 0) if trades else 0
        if latest_price > 0:
            # Near support + high sell pressure + crossings
            if trades_near_support and sell_lots > buy_lots * 1.5 and len(crossings) >= 3:
                breakdown_prob = 70
            elif trades_near_support and sell_lots > buy_lots:
                breakdown_prob = 50
            elif sell_lots > buy_lots * 1.5 and dominance == "RETAIL":
                breakdown_prob = 40
    
    return {
        "status": "ok",
        "minutes": minutes,
        "trade_count": len(trades),
        "buy_lots": buy_lots,
        "sell_lots": sell_lots,
        "buy_pct": round(buy_pct, 1),
        "pressure": pressure,
        "retail_trades": len(retail_trades),
        "big_player_trades": len(big_player_trades),
        "big_player_pct": round(big_player_pct, 1),
        "dominance": dominance,
        "crossings": len(crossings),
        "crossing_details": crossings[:5],
        "panic_detected": panic_detected,
        "fomo_detected": fomo_detected,
        "manipulation_detected": manipulation_detected,
        "manipulation_type": manipulation_type,
        "sr_activity": sr_activity,
        "trades_near_support": len(trades_near_support),
        "trades_near_resistance": len(trades_near_resistance),
        "breakout_prob": breakout_prob,
        "breakdown_prob": breakdown_prob,
    }


# ─── Orderbook Analysis ───────────────────────────────────────────────────────

def analyze_orderbook(ticker, data):
    """
    Analyze orderbook for bid-offer signal.
    Enhanced with fast_pace signals from waterseven reference.
    """
    if not data:
        return None, None
    
    try:
        bids = data.get("bid", [])
        offers = data.get("offer", [])
        
        if not bids or not offers:
            return None, None
        
        # Calculate bid-offer ratio
        total_bid_lots = sum(b.get("lot", 0) for b in bids[:5])
        total_offer_lots = sum(o.get("lot", 0) for o in offers[:5])
        
        if total_offer_lots > 0:
            bid_offer_ratio = total_bid_lots / total_offer_lots
        else:
            bid_offer_ratio = 999.0 if total_bid_lots > 0 else 1.0
        
        # Check for large walls
        large_bids = [b for b in bids[:5] if b.get("lot", 0) >= LARGE_LOT_THRESHOLD]
        large_offers = [o for o in offers[:5] if o.get("lot", 0) >= LARGE_LOT_THRESHOLD]
        
        # Best bid/offer prices
        best_bid = bids[0].get("price", 0) if bids else 0
        best_offer = offers[0].get("price", 0) if offers else 0
        mid_price = (best_bid + best_offer) / 2 if best_bid and best_offer else 0
        
        # Signal detection (enhanced from fast_pace_daemon)
        signal = "NEUTRAL"
        details = f"B/O: {bid_offer_ratio:.1f}x"
        
        # 1. THICK_BID_NEAR - Large bid wall near price
        if bid_offer_ratio >= 2.0 and len(large_bids) >= 2:
            signal = "THICK_BID_NEAR"
            details = f"B/O: {bid_offer_ratio:.1f}x, {len(large_bids)} large bids near price"
        # 2. THICK_BID_FAR - Large bids but not near price
        elif bid_offer_ratio >= 1.5 and large_bids:
            signal = "THICK_BID_FAR"
            details = f"B/O: {bid_offer_ratio:.1f}x, accumulation zone"
        # 3. DISTRIBUTION_WARNING - Heavy offer side
        elif bid_offer_ratio <= 0.5 and len(large_offers) >= 2:
            signal = "DISTRIBUTION_WARNING"
            details = f"B/O: {bid_offer_ratio:.1f}x, {len(large_offers)} large offers"
        # 4. OFFER_PRESSURE - General selling
        elif bid_offer_ratio <= 0.67:
            signal = "OFFER_PRESSURE"
            details = f"B/O: {bid_offer_ratio:.1f}x, offer dominance"
        # 5. BID_WITHDRAWAL - Large bids disappearing (would need delta, simplified here)
        # 6. BREAKOUT_IMMINENT - Strong bid near resistance (would need price context)
        
        return signal, details
        
    except Exception as e:
        log.warning(f"Orderbook analysis failed for {ticker}: {e}")
        return None, None


def check_orderbook_signal(ticker, state):
    """Check orderbook and write to batch queue."""
    now = time.time()
    
    # Only check every 3 minutes
    if now - state.get("last_orderbook_check", 0) < 180:
        return
    
    state["last_orderbook_check"] = now
    
    data = get_orderbook_stockbit(ticker)
    if not data:
        return
    
    signal, details = analyze_orderbook(ticker, data)
    
    if signal:
        prev_signal = state.get("orderbook_signal")
        state["orderbook_signal"] = signal
        
        # Write to batch queue
        bids = data.get("bid", [])
        offers = data.get("offer", [])
        total_bid_lots = sum(b.get("lot", 0) for b in bids[:5])
        total_offer_lots = sum(o.get("lot", 0) for o in offers[:5])
        bid_offer_ratio = total_bid_lots / total_offer_lots if total_offer_lots > 0 else 1.0
        
        write_batch_data(ticker, DATA_ORDERBOOK, {
            "signal": signal,
            "details": details,
            "bid_offer_ratio": round(bid_offer_ratio, 2),
            "total_bid_lots": total_bid_lots,
            "total_offer_lots": total_offer_lots,
        }, priority=PRIORITY_LOW)
        
        # Alert on significant signal changes
        if signal in ("THICK_BID_NEAR", "DISTRIBUTION_WARNING") and signal != prev_signal:
            emoji = "🟢" if signal == "THICK_BID_NEAR" else "🔴"
            send_alert(ticker, f"ob_{signal.lower()}",
                f"{emoji} {ticker}: {signal.replace('_', ' ')}\n{details}",
                priority=PRIORITY_MED, data_type=DATA_ORDERBOOK)


# ─── Crossing Detection ───────────────────────────────────────────────────────

def detect_crossing(ticker, trades, avg_vol):
    """Detect crossing trades (large aggressive orders)."""
    if not trades or not avg_vol:
        return []
    
    crossings = []
    
    for trade in trades[:30]:
        try:
            lot = trade.get("lot", 0)
            price = trade.get("price", 0)
            trade_type = trade.get("type", "")  # "buy" or "sell"
            
            # Crossing = large lot + aggressive
            if lot >= LARGE_LOT_THRESHOLD:
                crossings.append({
                    "price": price,
                    "lot": lot,
                    "type": trade_type,
                })
        except:
            continue
    
    return crossings


def check_crossing(ticker, state):
    """Check for crossing trades and write to batch queue."""
    trades = get_running_trade_stockbit(ticker, limit=50)
    if not trades:
        return
    
    avg_vol = state.get("avg_volume", 0)
    
    crossings = detect_crossing(ticker, trades, avg_vol)
    
    if crossings:
        write_batch_data(ticker, DATA_CROSSING, {
            "count": len(crossings),
            "crossings": crossings[:5],
        }, priority=PRIORITY_LOW)
        
        if len(crossings) >= 3:
            trade_type = crossings[0].get("type", "buy")
            emoji = "📈" if trade_type == "buy" else "📉"
            send_alert(ticker, "crossing_detected",
                f"{emoji} {ticker}: {len(crossings)} large trades detected\n"
                f"Aggressive {trade_type}ing - lots up to {crossings[0]['lot']}",
                priority=PRIORITY_MED, data_type=DATA_CROSSING)


# ─── Fallback Check ───────────────────────────────────────────────────────────

def check_queue_fallback():
    try:
        if os.path.exists(SENT_FILE):
            last_read = os.path.getmtime(SENT_FILE)
            time_since_read = time.time() - last_read
        else:
            time_since_read = 999999

        if time_since_read <= FALLBACK_STALE_SECONDS:
            return

        log.warning(f"Queue not read for {time_since_read/60:.0f} min. Fallback.")

        if not os.path.exists(ALERT_QUEUE):
            return

        already_read = _load_lines(SENT_FILE)
        already_fallback_sent = _load_lines(FALLBACK_SENT_FILE)

        with open(ALERT_QUEUE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = _json.loads(line)
                except:
                    continue

                k = f"{entry.get('ts')}:{entry.get('key')}"
                if k in already_read or k in already_fallback_sent:
                    continue

                if entry.get("key") == "pulse":
                    continue
                if entry.get("priority") == PRIORITY_LOW:
                    continue

                msg = entry.get("message", "")
                if not msg:
                    continue

                send_telegram_direct(msg)
                _append_line(FALLBACK_SENT_FILE, k)

    except Exception as e:
        log.error(f"Fallback check failed: {e}")


# ─── Trade Plan Level Checker ─────────────────────────────────────────────────

def check_trade_plan(ticker, price, state):
    plan = TRADE_PLANS.get(ticker)
    if not plan:
        return

    triggered = state["trade_plan_triggered"]

    for level in plan["levels"]:
        key = level["key"]
        if key in triggered:
            continue

        target_price = level["price"]
        direction = level["direction"]
        hit = False

        if direction == "above" and price >= target_price:
            hit = True
        elif direction == "below" and price <= target_price:
            hit = True

        if hit:
            triggered.add(key)
            msg = f"{level['message']}\nCurrent: {price:,.0f}"
            send_alert(ticker, f"plan_{key}", msg, priority=level.get("priority", PRIORITY_HIGH))
            log.info(f"TRADE PLAN TRIGGERED: {ticker} {key} at {price}")


# ─── Per-ticker Logic ─────────────────────────────────────────────────────────

def analyze(ticker, price, volume, avg_vol, cfg, state):
    if not price:
        return

    open_p = state["open_price"] or price
    move_pct = ((price - open_p) / open_p * 100) if open_p else 0
    vol_ratio = (volume / avg_vol) if avg_vol > 0 else 0
    alerted = state["alerted"]
    min_vr = cfg.get("min_vol_ratio", 1.2)

    state["intraday_low_pct"] = min(state["intraday_low_pct"], move_pct)
    state["intraday_high_pct"] = max(state["intraday_high_pct"], move_pct)

    # Check trade plan
    check_trade_plan(ticker, price, state)

    # Check orderbook
    check_orderbook_signal(ticker, state)

    # Check crossing
    check_crossing(ticker, state)

    # ESSA / ITMG logic
    if ticker in ("ESSA", "ITMG"):
        entry_pb = cfg.get("entry_pullback")
        entry_bo = cfg.get("entry_breakout")
        sl = cfg.get("stop_loss")
        tgt = cfg.get("target")

        # BREAKOUT
        if entry_bo and price >= entry_bo:
            if vol_ok(vol_ratio, min_vr) and "breakout_confirmed" not in alerted:
                alerted.add("breakout_confirmed")
                send_alert(ticker, "breakout_confirmed",
                    f"🚀 {ticker} BREAKOUT — BUY NOW\n"
                    f"Price: {price:,.0f} | Break: {entry_bo:,.0f}\n"
                    f"{vol_label(vol_ratio)}\n"
                    f"Target: {tgt:,.0f} | CL: {sl:,.0f}\n"
                    f"Volume confirmed. GO.",
                    priority=PRIORITY_HIGH
                )
                request_analysis(ticker, f"Breakout at {entry_bo:,.0f} with vol {vol_ratio:.1f}x")
            elif not vol_ok(vol_ratio, min_vr) and "breakout_thinvol" not in alerted:
                alerted.add("breakout_thinvol")
                send_alert(ticker, "breakout_thinvol",
                    f"⚠️ {ticker} at breakout level {entry_bo:,.0f} — but {vol_label(vol_ratio)}\n"
                    f"Price: {price:,.0f} | WAIT. No volume confirmation yet.",
                    priority=PRIORITY_MED
                )

        # PULLBACK
        if entry_pb and price <= entry_pb and (not sl or price > sl):
            if vol_ok(vol_ratio, min_vr) and "pullback_confirmed" not in alerted:
                alerted.add("pullback_confirmed")
                send_alert(ticker, "pullback_confirmed",
                    f"📥 {ticker} PULLBACK ENTRY — BUY NOW\n"
                    f"Price: {price:,.0f} | Zone: ≤{entry_pb:,.0f}\n"
                    f"{vol_label(vol_ratio)}\n"
                    f"Target: {tgt:,.0f} | CL: {sl:,.0f}\n"
                    f"Volume holding. Thesis intact. GO.",
                    priority=PRIORITY_HIGH
                )
            elif not vol_ok(vol_ratio, min_vr) and "pullback_thinvol" not in alerted:
                alerted.add("pullback_thinvol")
                send_alert(ticker, "pullback_thinvol",
                    f"👀 {ticker} in entry zone {price:,.0f} — but {vol_label(vol_ratio)}\n"
                    f"Thin volume. Could drift lower. WAIT for volume.\n"
                    f"Zone: ≤{entry_pb:,.0f} | CL: {sl:,.0f}",
                    priority=PRIORITY_MED
                )

        # STOP LOSS
        if sl and price <= sl and "stoploss" not in alerted:
            alerted.add("stoploss")
            send_alert(ticker, "stoploss",
                f"🚨 {ticker} BROKE STOP LOSS\n"
                f"Price: {price:,.0f} | Stop: {sl:,.0f}\n"
                f"EXIT if holding. Thesis invalidated.",
                priority=PRIORITY_HIGH
            )

    # VKTR
    elif ticker == "VKTR":
        entry_bo = cfg.get("entry_breakout")
        sl = cfg.get("stop_loss")
        tgt = cfg.get("target")
        if entry_bo and price >= entry_bo and vol_ok(vol_ratio, min_vr) and "breakout_confirmed" not in alerted:
            alerted.add("breakout_confirmed")
            send_alert(ticker, "breakout_confirmed",
                f"🔋 VKTR BREAKOUT — BUY\n"
                f"Price: {price} | Break: {entry_bo}\n"
                f"{vol_label(vol_ratio)}\n"
                f"Target: {tgt} | CL: {sl}\n"
                f"EV theme. Volume confirmed.",
                priority=PRIORITY_HIGH
            )

    # Big moves
    threshold = cfg.get("alert_move_pct", 2.5)
    if abs(move_pct) >= threshold:
        direction = "UP" if move_pct > 0 else "DOWN"
        key = f"move_{direction}_{int(abs(move_pct))}"
        if key not in alerted:
            alerted.add(key)
            if vol_ok(vol_ratio, min_vr):
                emoji = "📈" if move_pct > 0 else "📉"
                send_alert(ticker, key,
                    f"{emoji} {ticker} {move_pct:+.1f}% FROM OPEN\n"
                    f"Price: {price} | Open: {open_p}\n"
                    f"{vol_label(vol_ratio)}\n"
                    f"Worth checking.",
                    priority=PRIORITY_MED
                )
                if abs(move_pct) >= 3.0 and vol_ratio >= 2.0:
                    request_analysis(ticker, f"Big move {move_pct:+.1f}% with vol {vol_ratio:.1f}x")

    # Panic reversal
    if (
        state["intraday_low_pct"] <= PANIC_DROP_PCT
        and move_pct >= REVERSAL_RECOVERY_PCT
        and vol_ok(vol_ratio, max(min_vr, REVERSAL_MIN_VOL))
        and "panic_reversal" not in alerted
    ):
        alerted.add("panic_reversal")
        send_alert(
            ticker,
            "panic_reversal",
            f"⚡ {ticker} PANIC → MOMENTUM REVERSAL\n"
            f"Low: {state['intraday_low_pct']:+.1f}% | Now: {move_pct:+.1f}%\n"
            f"Price: {price:,.0f} | Open: {open_p:,.0f}\n"
            f"{vol_label(vol_ratio)}\n"
            f"Failed breakdown detected. Starter entry allowed (tight risk).",
            priority=PRIORITY_HIGH
        )
        request_analysis(ticker, f"Panic reversal from {state['intraday_low_pct']:+.1f}% to {move_pct:+.1f}%")


# ─── Main Loop ────────────────────────────────────────────────────────────────

def is_market_open():
    now = datetime.now(WIB)
    if now.weekday() >= 5:
        return False
    t = now.hour * 60 + now.minute
    return 9 * 60 <= t <= 15 * 60 + 15


def run():
    log.info("🛋️  Lazyboy Monitor v3.2 started (10-min Evaluation)")
    log.info(f"Watching: {', '.join(WATCHLIST.keys())}")
    log.info(f"Evaluation: every 10 minutes | Heartbeat: every 30 minutes")
    
    # Check Redis
    r = get_redis()
    if r:
        log.info("✅ Redis connected")
    else:
        log.warning("⚠️ Redis not available - using memory only")
    
    # Fetch Stockbit token
    token = get_stockbit_token()
    if token:
        log.info("✅ Stockbit token OK")
    else:
        log.warning("⚠️ No Stockbit token - some features disabled")
    
    # Fetch avg volumes
    log.info("Fetching average volumes...")
    for ticker in WATCHLIST:
        av = get_avg_volume_backend(ticker)
        STATE[ticker]["avg_volume"] = av
        log.info(f"  {ticker} avg_vol: {av:,.0f}")

    # Track 10-minute evaluation cycles
    last_eval_cycle = -1
    EVAL_INTERVAL_MIN = 10  # Evaluate every 10 minutes
    
    # Insight accumulator for 30-min dataset
    insight_accumulator = {}  # {ticker: [insights...]}
    INSIGHT_DATASET = "/home/lazywork/lazyboy/trade/data/monitor_insights.jsonl"
    
    while True:
        now = datetime.now(WIB)
        
        if not is_market_open():
            log.info(f"Market closed ({now.strftime('%H:%M')} WIB). Sleeping 60s...")
            time.sleep(60)
            continue
        
        # Calculate current 10-min cycle (0-5 for each hour)
        # 09:00-09:09 = cycle 0, 09:10-09:19 = cycle 1, etc.
        current_cycle = (now.hour * 60 + now.minute) // EVAL_INTERVAL_MIN
        
        # Check if we should run evaluation (new cycle)
        if current_cycle != last_eval_cycle:
            log.info(f"━━━ 10-MIN EVALUATION (cycle {current_cycle}) ━━━")
            
            for ticker in WATCHLIST:
                # Get price from Redis orderbook or fallback
                ob_data = get_orderbook_from_redis(ticker)
                if ob_data and ob_data.get("bids") and ob_data.get("offers"):
                    bids = ob_data.get("bids", [])
                    offers = ob_data.get("offers", [])
                    if bids and offers:
                        best_bid = float(bids[0].get("price", 0) or 0)
                        best_offer = float(offers[0].get("price", 0) or 0)
                        price = (best_bid + best_offer) / 2 if (best_bid and best_offer) else 0
                    else:
                        price = get_price_stockbit(ticker)
                else:
                    price = get_price_stockbit(ticker)
                    # Fallback: fetch orderbook from API
                    ob_data = get_orderbook_stockbit(ticker) or {"bid": [], "offer": []}
                
                if not price:
                    continue
                
                # Get volume
                volume = get_volume_backend(ticker)
                
                # Get support/resistance
                try:
                    sr_resp = httpx.get(
                        f"{BACKEND_URL}/data/signal/support-resistance?ticker={ticker}",
                        headers=BACKEND_HEADERS,
                        timeout=8
                    )
                    sr = sr_resp.json().get("kwargs-after", {})
                    support = sr.get("current_support_value", 0)
                    resistance = sr.get("current_resistance_value", 0)
                except:
                    support = 0
                    resistance = 0
                
                # Update state with S/R
                state = STATE[ticker]
                state["support"] = support
                state["resistance"] = resistance
                
                # Get running trade history (10 min)
                trade_analysis = analyze_running_trade_history(ticker, minutes=10)
                
                # Analyze orderbook
                ob_signal, ob_details = analyze_orderbook(ticker, ob_data)
                
                # ─── 4 ADVANCED DETECTIONS ─────────────────────────────────────
                
                # 1. Fake wall detection
                prev_ob = _orderbook_history.get(ticker, [{}])[-1] if ticker in _orderbook_history else None
                fake_wall = detect_fake_wall(ticker, ob_data, prev_ob)
                
                # Store current orderbook for next comparison
                if ticker not in _orderbook_history:
                    _orderbook_history[ticker] = []
                _orderbook_history[ticker].append({"ts": time.time(), **ob_data})
                # Keep only last 10 snapshots
                if len(_orderbook_history[ticker]) > 10:
                    _orderbook_history[ticker].pop(0)
                
                # 2. Bot pattern detection
                trade_history = get_running_trade_history(ticker, minutes=10)
                bot_pattern = detect_bot_pattern(trade_history)
                
                # 3. Jebakan tektok detection
                tektok_trap = detect_jebakan_tektok(ticker, minutes=30)
                
                # 4. Liquidity sweep detection
                liquidity_sweep = detect_liquidity_sweep(ticker, support, resistance)
                
                # ─── ALERTS FOR DETECTIONS ────────────────────────────────────
                
                # Fake wall alert
                if fake_wall.get("detected"):
                    wall_type = "BID" if fake_wall.get("fake_bid_wall") else "OFFER"
                    emoji = "🔴" if fake_wall.get("fake_bid_wall") else "🟢"
                    send_alert(ticker, "fake_wall",
                        f"{emoji} {ticker}: FAKE {wall_type} WALL detected\n"
                        f"Wall disappeared as price approached. Manipulation signal.",
                        priority=PRIORITY_MED, data_type="detection")
                
                # Jebakan tektok alert
                if tektok_trap.get("detected"):
                    send_alert(ticker, "tektok_trap",
                        f"⚠️ {ticker}: JEBAKAN TEKTOK detected!\n"
                        f"Slow grind → sudden dump. Distribution trap.\n"
                        f"Dump ratio: {tektok_trap.get('dump_ratio', 0)}x",
                        priority=PRIORITY_HIGH, data_type="detection")
                
                # Liquidity sweep alert
                if liquidity_sweep.get("detected"):
                    sweep_type = liquidity_sweep.get("type", "")
                    if "bullish" in sweep_type:
                        emoji = "🟢"
                        msg = f"{emoji} {ticker}: BULLISH LIQUIDITY SWEEP\n"
                        msg += f"Dip below {support:.0f}, recovered to {liquidity_sweep.get('recovery', 0):.0f}\n"
                        msg += f"Break volume: {liquidity_sweep.get('break_volume_pct', 0)}%"
                    else:
                        emoji = "🔴"
                        msg = f"{emoji} {ticker}: BEARISH LIQUIDITY SWEEP\n"
                        msg += f"Spike above {resistance:.0f}, rejected to {liquidity_sweep.get('rejection', 0):.0f}\n"
                        msg += f"Break volume: {liquidity_sweep.get('break_volume_pct', 0)}%"
                    send_alert(ticker, "liquidity_sweep", msg, priority=PRIORITY_MED, data_type="detection")
                
                # Update state
                state = STATE[ticker]
                if state["open_price"] == 0:
                    state["open_price"] = price
                state["price"] = price
                state["volume"] = volume
                state["orderbook_signal"] = ob_signal
                
                # Calculate change
                op = state["open_price"]
                pct = ((price - op) / op * 100) if op else 0
                vol_ratio = (volume / state["avg_volume"]) if state["avg_volume"] else 0
                
                # Write to batch queue for heartbeat
                write_batch_data(ticker, "eval_10min", {
                    "price": price,
                    "open": op,
                    "change_pct": round(pct, 2),
                    "volume": volume,
                    "vol_ratio": round(vol_ratio, 2),
                    "trade_analysis": trade_analysis,
                    "orderbook_signal": ob_signal,
                    "orderbook_details": ob_details,
                }, priority=PRIORITY_LOW)
                
                # Check for significant patterns → alert
                if trade_analysis.get("status") == "ok":
                    pressure = trade_analysis.get("pressure", "")
                    dominance = trade_analysis.get("dominance", "")
                    crossings = trade_analysis.get("crossings", 0)
                    
                    # Strong pressure + big player
                    if pressure in ("STRONG_BUY", "STRONG_SELL") and dominance == "BIG_PLAYER":
                        emoji = "🟢" if pressure == "STRONG_BUY" else "🔴"
                        send_alert(ticker, f"eval_{pressure.lower()}",
                            f"{emoji} {ticker}: {pressure} ({dominance})\n"
                            f"Buy: {trade_analysis['buy_pct']:.0f}% | Crossings: {crossings}\n"
                            f"OB: {ob_signal} | Change: {pct:+.1f}%",
                            priority=PRIORITY_MED, data_type="eval")
                    
                    # Multiple crossings
                    if crossings >= 5:
                        send_alert(ticker, "eval_crossings",
                            f"📊 {ticker}: {crossings} crossing trades in 10 min\n"
                            f"Pressure: {pressure} | Dominance: {dominance}",
                            priority=PRIORITY_MED, data_type="eval")
                
                log.info(f"  {ticker}: {pct:+.1f}% | {trade_analysis.get('pressure', '?')} | OB: {ob_signal}")
                
                # Accumulate insight for 30-min dataset
                if ticker not in insight_accumulator:
                    insight_accumulator[ticker] = []
                
                insight_accumulator[ticker].append({
                    "ts": time.time(),
                    "cycle": current_cycle,
                    "price": price,
                    "support": state.get("support", 0),
                    "resistance": state.get("resistance", 0),
                    "change_pct": round(pct, 2),
                    "vol_ratio": round(vol_ratio, 2),
                    "pressure": trade_analysis.get("pressure"),
                    "dominance": trade_analysis.get("dominance"),
                    "big_player_pct": trade_analysis.get("big_player_pct", 0),
                    "crossings": trade_analysis.get("crossings", 0),
                    "orderbook_signal": ob_signal,
                    "panic_detected": trade_analysis.get("panic_detected", False),
                    "fomo_detected": trade_analysis.get("fomo_detected", False),
                    "manipulation_detected": trade_analysis.get("manipulation_detected", False),
                    "manipulation_type": trade_analysis.get("manipulation_type"),
                    "sr_activity": trade_analysis.get("sr_activity"),
                    "breakout_prob": trade_analysis.get("breakout_prob", 0),
                    "breakdown_prob": trade_analysis.get("breakdown_prob", 0),
                    # Advanced detections
                    "fake_wall": fake_wall.get("detected", False),
                    "fake_wall_type": "bid" if fake_wall.get("fake_bid_wall") else "offer" if fake_wall.get("fake_offer_wall") else None,
                    "bot_pattern": bot_pattern.get("detected", False),
                    "bot_lot_size": bot_pattern.get("lot_size"),
                    "tektok_trap": tektok_trap.get("detected", False),
                    "liquidity_sweep": liquidity_sweep.get("detected", False),
                    "sweep_type": liquidity_sweep.get("type"),
                })
            
            last_eval_cycle = current_cycle
            log.info(f"✅ Evaluation complete. Next in 10 minutes.")
            
            # ─── 30-MIN INSIGHT DATASET WRITE ─────────────────────────────────
            # Write every 30 minutes (cycles 0, 3 per hour: 09:00, 09:30, 10:00, ...)
            if current_cycle % 3 == 0:
                log.info(f"📝 Writing 30-min insights to dataset...")
                
                insight_record = {
                    "ts": time.time(),
                    "datetime": now.isoformat(),
                    "cycle": current_cycle,
                    "tickers": {},
                }
                
                for ticker, insights in insight_accumulator.items():
                    if not insights:
                        continue
                    
                    # Aggregate 30-min insights
                    avg_change = sum(i["change_pct"] for i in insights) / len(insights)
                    avg_vol_ratio = sum(i["vol_ratio"] for i in insights) / len(insights)
                    avg_big_player_pct = sum(i.get("big_player_pct", 0) for i in insights) / len(insights)
                    
                    # Count pressure patterns
                    pressures = [i["pressure"] for i in insights if i.get("pressure")]
                    dominant_pressure = max(set(pressures), key=pressures.count) if pressures else None
                    
                    # Count orderbook signals
                    ob_signals = [i["orderbook_signal"] for i in insights if i.get("orderbook_signal")]
                    dominant_ob = max(set(ob_signals), key=ob_signals.count) if ob_signals else None
                    
                    # Total crossings
                    total_crossings = sum(i.get("crossings", 0) for i in insights)
                    
                    # Panic/FOMO/Manipulation counts
                    panic_count = sum(1 for i in insights if i.get("panic_detected"))
                    fomo_count = sum(1 for i in insights if i.get("fomo_detected"))
                    manipulation_count = sum(1 for i in insights if i.get("manipulation_detected"))
                    
                    # S/R activity
                    sr_activities = [i.get("sr_activity") for i in insights if i.get("sr_activity")]
                    dominant_sr_activity = max(set(sr_activities), key=sr_activities.count) if sr_activities else None
                    
                    # Breakout/breakdown probability
                    max_breakout_prob = max(i.get("breakout_prob", 0) for i in insights)
                    max_breakdown_prob = max(i.get("breakdown_prob", 0) for i in insights)
                    
                    # Advanced detections
                    fake_wall_count = sum(1 for i in insights if i.get("fake_wall"))
                    bot_pattern_count = sum(1 for i in insights if i.get("bot_pattern"))
                    tektok_trap_count = sum(1 for i in insights if i.get("tektok_trap"))
                    liquidity_sweep_count = sum(1 for i in insights if i.get("liquidity_sweep"))
                    
                    # Sweep types
                    sweep_types = [i.get("sweep_type") for i in insights if i.get("sweep_type")]
                    dominant_sweep_type = max(set(sweep_types), key=sweep_types.count) if sweep_types else None
                    
                    # Latest data
                    latest = insights[-1]
                    latest_price = latest.get("price", 0)
                    support = latest.get("support", 0)
                    resistance = latest.get("resistance", 0)
                    
                    # Build data dict for insight generation
                    ticker_data = {
                        "latest_price": latest_price,
                        "support": support,
                        "resistance": resistance,
                        "avg_change_pct": round(avg_change, 2),
                        "avg_vol_ratio": round(avg_vol_ratio, 2),
                        "avg_big_player_pct": round(avg_big_player_pct, 1),
                        "dominant_pressure": dominant_pressure,
                        "dominant_orderbook": dominant_ob,
                        "total_crossings": total_crossings,
                        "panic_count": panic_count,
                        "fomo_count": fomo_count,
                        "manipulation_count": manipulation_count,
                        "dominant_sr_activity": dominant_sr_activity,
                        "max_breakout_prob": max_breakout_prob,
                        "max_breakdown_prob": max_breakdown_prob,
                        "fake_wall_count": fake_wall_count,
                        "bot_pattern_count": bot_pattern_count,
                        "tektok_trap_count": tektok_trap_count,
                        "liquidity_sweep_count": liquidity_sweep_count,
                        "dominant_sweep_type": dominant_sweep_type,
                        "sample_count": len(insights),
                    }
                    
                    # Generate AI insight
                    ai_insight = generate_ticker_insight(ticker, ticker_data)
                    
                    insight_record["tickers"][ticker] = {
                        **ticker_data,
                        "insight": ai_insight,
                    }
                
                # Write to dataset file
                try:
                    with open(INSIGHT_DATASET, "a") as f:
                        f.write(_json.dumps(insight_record) + "\n")
                    log.info(f"✅ Insights written for {len(insight_record['tickers'])} tickers")
                    
                    # Log interesting events
                    for ticker, data in insight_record["tickers"].items():
                        if any([
                            abs(data.get("avg_change_pct", 0)) >= 3,
                            data.get("tektok_trap_count", 0) > 0,
                            data.get("liquidity_sweep_count", 0) > 0,
                            data.get("panic_count", 0) >= 2,
                        ]):
                            log.info(f"⚡ {ticker}: {data.get('insight', '')}")
                except Exception as e:
                    log.error(f"Failed to write insights: {e}")
                
                # Clear accumulator for next 30 min
                insight_accumulator = {}
            
            # ─── END-OF-DAY RECAP (15:30 WIB) ─────────────────────────────────
            if now.hour == 15 and now.minute >= 30 and now.minute < 40:
                log.info("📝 Writing end-of-day recap...")
                
                # Read all insights from today
                try:
                    import glob
                    insight_files = glob.glob(f"{INSIGHT_DATASET}*")
                    all_insights = {}
                    
                    for fpath in sorted(insight_files):
                        try:
                            with open(fpath) as f:
                                for line in f:
                                    record = _json.loads(line)
                                    for ticker, data in record.get("tickers", {}).items():
                                        if ticker not in all_insights:
                                            all_insights[ticker] = data
                        except:
                            continue
                    
                    # Write daily recap
                    write_daily_recap(all_insights)
                except Exception as e:
                    log.error(f"End-of-day recap failed: {e}")
        
        # Sleep until next check (60 seconds)
        time.sleep(60)


if __name__ == "__main__":
    run()
