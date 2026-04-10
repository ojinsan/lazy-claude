"""
Macro — Market Regime & Sector Rotation
=========================================
Layer 1 skill: What's the environment? What story should we play?

Before looking at ANY stock:
1. Market regime: risk-on or risk-off?
2. Foreign flow: buying or selling?
3. Sector rotation: which sector is hot and why?
4. Active theses: what stories are we playing?

Multiple theses can run in parallel.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from . import api

log = logging.getLogger(__name__)
WIB = ZoneInfo("Asia/Jakarta")

DATA_DIR = Path("/home/lazywork/lazyboy/trade/data")
REGIME_FILE = DATA_DIR / "regime.json"
THESIS_FILE = DATA_DIR / "sector_thesis.json"


# ─── Sector Definitions ──────────────────────────────────────────────────────

SECTORS = {
    "COAL": ["ADRO", "PTBA", "ITMG", "HRUM", "BSSR", "MYOH", "ABMM", "KKGI", 
             "GEMS", "COAL", "INDY", "TOBA"],
    "NICKEL": ["MBMA", "NICL", "NICE", "NCKL", "INCO", "DKFT", "MDKA", "ANTM"],
    "MINING_SERVICES": ["ADMR", "PSAB", "ARCO", "PTRO", "MEDC", "ENRG"],
    "OIL_GAS": ["MEDC", "ENRG", "RAJA", "ESSA", "ELSA", "AKRA"],
    "BANK": ["BBCA", "BBRI", "BMRI", "BBNI", "BNGA", "PNBN", "BDMN", "BBYB"],
    "PROPERTY": ["BSDE", "CTRA", "PWON", "LAND", "KOTA", "PPGL", "CBDK"],
    "TELECOM": ["TLKM", "EXCL", "ISAT", "TOWR", "WIFI", "INET"],
    "SHIPPING": ["BULL", "SMDR", "TMAS", "RIGS", "HITS", "WINS"],
    "CPO_AGRI": ["DSNG", "TAPG", "AALI", "LSIP", "SSMS", "SGRO"],
    "POULTRY": ["CPIN", "JPFA", "MAIN"],
    "CHEMICAL": ["TPIA", "BRPT", "CGAS"],
    "CONSUMER": ["INDF", "ICBP", "UNVR", "MYOR", "ULTJ"],
    "AUTO": ["ASII", "AUTO", "IMAS", "DRMA"],
    "TECH": ["GOTO", "BUKA", "EMTK", "DCII"],
    "ENERGY": ["VKTR", "BIPI", "BUMI"],
}

# Reverse lookup: ticker → sector
TICKER_SECTOR = {}
for sector, tickers in SECTORS.items():
    for t in tickers:
        TICKER_SECTOR[t] = sector


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class MarketRegime:
    """Current market environment assessment."""
    label: str = "UNKNOWN"          # BULL / SIDEWAYS / BEAR
    confidence: str = "LOW"         # HIGH / MEDIUM / LOW
    risk_multiplier: float = 1.0    # applied to position sizing
    notes: str = ""
    timestamp: str = ""
    
    # Components
    trend_distribution: dict = field(default_factory=dict)  # {up: N, down: N, sideways: N}
    foreign_flow: str = ""          # "net_buy" / "net_sell" / "neutral"


@dataclass
class SectorThesis:
    """A sector-level investment thesis."""
    sector: str
    narrative: str                  # WHY this sector
    conviction: str = "MEDIUM"      # HIGH / MEDIUM / LOW
    catalysts: list[str] = field(default_factory=list)
    tickers_of_interest: list[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    status: str = "active"          # active / paused / closed


# ─── Market Regime ────────────────────────────────────────────────────────────

# Blue chips to sample for regime detection
REGIME_SAMPLE = [
    "BBCA", "BBRI", "BMRI", "TLKM", "ASII", "ADRO", 
    "AMMN", "GOTO", "BREN", "TPIA", "INDF", "ICBP",
    "ANTM", "MDKA", "PGAS",
]


def _analyze_trend_label(trend_data: dict) -> str:
    """Analyze trend data into simple label."""
    trend_list = trend_data.get("trend", [])
    if not trend_list:
        return "UNKNOWN"
    
    recent = trend_list[-20:]
    hh = sum(1 for t in recent if t[0] == "HH")
    ll = sum(1 for t in recent if t[0] == "LL")
    hl = sum(1 for t in recent if t[0] == "HL")
    lh = sum(1 for t in recent if t[0] == "LH")
    
    last5 = [t[0] for t in trend_list[-5:]]
    
    if hh > ll + lh and "HH" in last5:
        return "UPTREND"
    elif ll > hh + hl and "LL" in last5:
        return "DOWNTREND"
    elif lh >= 2 and ll >= 2:
        return "DOWNTREND"
    return "SIDEWAYS"


def assess_regime() -> MarketRegime:
    """
    Assess current market regime.

    Priority:
    1) Index feed (IDX/IHSG) when available
    2) Blue-chip proxy basket when index feed unavailable

    This is Layer 1 — before looking at any specific stock.
    """
    now = datetime.now(WIB)
    regime = MarketRegime(timestamp=now.strftime("%Y-%m-%d %H:%M"))
    
    # 1) Try direct Stockbit index feed first (Waterseven principle)
    ihsg = api.get_stockbit_index("IHSG")
    if ihsg and not ihsg.get("error") and ihsg.get("lastprice"):
        pct = float(ihsg.get("percentage_change", 0))
        fnet = float(ihsg.get("fnet", 0))
        freq = int(ihsg.get("frequency", 0) or 0)

        if pct <= -1.0:
            regime.label = "BEAR"
            regime.risk_multiplier = 0.65
            regime.confidence = "HIGH" if pct <= -2.0 else "MEDIUM"
        elif pct >= 1.0:
            regime.label = "BULL"
            regime.risk_multiplier = 1.15
            regime.confidence = "HIGH" if pct >= 2.0 else "MEDIUM"
        elif pct <= -0.3:
            regime.label = "SIDEWAYS_BEARISH"
            regime.risk_multiplier = 0.85
            regime.confidence = "MEDIUM"
        else:
            regime.label = "SIDEWAYS"
            regime.risk_multiplier = 0.95
            regime.confidence = "MEDIUM"

        ff = "net sell" if fnet < 0 else ("net buy" if fnet > 0 else "flat")
        regime.foreign_flow = ff
        regime.notes = (
            f"IHSG {ihsg.get('lastprice')} ({pct:+.2f}%), foreign {ff} "
            f"({fnet:,.0f}), freq {freq:,} [Stockbit direct]"
        )

        _save_regime(regime)
        return regime

    # 2) Fallback: blue-chip proxy basket when index feed unavailable
    up = 0
    down = 0
    sideways = 0

    for ticker in REGIME_SAMPLE:
        trend_data = api.get_trend(ticker)
        label = _analyze_trend_label(trend_data)
        if label == "UPTREND":
            up += 1
        elif label == "DOWNTREND":
            down += 1
        else:
            sideways += 1

    total = len(REGIME_SAMPLE)
    regime.trend_distribution = {"up": up, "down": down, "sideways": sideways}

    up_pct = up / total
    down_pct = down / total

    if down_pct >= 0.6:
        regime.label = "PROXY_BEAR"
        regime.confidence = "HIGH" if down_pct >= 0.75 else "MEDIUM"
        regime.risk_multiplier = 0.65
    elif down_pct >= 0.4:
        regime.label = "PROXY_SIDEWAYS_BEARISH"
        regime.confidence = "MEDIUM"
        regime.risk_multiplier = 0.80
    elif up_pct >= 0.6:
        regime.label = "PROXY_BULL"
        regime.confidence = "HIGH" if up_pct >= 0.75 else "MEDIUM"
        regime.risk_multiplier = 1.15
    else:
        regime.label = "PROXY_SIDEWAYS"
        regime.confidence = "MEDIUM"
        regime.risk_multiplier = 0.90

    regime.notes = (
        f"{up} up / {down} down / {sideways} sideways from {total} blue chips "
        f"(INDEX FEED UNAVAILABLE, proxy mode)"
    )

    _save_regime(regime)
    return regime


def _save_regime(regime: MarketRegime):
    """Save regime assessment."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "label": regime.label,
        "confidence": regime.confidence,
        "risk_multiplier": regime.risk_multiplier,
        "notes": regime.notes,
        "timestamp": regime.timestamp,
        "trend_distribution": regime.trend_distribution,
    }
    REGIME_FILE.write_text(json.dumps(data, indent=2))


