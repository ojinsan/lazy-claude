"""
Wyckoff Phase Detection + Smart Money Index (SMI)
==================================================
Detect accumulation, markup, distribution, markdown phases.
Track smart money behavior via price-volume structure, not broker codes.

Based on: smartmoneyflow.id methodology
"""

import httpx
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Literal
from dataclasses import dataclass

log = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
BASE_URL = "http://43.173.164.222:8080"
TOKEN = "6697ed8a65e1bf92bdbe4cd1aa2d64dcbeb91a0d9c39a35d0a245b830524fe92"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# Phase definitions
Phase = Literal["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN", "UNKNOWN"]


@dataclass
class WyckoffAnalysis:
    ticker: str
    phase: Phase
    smi_trend: str  # "RISING", "FLAT", "FALLING"
    structure: str  # "HH-HL", "LH-LL", "RANGE"
    volume_pattern: str  # "DECLINING", "HEALTHY", "SPIKE"
    signals: list[str]
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    summary: str


def get_price_history(ticker: str, days: int = 30) -> list[dict]:
    """Fetch price history for structure analysis from Stockbit."""
    try:
        # Use Stockbit candles (proper OHLCV)
        from . import api
        candles = api.get_candles(ticker, timeframe="1d", limit=min(days, 100))
        if candles:
            return candles
    except Exception as e:
        log.warning(f"Stockbit candles fetch failed for {ticker}: {e}")
    
    # Fallback: backend current-price (tick data aggregation)
    try:
        r = httpx.get(
            f"{BASE_URL}/data/signal/current-price",
            params={"ticker": ticker},
            headers=HEADERS,
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("kwargs-after", {})
            prices = data.get("prices", [])
            if prices and len(prices) > 0:
                candles = []
                candle_size = max(1, len(prices) // 50)
                for i in range(0, len(prices), candle_size):
                    chunk = prices[i:i+candle_size]
                    if chunk:
                        candles.append({
                            "open": chunk[0],
                            "high": max(chunk),
                            "low": min(chunk),
                            "close": chunk[-1],
                            "volume": 0
                        })
                return candles
    except Exception as e:
        log.warning(f"Price history fetch failed for {ticker}: {e}")
    return []


def get_volume_history(ticker: str, days: int = 30) -> list[dict]:
    """Fetch volume history for pattern analysis from Stockbit candles."""
    try:
        # Use same candles as price history (already includes volume)
        from . import api
        candles = api.get_candles(ticker, timeframe="1d", limit=min(days, 100))
        if candles:
            return [{"volume": c.get("volume", 0), "date": c.get("date")} for c in candles]
    except Exception as e:
        log.warning(f"Volume history fetch failed for {ticker}: {e}")
    return []


def analyze_structure(prices: list[dict]) -> tuple[str, str]:
    """
    Analyze price structure.
    Returns: (structure, trend)
    - structure: "HH-HL" (uptrend), "LH-LL" (downtrend), "RANGE"
    - trend: "UP", "DOWN", "SIDEWAYS"
    """
    if len(prices) < 10:
        return "RANGE", "SIDEWAYS"
    
    closes = [p.get("close", 0) for p in prices[-20:]]
    if not closes:
        return "RANGE", "SIDEWAYS"
    
    # Find swing highs and lows
    highs = []
    lows = []
    for i in range(1, len(closes) - 1):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1]:
            highs.append(closes[i])
        elif closes[i] < closes[i-1] and closes[i] < closes[i+1]:
            lows.append(closes[i])
    
    # Determine structure
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "HH-HL", "UP"
        elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "LH-LL", "DOWN"
    
    # Fallback: simple trend
    if closes[-1] > closes[0]:
        return "HH-HL", "UP"
    elif closes[-1] < closes[0]:
        return "LH-LL", "DOWN"
    
    return "RANGE", "SIDEWAYS"


def analyze_volume_pattern(volumes: list[dict]) -> tuple[str, str]:
    """
    Analyze volume pattern.
    Returns: (pattern, health)
    - pattern: "DECLINING", "HEALTHY", "SPIKE", "THIN"
    - health: "GOOD", "WARNING", "BAD"
    """
    if len(volumes) < 5:
        return "THIN", "WARNING"
    
    vols = [v.get("volume", 0) for v in volumes[-10:]]
    if not vols:
        return "THIN", "WARNING"
    
    avg = sum(vols) / len(vols)
    recent = vols[-3:]
    recent_avg = sum(recent) / len(recent)
    
    # Spike detection
    if recent_avg > avg * 2:
        return "SPIKE", "WARNING"
    
    # Declining
    if recent_avg < avg * 0.5:
        return "DECLINING", "GOOD"  # Good for accumulation
    
    # Healthy
    if 0.8 * avg <= recent_avg <= 1.5 * avg:
        return "HEALTHY", "GOOD"
    
    return "THIN", "WARNING"


def detect_spring(prices: list[dict], support_level: float) -> bool:
    """
    Detect spring pattern (false break below support).
    - Price briefly breaks support
    - Quickly recovers back above
    """
    if len(prices) < 5:
        return False
    
    for i in range(len(prices) - 3):
        low = prices[i].get("low", 0)
        close = prices[i].get("close", 0)
        next_close = prices[i+1].get("close", 0)
        
        # Break below support, then recover
        if low < support_level * 0.98 and close > support_level and next_close > close:
            return True
    
    return False


def detect_utad(prices: list[dict], resistance_level: float) -> bool:
    """
    Detect UTAD pattern (Upthrust After Distribution).
    - Price spikes above resistance
    - Fails to hold, closes back below
    """
    if len(prices) < 5:
        return False
    
    for i in range(len(prices) - 3):
        high = prices[i].get("high", 0)
        close = prices[i].get("close", 0)
        next_close = prices[i+1].get("close", 0)
        
        # Spike above resistance, then fail
        if high > resistance_level * 1.02 and close < resistance_level and next_close < close:
            return True
    
    return False


def calculate_smi(ticker: str, prices: list[dict], volumes: list[dict]) -> str:
    """
    Calculate Smart Money Index trend.
    Simplified: based on price-volume convergence/divergence.
    
    Returns: "RISING", "FLAT", "FALLING"
    """
    if len(prices) < 10 or len(volumes) < 10:
        return "FLAT"
    
    # Combine price and volume data
    combined = []
    for i, p in enumerate(prices[-10:]):
        if i < len(volumes):
            combined.append({
                "close": p.get("close", 0),
                "volume": volumes[i].get("volume", 0)
            })
    
    if len(combined) < 5:
        return "FLAT"
    
    # SMI heuristic:
    # - Price up + Volume up = Strong SMI (RISING)
    # - Price down + Volume down = Weak SMI (FALLING)
    # - Divergence = FLAT
    
    price_changes = []
    vol_changes = []
    
    for i in range(1, len(combined)):
        price_changes.append(combined[i]["close"] - combined[i-1]["close"])
        vol_changes.append(combined[i]["volume"] - combined[i-1]["volume"])
    
    if not price_changes:
        return "FLAT"
    
    # Count convergent moves
    convergent = 0
    for pc, vc in zip(price_changes, vol_changes):
        if pc > 0 and vc > 0:
            convergent += 1
        elif pc < 0 and vc < 0:
            convergent += 1
    
    ratio = convergent / len(price_changes)
    
    if ratio >= 0.7:
        return "RISING"
    elif ratio <= 0.3:
        return "FALLING"
    return "FLAT"


def analyze_wyckoff(ticker: str, support: float = None, resistance: float = None) -> WyckoffAnalysis:
    """
    Main entry: analyze ticker for Wyckoff phase + SMI.
    """
    prices = get_price_history(ticker, days=30)
    volumes = get_volume_history(ticker, days=30)
    
    if not prices:
        return WyckoffAnalysis(
            ticker=ticker,
            phase="UNKNOWN",
            smi_trend="FLAT",
            structure="RANGE",
            volume_pattern="THIN",
            signals=["Insufficient data"],
            confidence="LOW",
            summary=f"{ticker}: Data tidak cukup untuk analisis Wyckoff."
        )
    
    # Analyze structure
    structure, trend = analyze_structure(prices)
    vol_pattern, vol_health = analyze_volume_pattern(volumes)
    smi_trend = calculate_smi(ticker, prices, volumes)
    
    # Determine phase
    signals = []
    phase = "UNKNOWN"
    confidence = "MEDIUM"
    
    # Find support/resistance if not provided
    if not support or not resistance:
        closes = [p.get("close", 0) for p in prices]
        if closes:
            if not support:
                support = min(closes[-20:]) if len(closes) >= 20 else min(closes)
            if not resistance:
                resistance = max(closes[-20:]) if len(closes) >= 20 else max(closes)
    
    # ACCUMULATION detection
    if trend == "SIDEWAYS" and vol_pattern == "DECLINING":
        if detect_spring(prices, support):
            phase = "ACCUMULATION"
            signals.append("Spring detected (false break below support)")
            confidence = "HIGH"
        else:
            phase = "ACCUMULATION"
            signals.append("Range + declining volume")
        
        if smi_trend == "RISING":
            signals.append("SMI rising (smart money accumulating)")
    
    # MARKUP detection
    elif structure == "HH-HL" and trend == "UP":
        phase = "MARKUP"
        signals.append("Higher highs, higher lows")
        
        if vol_pattern == "HEALTHY":
            signals.append("Volume healthy")
        elif vol_pattern == "SPIKE":
            signals.append("Volume spike (check distribution)")
            confidence = "LOW"
        
        if smi_trend == "RISING":
            signals.append("SMI supporting")
    
    # DISTRIBUTION detection
    elif trend == "SIDEWAYS" and vol_pattern == "SPIKE":
        if detect_utad(prices, resistance):
            phase = "DISTRIBUTION"
            signals.append("UTAD detected (upthrust after distribution)")
            confidence = "HIGH"
        else:
            phase = "DISTRIBUTION"
            signals.append("Range + volume spikes")
        
        if smi_trend == "FALLING":
            signals.append("SMI falling (smart money exiting)")
    
    # MARKDOWN detection
    elif structure == "LH-LL" and trend == "DOWN":
        phase = "MARKDOWN"
        signals.append("Lower highs, lower lows")
        
        if smi_trend == "FALLING":
            signals.append("SMI falling")
        
        confidence = "HIGH"
    
    # Build summary
    phase_emoji = {
        "ACCUMULATION": "📥",
        "MARKUP": "🚀",
        "DISTRIBUTION": "📤",
        "MARKDOWN": "📉",
        "UNKNOWN": "❓"
    }
    
    smi_emoji = {
        "RISING": "🟢",
        "FLAT": "🟡",
        "FALLING": "🔴"
    }
    
    summary = f"{phase_emoji.get(phase, '❓')} {ticker}: **{phase}**\n"
    summary += f"SMI: {smi_emoji.get(smi_trend, '🟡')} {smi_trend} | Structure: {structure}\n"
    summary += f"Volume: {vol_pattern}\n"
    
    if signals:
        summary += "Signals:\n"
        for s in signals:
            summary += f"  • {s}\n"
    
    return WyckoffAnalysis(
        ticker=ticker,
        phase=phase,
        smi_trend=smi_trend,
        structure=structure,
        volume_pattern=vol_pattern,
        signals=signals,
        confidence=confidence,
        summary=summary
    )


def format_wyckoff(w: WyckoffAnalysis) -> str:
    """Format for output."""
    return w.summary


# Quick test
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "ESSA"
    result = analyze_wyckoff(ticker)
    print(format_wyckoff(result))