def get_last_regime() -> Optional[MarketRegime]:
    """Load last saved regime."""
    if not REGIME_FILE.exists():
        return None
    try:
        data = json.loads(REGIME_FILE.read_text())
        return MarketRegime(**{k: v for k, v in data.items() if k != "trend_distribution"},
                           trend_distribution=data.get("trend_distribution", {}))
    except:
        return None


# ─── Sector Rotation ─────────────────────────────────────────────────────────

def detect_sector_rotation(sectors_to_check: list[str] = None) -> dict[str, dict]:
    """
    Detect which sectors are showing momentum.
    
    For each sector, samples a few tickers and checks:
    - How many are in uptrend?
    - Average volume ratio (activity level)
    
    Returns: {sector: {momentum, volume_activity, tickers_up, ...}}
    """
    if sectors_to_check is None:
        sectors_to_check = list(SECTORS.keys())
    
    results = {}
    
    for sector in sectors_to_check:
        tickers = SECTORS.get(sector, [])
        if not tickers:
            continue
        
        # Sample up to 5 tickers per sector
        sample = tickers[:5]
        up = 0
        total_vol_ratio = 0.0
        checked = 0
        
        for ticker in sample:
            trend_data = api.get_trend(ticker)
            label = _analyze_trend_label(trend_data)
            if label == "UPTREND":
                up += 1
            
            vol_ratio = api.get_volume_ratio(ticker)
            total_vol_ratio += vol_ratio
            checked += 1
        
        if checked == 0:
            continue
        
        momentum = up / checked
        avg_vol = total_vol_ratio / checked
        
        results[sector] = {
            "momentum": round(momentum, 2),      # 0-1, higher = more stocks trending up
            "avg_volume_ratio": round(avg_vol, 2),
            "tickers_up": up,
            "tickers_checked": checked,
            "hot": momentum >= 0.6 and avg_vol >= 1.0,
        }
    
    return results


# ─── Sector Thesis Management ────────────────────────────────────────────────

def get_active_theses() -> list[SectorThesis]:
    """Load active sector theses."""
    if not THESIS_FILE.exists():
        return []
    try:
        data = json.loads(THESIS_FILE.read_text())
        return [SectorThesis(**t) for t in data if t.get("status") == "active"]
    except:
        return []


def save_thesis(thesis: SectorThesis):
    """Save or update a sector thesis."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    theses = []
    if THESIS_FILE.exists():
        try:
            theses = json.loads(THESIS_FILE.read_text())
        except:
            theses = []
    
    now = datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
    
    # Update existing or add new
    found = False
    for i, t in enumerate(theses):
        if t["sector"] == thesis.sector:
            theses[i] = {
                "sector": thesis.sector,
                "narrative": thesis.narrative,
                "conviction": thesis.conviction,
                "catalysts": thesis.catalysts,
                "tickers_of_interest": thesis.tickers_of_interest,
                "created": t.get("created", now),
                "updated": now,
                "status": thesis.status,
            }
            found = True
            break
    
    if not found:
        theses.append({
            "sector": thesis.sector,
            "narrative": thesis.narrative,
            "conviction": thesis.conviction,
            "catalysts": thesis.catalysts,
            "tickers_of_interest": thesis.tickers_of_interest,
            "created": now,
            "updated": now,
            "status": thesis.status,
        })
    
    THESIS_FILE.write_text(json.dumps(theses, indent=2, ensure_ascii=False))


def close_thesis(sector: str, reason: str = ""):
    """Close/deactivate a sector thesis."""
    if not THESIS_FILE.exists():
        return
    theses = json.loads(THESIS_FILE.read_text())
    for t in theses:
        if t["sector"] == sector:
            t["status"] = "closed"
            t["close_reason"] = reason
            t["updated"] = datetime.now(WIB).strftime("%Y-%m-%d %H:%M")
    THESIS_FILE.write_text(json.dumps(theses, indent=2, ensure_ascii=False))


def get_sector(ticker: str) -> str:
    """Get sector for a ticker."""
    return TICKER_SECTOR.get(ticker, "UNKNOWN")


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_regime(r: MarketRegime) -> str:
    """Format regime for display."""
    emoji = {
        "BULL": "🟢", "SIDEWAYS": "🟡", "SIDEWAYS_BEARISH": "🟠", "BEAR": "🔴",
        "PROXY_BULL": "🟢", "PROXY_SIDEWAYS": "🟡", "PROXY_SIDEWAYS_BEARISH": "🟠", "PROXY_BEAR": "🔴",
    }.get(r.label, "⚪")
    
    lines = []
    lines.append(f"📊 Market Regime — {r.timestamp}")
    lines.append(f"  {emoji} {r.label} ({r.confidence} confidence)")
    lines.append(f"  {r.notes}")
    lines.append(f"  Risk multiplier: {r.risk_multiplier}x")
    return "\n".join(lines)


def format_sector_rotation(rotation: dict) -> str:
    """Format sector rotation for display."""
    lines = []
    lines.append("🔄 Sector Rotation")
    
    # Sort by momentum
    sorted_sectors = sorted(rotation.items(), key=lambda x: x[1]["momentum"], reverse=True)
    
    for sector, data in sorted_sectors:
        if data["hot"]:
            lines.append(f"  🔥 {sector}: {data['tickers_up']}/{data['tickers_checked']} up, vol {data['avg_volume_ratio']:.1f}x")
        elif data["momentum"] >= 0.4:
            lines.append(f"  🟡 {sector}: {data['tickers_up']}/{data['tickers_checked']} up, vol {data['avg_volume_ratio']:.1f}x")
        else:
            lines.append(f"  ⬜ {sector}: {data['tickers_up']}/{data['tickers_checked']} up, vol {data['avg_volume_ratio']:.1f}x")
    
    return "\n".join(lines)
