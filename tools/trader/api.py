"""
Lazyboy Shared API Layer
========================
Follows Waterseven architecture:
- Token priority: Backend API /token-store/stockbit → local cache
- Stockbit direct: index/regime, realtime needs
- Backend API: cached stock data, broker analysis, RAG

Learned from: ~/bitstock/waterseven/skills/stockbit_client.py
"""

import httpx
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

log = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

# Backend API (cached data from scraper)
from config import load_env, backend_url, backend_token, stockbit_token_cache, ORDERBOOK_STATE_DIR
load_env()
BACKEND_BASE_URL = backend_url()
BACKEND_API_TOKEN = backend_token()
BACKEND_HEADERS = {"Authorization": f"Bearer {BACKEND_API_TOKEN}"} if BACKEND_API_TOKEN else {}

# Stockbit direct API (realtime, index feed)
STOCKBIT_BASE_URL = "https://exodus.stockbit.com"

# Token is fetched exclusively from backend API (/token-store/stockbit)

TIMEOUT = 15

from stockbit_headers import STOCKBIT_BROWSER_HEADERS, stockbit_headers
from tick_walls import analyze_tick_walls

# Smart money / retail classification (from SYSTEM.md)
SMART_MONEY = {"RF", "SS", "HP", "YU", "AI", "ES", "HD", "AK", "ZP", "BP",
               "BK", "MS", "CS", "DB", "MG", "RX"}
FOREIGN = {"BK", "MS", "CS", "DB", "MG", "RX", "YU", "CG", "ML"}
RETAIL = {"XL", "XC", "YP", "CC", "KK", "PD", "SQ", "NI", "AZ", "CP"}
PRAJOGO = {"DP", "LG", "NI"}


def classify_broker(code: str) -> str:
    """Classify broker code into category."""
    code = code.upper().strip()
    if code in SMART_MONEY:
        return "smart_money"
    if code in FOREIGN:
        return "foreign"
    if code in RETAIL:
        return "retail"
    if code in PRAJOGO:
        return "prajogo_group"
    return "unknown"


# ─── Stockbit Portfolio API (Carina) ──────────────────────────────────────────

CARINA_BASE_URL = "https://carina.stockbit.com"
CARINA_TOKEN_CACHE = Path(stockbit_token_cache().parent / "carina_token.json")


def _load_carina_token() -> Optional[str]:
    """Load Carina (portfolio) Bearer token from cache."""
    if CARINA_TOKEN_CACHE.exists():
        try:
            data = json.loads(CARINA_TOKEN_CACHE.read_text())
            token = data.get("token", "")
            exp = data.get("expires_at", 0)
            if token and (exp == 0 or exp > time.time()):
                return token
        except Exception:
            pass
    return None


def save_carina_token(token: str, expires_at: int = 0):
    """Save Carina Bearer token to cache.
    
    Usage: save_carina_token("eyJ...", expires_at=1773052731)
    """
    CARINA_TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CARINA_TOKEN_CACHE.write_text(json.dumps({
        "token": token,
        "expires_at": expires_at,
        "saved_at": int(time.time()),
    }))
    log.info("Carina token saved")


def get_portfolio() -> dict:
    """Fetch portfolio from Stockbit Carina API.
    
    Token priority:
    1. Backend API token (get_stockbit_token) — auto-refreshed
    2. Carina-specific token (carina_token.json) — manual, v2 with account info
    
    Returns dict with keys:
      - summary: {cash, invested, equity, unrealised_pl, gain_pct}
      - positions: [{symbol, lots, shares, avg_price, latest_price, market_value, pl, gain_pct}]
    """
    # Try tokens in priority order
    tokens_to_try = []
    
    # 1. Carina-specific v2 token (most likely to work for portfolio)
    carina_token = _load_carina_token()
    if carina_token:
        tokens_to_try.append(("carina_v2", carina_token))
    
    # 2. Backend API token (v1, may or may not work for Carina)
    try:
        backend_token = get_stockbit_token()
        if backend_token:
            tokens_to_try.append(("backend_v1", backend_token))
    except Exception:
        pass
    
    if not tokens_to_try:
        raise RuntimeError("No Stockbit token available. Ask Mr O for Bearer token → save_carina_token()")
    
    last_error = None
    for token_name, token in tokens_to_try:
        r = httpx.get(
            f"{CARINA_BASE_URL}/portfolio/v2/list",
            headers={
                **STOCKBIT_BROWSER_HEADERS,
                "authorization": f"Bearer {token}",
                "origin": "https://stockbit.com",
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            log.info(f"Portfolio fetched with {token_name}")
            break
        last_error = f"{token_name}: {r.status_code} {r.text[:100]}"
        log.warning(f"Portfolio {last_error}")
    else:
        raise RuntimeError(f"All tokens failed for Carina portfolio. Last: {last_error}. Ask Mr O for new v2 Bearer token → save_carina_token()") 
    data = r.json().get("data", {})
    
    summary_raw = data.get("summary", {})
    results_raw = data.get("results", [])
    
    summary = {
        "cash": summary_raw.get("trading", {}).get("balance", 0),
        "invested": summary_raw.get("amount", {}).get("invested", 0),
        "allocated": summary_raw.get("amount", {}).get("allocated", 0),
        "equity": summary_raw.get("equity", 0),
        "unrealised_pl": summary_raw.get("profit_loss", {}).get("unrealised", 0),
        "realised_pl": summary_raw.get("profit_loss", {}).get("realised", 0),
        "gain_pct": summary_raw.get("gain", 0) * 100,
    }
    
    positions = []
    for r in results_raw:
        qty = r.get("qty", {})
        price = r.get("price", {})
        asset = r.get("asset", {}).get("unrealised", {})
        shares = qty.get("available", {}).get("share", 0)
        if shares <= 0:
            continue
        positions.append({
            "symbol": r.get("symbol", ""),
            "lots": int(shares / 100) if shares >= 100 else shares / 100,
            "shares": shares,
            "avg_price": price.get("average", {}).get("fee", 0),
            "latest_price": price.get("latest", 0),
            "market_value": asset.get("market_value", 0),
            "pl": asset.get("profit_loss", 0),
            "gain_pct": asset.get("gain", 0) * 100,
        })
    
    return {"summary": summary, "positions": positions}


def format_portfolio(portfolio: dict) -> str:
    """Format portfolio dict into readable string."""
    s = portfolio["summary"]
    lines = [
        f"💼 Portfolio Summary",
        f"Cash: Rp {s['cash']:,.0f}",
        f"Invested: Rp {s['invested']:,.0f}",
        f"Equity: Rp {s['equity']:,.0f}",
        f"Unrealised P/L: Rp {s['unrealised_pl']:,.0f} ({s['gain_pct']:+.2f}%)",
        "",
        "Positions:",
    ]
    for p in portfolio["positions"]:
        emoji = "📈" if p["pl"] >= 0 else "📉"
        lines.append(
            f"  {emoji} {p['symbol']} — {p['lots']} lot | "
            f"Avg: {p['avg_price']:.0f} | Now: {p['latest_price']} | "
            f"P/L: Rp {p['pl']:,.0f} ({p['gain_pct']:+.1f}%)"
        )
    return "\n".join(lines)


# ─── Token Management (Waterseven style) ──────────────────────────────────────

_stockbit_token: Optional[str] = None
_stockbit_token_expires_at: int = 0


def _extract_token(data: dict) -> Optional[str]:
    """Extract token from various payload structures."""
    if not isinstance(data, dict):
        return None
    # Direct fields
    for k in ("token", "access_token", "login_access_token", "jwt"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def get_stockbit_token() -> Optional[str]:
    """
    Get Stockbit bearer token from backend API (sole source of truth).
    Token is managed and refreshed by the backend — no local fallbacks.
    """
    global _stockbit_token, _stockbit_token_expires_at

    # Use cached token if still valid (5 min buffer)
    now_ms = int(time.time() * 1000)
    if _stockbit_token and (_stockbit_token_expires_at == 0 or now_ms < _stockbit_token_expires_at - 300000):
        return _stockbit_token

    try:
        r = httpx.get(
            f"{BACKEND_BASE_URL}/token-store/stockbit",
            headers=BACKEND_HEADERS,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            token = _extract_token(data)
            if token:
                _stockbit_token = token
                _stockbit_token_expires_at = data.get("expires_at", 0)
                return token
    except Exception as e:
        log.debug(f"Token fetch failed: {e}")

    log.warning("No Stockbit token available from backend")
    return None


# ─── HTTP Helpers ─────────────────────────────────────────────────────────────

def _backend_get(path: str, params: Optional[dict] = None) -> dict:
    """GET request to backend API."""
    try:
        r = httpx.get(f"{BACKEND_BASE_URL}{path}", headers=BACKEND_HEADERS, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Backend GET {path} failed: {e}")
        return {"error": str(e)}


def _backend_post(path: str, data: dict) -> dict:
    """POST request to backend API."""
    try:
        r = httpx.post(f"{BACKEND_BASE_URL}{path}", headers=BACKEND_HEADERS, json=data, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Backend POST {path} failed: {e}")
        return {"error": str(e)}


def _stockbit_get(path: str, params: Optional[dict] = None) -> dict:
    """GET request to Stockbit direct API with auto-refresh on 401."""
    token = get_stockbit_token()
    if not token:
        return {"error": "No Stockbit token"}

    try:
        r = httpx.get(
            f"{STOCKBIT_BASE_URL}{path}",
            headers=stockbit_headers(token),
            params=params,
            timeout=TIMEOUT,
        )

        if r.status_code == 401:
            log.warning(f"401 on {path} — token expired or invalid. Backend needs to refresh it.")
            return {"error": "401 Unauthorized — token needs backend refresh"}

        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Stockbit GET {path} failed: {e}")
        return {"error": str(e)}


def _stockbit_post(path: str, data: dict) -> dict:
    """POST request to Stockbit direct API (exodus)."""
    token = get_stockbit_token()
    if not token:
        return {"error": "No Stockbit token"}
    try:
        r = httpx.post(
            f"{STOCKBIT_BASE_URL}{path}",
            headers=stockbit_headers(token),
            json=data,
            timeout=TIMEOUT,
        )
        if r.status_code == 401:
            return {"error": "401 Unauthorized — token needs backend refresh"}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Stockbit POST {path} failed: {e}")
        return {"error": str(e)}


def _carina_get(path: str, params: Optional[dict] = None) -> dict:
    """GET request to Carina (broker/portfolio) API."""
    token = _load_carina_token()
    if not token:
        # fallback to stockbit token
        token = get_stockbit_token()
    if not token:
        return {"error": "No Carina token. Use save_carina_token() to store it."}
    try:
        r = httpx.get(
            f"{CARINA_BASE_URL}{path}",
            headers={**STOCKBIT_BROWSER_HEADERS, "authorization": f"Bearer {token}", "origin": "https://stockbit.com"},
            params=params,
            timeout=TIMEOUT,
        )
        if r.status_code == 401:
            return {"error": "401 Unauthorized — Carina token expired. Use save_carina_token()."}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Carina GET {path} failed: {e}")
        return {"error": str(e)}


def _carina_post(path: str, data: dict) -> dict:
    """POST request to Carina (broker/portfolio) API."""
    token = _load_carina_token()
    if not token:
        token = get_stockbit_token()
    if not token:
        return {"error": "No Carina token. Use save_carina_token() to store it."}
    try:
        r = httpx.post(
            f"{CARINA_BASE_URL}{path}",
            headers={**STOCKBIT_BROWSER_HEADERS, "authorization": f"Bearer {token}", "origin": "https://stockbit.com"},
            json=data,
            timeout=TIMEOUT,
        )
        if r.status_code == 401:
            return {"error": "401 Unauthorized — Carina token expired. Use save_carina_token()."}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Carina POST {path} failed: {e}")
        return {"error": str(e)}


def _carina_delete(path: str) -> dict:
    """DELETE request to Carina API."""
    token = _load_carina_token()
    if not token:
        token = get_stockbit_token()
    if not token:
        return {"error": "No Carina token."}
    try:
        r = httpx.delete(
            f"{CARINA_BASE_URL}{path}",
            headers={**STOCKBIT_BROWSER_HEADERS, "authorization": f"Bearer {token}", "origin": "https://stockbit.com"},
            timeout=TIMEOUT,
        )
        if r.status_code == 401:
            return {"error": "401 Unauthorized — Carina token expired."}
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Carina DELETE {path} failed: {e}")
        return {"error": str(e)}


# ─── Stockbit Direct API ──────────────────────────────────────────────────────

def get_stockbit_index(symbol: str = "IHSG") -> dict:
    """
    Get index snapshot from Stockbit orderbook feed.
    
    Endpoint: /company-price-feed/v2/orderbook/companies/{symbol}
    Returns: lastprice, change, percentage_change, foreign flow, etc.
    """
    data = _stockbit_get(f"/company-price-feed/v2/orderbook/companies/{symbol.upper()}")
    if "error" in data:
        return data
    return _normalize_change_percent(data.get("data", {}))


def _normalize_change_percent(payload: dict) -> dict:
    """Backfill change_percent when Stockbit omits it in orderbook payloads."""
    if not isinstance(payload, dict):
        return payload
    if payload.get("change_percent") is not None:
        return payload
    try:
        if payload.get("percentage_change") is not None:
            payload["change_percent"] = payload.get("percentage_change")
            return payload
        last_price = float(payload.get("lastprice") or 0)
        prev_close = float(payload.get("close") or payload.get("previous") or 0)
        if last_price and prev_close:
            payload["change_percent"] = round(((last_price - prev_close) / prev_close) * 100, 2)
    except Exception:
        pass
    return payload


def get_stockbit_orderbook(symbol: str) -> dict:
    """Get orderbook from Stockbit direct."""
    data = _stockbit_get(f"/company-price-feed/v2/orderbook/companies/{symbol.upper()}")
    if "error" in data:
        return data
    return _normalize_change_percent(data.get("data", {}))


def get_stockbit_chart(symbol: str, timeframe: str = "1m") -> dict:
    """
    Get chart data from Stockbit.
    
    Timeframe: today, 1w, 1m, 3m, 1y
    """
    tf_map = {"1d": "today", "7d": "1w"}
    tf = tf_map.get(timeframe.lower(), timeframe.lower())
    
    data = _stockbit_get(
        f"/charts/{symbol.upper()}/daily",
        {"timeframe": tf, "chart_type": "PRICE_CHART_TYPE_CANDLE"},
    )
    if "error" in data:
        return data
    return data.get("data", {})


def get_stockbit_running_trade(
    symbol: str,
    mode: str = "realtime",
    limit: int = 50,
    date: Optional[str] = None,
    market_board: str = "ALL",
) -> dict:
    """
    Get running trades from Stockbit direct.
    
    IMPORTANT: Broker codes only visible when market CLOSED.
    
    Args:
        symbol: Stock ticker
        mode: "realtime" (by time) or "recap" (by lot size)
        limit: Number of trades
        date: Optional date filter (YYYY-MM-DD)
        market_board: "ALL", "RG" (Regular), "NG" (Negotiated)
    """
    order_by = "RUNNING_TRADE_ORDER_BY_TIME" if mode == "realtime" else "RUNNING_TRADE_ORDER_BY_LOT"
    params = {
        "symbols[]": symbol.upper(),
        "order_by": order_by,
        "limit": str(limit),
        "sort": "DESC",
    }
    if date:
        params["date"] = date
    if market_board != "ALL":
        params["market_board"] = f"MARKET_BOARD_{market_board}"
    
    data = _stockbit_get("/order-trade/running-trade", params)
    if "error" in data:
        return data
    
    result = data.get("data", {})
    
    # Separate regular vs negotiated
    if market_board == "ALL" and "running_trade" in result:
        regular = [t for t in result["running_trade"] if t.get("market_board") == "RG"]
        negotiated = [t for t in result["running_trade"] if t.get("market_board") in ("NG", "TN")]
        result["regular_trades"] = regular
        result["negotiated_trades"] = negotiated
        result["summary"] = {
            "total_trades": len(result["running_trade"]),
            "regular_count": len(regular),
            "negotiated_count": len(negotiated),
        }
    
    return result


def get_stockbit_broker_info(symbol: str, scope: str = "L10D") -> dict:
    """
    Get broker info / market detector from Stockbit.
    
    Returns: broker_summary (buy/sell), bandar_detector
    """
    data = _stockbit_get(f"/marketdetectors/{symbol.upper()}", {"scope": scope})
    if "error" in data:
        return data
    return data.get("data", {})


def get_stockbit_broker_distribution(symbol: str, date: Optional[str] = None) -> dict:
    """
    Get broker distribution (who bought from whom, who sold to whom).
    
    Args:
        symbol: Stock ticker
        date: Optional date (YYYY-MM-DD). If None, uses latest trading day.
    """
    params = {"symbol": symbol.upper(), "company_code": symbol.upper()}
    if date:
        params["date"] = date
    
    data = _stockbit_get("/order-trade/broker/distribution", params)
    if "error" in data:
        return data
    return data.get("data", {})


def get_stockbit_broker_movement(
    symbol: str,
    period: str = "1w",
    broker_codes: Optional[list[str]] = None,
) -> dict:
    """
    Get broker position history over time.
    
    Args:
        symbol: Stock ticker
        period: 1d, 1w, 1m, 3m, 1y
        broker_codes: Optional list of broker codes to filter
    """
    period_map = {
        "1d": "RT_PERIOD_LAST_1_DAY",
        "1w": "RT_PERIOD_LAST_7_DAYS",
        "1m": "RT_PERIOD_LAST_1_MONTH",
        "3m": "RT_PERIOD_LAST_3_MONTHS",
        "1y": "RT_PERIOD_LAST_1_YEAR",
    }
    api_period = period_map.get(period, period_map["1w"])
    
    params = {"period": api_period}
    if broker_codes:
        params["broker_code"] = broker_codes
    
    data = _stockbit_get(f"/order-trade/running-trade/chart/{symbol.upper()}", params)
    if "error" in data:
        return data
    return data.get("data", {})


def get_stockbit_sid_count(symbol: str) -> dict:
    """
    Get SID (Shareholder ID) count from Stockbit ems profile.
    
    Returns: current_sid, previous_sid, change, change_pct, signal, history
    """
    data = _stockbit_get(f"/emitten/{symbol.upper()}/profile")
    if "error" in data:
        return data
    
    profile = data.get("data", {})
    numbers = profile.get("shareholder_numbers", [])
    
    if not numbers or not isinstance(numbers, list):
        return {"error": "No SID data", "symbol": symbol}
    
    history = []
    for item in numbers:
        if not isinstance(item, dict):
            continue
        total_share = item.get("total_share", 0)
        if isinstance(total_share, str):
            total_share = int("".join(c for c in total_share if c.isdigit()) or 0)
        if total_share > 0:
            history.append({
                "date": item.get("date", ""),
                "total_share": total_share,
            })
    
    if len(history) < 2:
        return {"error": "Insufficient SID history", "symbol": symbol, "history": history}
    
    current_sid = history[0]["total_share"]
    previous_sid = history[1]["total_share"]
    change = current_sid - previous_sid
    change_pct = (change / previous_sid * 100) if previous_sid > 0 else 0
    
    if change_pct <= -5:
        signal = "strong_accumulation"
    elif change_pct < -1:
        signal = "accumulation"
    elif change_pct >= 5:
        signal = "strong_distribution"
    elif change_pct > 1:
        signal = "distribution"
    else:
        signal = "neutral"
    
    return {
        "symbol": symbol,
        "current_sid": current_sid,
        "previous_sid": previous_sid,
        "change": change,
        "change_pct": round(change_pct, 2),
        "signal": signal,
        "history": history,
    }


# ─── Stockbit Direct: Emitten Info ───────────────────────────────────────────

def get_emitten_info(symbol: str) -> dict:
    """
    Get company info from Stockbit (price, change, avg volume, exchange, sector).

    Endpoint: GET exodus.stockbit.com/emitten/{symbol}/info
    Returns: average, change, date, exchange, last_price, market_cap, etc.
    """
    data = _stockbit_get(f"/emitten/{symbol.upper()}/info")
    if "error" in data:
        return data
    return data.get("data", data)


# ─── Stockbit Direct: Watchlist ───────────────────────────────────────────────

def get_stockbit_watchlists(category_types: Optional[list[str]] = None, page: int = 1, limit: int = 50) -> list[dict]:
    """
    List user's Stockbit watchlists.

    Endpoint: GET exodus.stockbit.com/watchlist
    Returns: list of {watchlist_id, name, description, total_items, ...}
    """
    params: dict = {"page": page, "limit": limit}
    if category_types:
        params["category_types"] = category_types
    data = _stockbit_get("/watchlist", params)
    if "error" in data:
        return []
    return data.get("data", [])


def get_stockbit_watchlist(watchlist_id: int, page: int = 1, limit: int = 50) -> dict:
    """
    Get items in a Stockbit watchlist.

    Endpoint: GET exodus.stockbit.com/watchlist/{watchlist_id}
    Returns: {watchlist_id, header, items: [{symbol, last, change, percent, ...}]}

    Args:
        watchlist_id: Watchlist ID (e.g. 888864)
        setfincol: Financial columns to include (default: 1)
    """
    data = _stockbit_get(f"/watchlist/{watchlist_id}", {"page": page, "limit": limit, "setfincol": 1})
    if "error" in data:
        return data
    return data.get("data", data)


def get_stockbit_watchlist_metrics() -> list[dict]:
    """
    Get available financial metrics for watchlist columns.

    Endpoint: GET exodus.stockbit.com/watchlist/metric
    """
    data = _stockbit_get("/watchlist/metric")
    if "error" in data:
        return []
    return data.get("data", [])


# ─── Stockbit Direct: Screener ────────────────────────────────────────────────

def get_screener_templates() -> list[dict]:
    """
    List all screener templates (custom + favorites).

    Endpoint: GET exodus.stockbit.com/screener/templates
    Returns: [{id, name, type, favorite}, ...]
    """
    data = _stockbit_get("/screener/templates")
    if "error" in data:
        return []
    return data.get("data", [])


def get_screener_presets() -> list[dict]:
    """
    Get preset screener categories (Guru Screener, Value, Growth, etc.).

    Endpoint: GET exodus.stockbit.com/screener/preset
    Returns: [{id, name, childs: [{id, name, childs: [...]}]}]
    """
    data = _stockbit_get("/screener/preset")
    if "error" in data:
        return []
    return data.get("data", [])


def get_screener_metrics() -> list[dict]:
    """
    Get all available screening metrics/filters.

    Endpoint: GET exodus.stockbit.com/screener/metric
    Returns: [{fitem_id, fitem_name, child: [{fitem_id, fitem_name, ...}]}]
    """
    data = _stockbit_get("/screener/metric")
    if "error" in data:
        return []
    return data.get("data", [])


def get_screener_universe() -> dict:
    """
    Get available stock universes for screener (IHSG, IDX30, LQ45, sectors, etc.).

    Endpoint: GET exodus.stockbit.com/screener/universe
    Returns: {index: [{id, name, scope, list: [...]}], sector: [...]}
    """
    data = _stockbit_get("/screener/universe")
    if "error" in data:
        return {}
    return data.get("data", data)


def run_screener_template(template_id: int, result_type: str = "TEMPLATE_TYPE_CUSTOM") -> list[dict]:
    """
    Run a preset or saved screener template.

    Endpoint: GET exodus.stockbit.com/screener/templates/{template_id}?type=...
    Returns: list of matching companies with their metric values.

    Args:
        template_id: Template ID (get from get_screener_templates() or get_screener_presets())
        result_type: "TEMPLATE_TYPE_CUSTOM" or "TEMPLATE_TYPE_GURU"
    """
    data = _stockbit_get(f"/screener/templates/{template_id}", {"type": result_type})
    if "error" in data:
        return []
    inner = data.get("data", {})
    return inner.get("calcs", inner) if isinstance(inner, dict) else inner


def run_screener_custom(
    filters: list[dict],
    universe: Optional[dict] = None,
    page: int = 1,
    ordercol: int = 2,
    ordertype: str = "desc",
    name: str = "",
    save: bool = False,
) -> list[dict]:
    """
    Run a custom screener with arbitrary filters.

    Endpoint: POST exodus.stockbit.com/screener/templates

    Args:
        filters: List of filter rules. Each rule:
            {"type": "between"|"gt"|"lt"|"eq",
             "item1": <fitem_id>,    # metric ID from get_screener_metrics()
             "item2": <value_or_fitem_id>,
             "item3": <upper_bound>  # only for "between"}
        universe: {scope, scopeID, name} — default: all IHSG stocks.
                  Get valid values from get_screener_universe().
        page: Result page number
        ordercol: Column index to sort by (default: 2)
        ordertype: "asc" or "desc"
        name: Optional screener name
        save: If True, saves the screener as a template

    Returns:
        list of matching companies [{company: {symbol, name}, ...metrics}]

    Example filters (volume ratio > 1.5 AND price 100-5000):
        [
            {"type": "gt", "item1": <volume_ratio_fitem_id>, "item2": "1.5"},
            {"type": "between", "item1": <price_fitem_id>, "item2": "100", "item3": "5000"},
        ]
    """
    if universe is None:
        universe = {"scope": "IHSG", "scopeID": "", "name": ""}

    import json as _json
    payload = {
        "name": name,
        "description": "",
        "save": "1" if save else "0",
        "ordertype": ordertype,
        "ordercol": ordercol,
        "page": page,
        "universe": _json.dumps(universe),
        "filters": _json.dumps(filters),
    }
    data = _stockbit_post("/screener/templates", payload)
    if "error" in data:
        return []
    inner = data.get("data", {})
    return inner.get("calcs", inner) if isinstance(inner, dict) else inner


def get_screener_favorites() -> list[dict]:
    """
    Get user's favorite screener templates.

    Endpoint: GET exodus.stockbit.com/screener/favorites
    Returns: [{id, name, type, order}, ...]
    """
    data = _stockbit_get("/screener/favorites")
    if "error" in data:
        return []
    return data.get("data", [])


# ─── Carina: Balance ──────────────────────────────────────────────────────────

def get_cash_balance() -> float:
    """
    Get available cash on hand from Carina.

    Endpoint: GET carina.stockbit.com/balance/cash
    Returns: available_cash_on_hand as float
    """
    data = _carina_get("/balance/cash")
    if "error" in data:
        log.warning(f"get_cash_balance: {data['error']}")
        return 0.0
    return float(data.get("data", {}).get("available_cash_on_hand", 0))


def get_cash_info(stock_code: Optional[str] = None, order_id: Optional[str] = None) -> dict:
    """
    Get trading cash info (trade limit, day trade buying power, etc.).

    Endpoint: GET carina.stockbit.com/balance/cash/info
    Returns: {trade_limit, trade_balance, day_trade_buying_power, ...}
    """
    params: dict = {}
    if stock_code:
        params["stock_code"] = stock_code.upper()
    if order_id:
        params["order_id"] = order_id
    data = _carina_get("/balance/cash/info", params)
    if "error" in data:
        return data
    return data.get("data", data)


# ─── Carina: Portfolio Detail ─────────────────────────────────────────────────

def get_position_detail(stock_code: str) -> dict:
    """
    Get per-stock position detail from Carina portfolio.

    Endpoint: GET carina.stockbit.com/portfolio/v2/detail?stock_code={symbol}
    Returns: {symbol, company, qty, price, asset, ...}
    """
    data = _carina_get("/portfolio/v2/detail", {"stock_code": stock_code.upper()})
    if "error" in data:
        return data
    return data.get("data", {}).get("result", data.get("data", data))


# ─── Carina: Orders ───────────────────────────────────────────────────────────

def get_orders(stock_code: Optional[str] = None) -> list[dict]:
    """
    Get open/today's orders from Carina.

    Endpoint: GET carina.stockbit.com/order/v2/list
    Returns: list of order dicts {order_id, symbol, side, price, shares, status_text, ...}
    """
    params: dict = {}
    if stock_code:
        params["filter_criteria.stock_code"] = stock_code.upper()
    data = _carina_get("/order/v2/list", params)
    if "error" in data:
        return []
    return data.get("data", [])


def get_order_detail(order_id: str) -> dict:
    """
    Get detail for a specific order.

    Endpoint: GET carina.stockbit.com/order/v2/detail?order_id={order_id}
    Returns: {order_id, symbol, side, price, shares, status_text, filled_shares, ...}
    """
    data = _carina_get("/order/v2/detail", {"order_id": order_id})
    if "error" in data:
        return data
    return data.get("data", data)


def place_buy_order(
    symbol: str,
    price: int,
    shares: int,
    board_type: str = "RG",
    is_gtc: bool = False,
    time_in_force: str = "0",
    ui_ref: Optional[str] = None,
) -> dict:
    """
    Place a buy order via Carina.

    Endpoint: POST carina.stockbit.com/order/v2/buy

    Args:
        symbol: Stock ticker (e.g. "BBCA")
        price: Limit price in IDR
        shares: Number of shares (not lots — 1 lot = 100 shares)
        board_type: "RG" (regular), "TN" (negotiated)
        is_gtc: Good Till Cancelled
        time_in_force: "0" = day order
        ui_ref: Optional UI reference string

    Returns: {order_id, order_limit_info} or {error}

    WARNING: This places a REAL order. Confirm before calling.
    """
    import time as _time
    if ui_ref is None:
        ui_ref = f"W{int(_time.time() * 1000)}claude"
    payload = {
        "ui_ref": ui_ref,
        "symbol": symbol.upper(),
        "price": price,
        "shares": shares,
        "board_type": board_type,
        "is_gtc": is_gtc,
        "time_in_force": time_in_force,
        "platform_order_type": "PLATFORM_ORDER_TYPE_LIMIT_DAY",
    }
    data = _carina_post("/order/v2/buy", payload)
    if "error" in data:
        return data
    return data.get("data", data)


def place_sell_order(
    symbol: str,
    price: int,
    shares: int,
    board_type: str = "RG",
    is_gtc: bool = False,
    time_in_force: str = "0",
    ui_ref: Optional[str] = None,
) -> dict:
    """
    Place a sell order via Carina.

    Endpoint: POST carina.stockbit.com/order/v2/sell

    Args:
        symbol: Stock ticker (e.g. "BBCA")
        price: Limit price in IDR
        shares: Number of shares (not lots — 1 lot = 100 shares)
        board_type: "RG" (regular), "TN" (negotiated)
        is_gtc: Good Till Cancelled
        time_in_force: "0" = day order
        ui_ref: Optional UI reference string

    Returns: {order_id, order_limit_info} or {error}

    WARNING: This places a REAL order. Confirm before calling.
    """
    import time as _time
    if ui_ref is None:
        ui_ref = f"W{int(_time.time() * 1000)}claude"
    payload = {
        "ui_ref": ui_ref,
        "symbol": symbol.upper(),
        "price": price,
        "shares": shares,
        "board_type": board_type,
        "is_gtc": is_gtc,
        "time_in_force": time_in_force,
        "platform_order_type": "PLATFORM_ORDER_TYPE_LIMIT_DAY",
    }
    data = _carina_post("/order/v2/sell", payload)
    if "error" in data:
        return data
    return data.get("data", data)


def cancel_order(order_id: str, ui_ref: Optional[str] = None) -> dict:
    """
    Cancel an open order via Carina.

    Endpoint: POST carina.stockbit.com/order/v2/cancel

    Args:
        order_id: Order ID to cancel

    Returns: {} on success or {error}
    """
    import time as _time
    if ui_ref is None:
        ui_ref = f"W{int(_time.time() * 1000)}claude"
    data = _carina_post("/order/v2/cancel", {"order_id": order_id, "ui_ref": ui_ref})
    if "error" in data:
        return data
    return data.get("data", data)


def amend_orders(amend_requests: list[dict], ui_ref: Optional[str] = None) -> dict:
    """
    Bulk amend open orders via Carina.

    Endpoint: POST carina.stockbit.com/order/v2/amend/bulk

    Args:
        amend_requests: List of {order_id, price, shares}
        ui_ref: Optional UI reference string

    Returns: {accepted: [...], rejected: [...]} or {error}

    Example:
        amend_orders([{"order_id": "XL039421L...", "price": 1770, "shares": 5000}])
    """
    import time as _time
    if ui_ref is None:
        ui_ref = f"W{int(_time.time() * 1000)}claude"
    data = _carina_post("/order/v2/amend/bulk", {"ui_ref": ui_ref, "amend_request": amend_requests})
    if "error" in data:
        return data
    return data.get("data", data)


def cancel_stop_order(order_id: str) -> dict:
    """
    Cancel a smart/stop order via Carina.

    Endpoint: DELETE carina.stockbit.com/smart-order/stop-order/v1/order/{order_id}

    Returns: {} on success or {error}
    """
    return _carina_delete(f"/smart-order/stop-order/v1/order/{order_id}")


# ─── Stockbit Direct: Price & Volume ─────────────────────────────────────────

def get_price(ticker: str) -> float:
    """Get current price from Stockbit intraday chart (last candle close)."""
    chart = get_stockbit_chart(ticker, timeframe="today")
    if isinstance(chart, dict):
        prices = chart.get("prices", [])
        if prices:
            last = prices[-1]
            return float(last.get("value") or last.get("close") or 0)
    return 0.0


def get_candles(ticker: str, timeframe: str = "1d", limit: int = 50) -> list[dict]:
    """Get OHLCV candles directly from Stockbit."""
    tf = timeframe.lower()
    tf_for_chart = "1y" if tf in {"1d", "daily", "d"} else tf
    chart = get_stockbit_chart(ticker, timeframe=tf_for_chart)
    if not isinstance(chart, dict) or "error" in chart:
        return []
    prices = chart.get("prices", [])
    candles: list[dict] = []
    for p in prices:
        try:
            candles.append({
                "open": float(p.get("open") or p.get("o") or p.get("value") or 0),
                "high": float(p.get("high") or p.get("h") or p.get("value") or 0),
                "low": float(p.get("low") or p.get("l") or p.get("value") or 0),
                "close": float(p.get("value") or p.get("close") or p.get("c") or 0),
                "volume": float(p.get("volume") or p.get("v") or 0),
                "date": p.get("formatted_date") or p.get("date") or p.get("time"),
            })
        except Exception:
            continue
    return candles[-limit:] if candles else []


def get_volume(ticker: str) -> int:
    """Get current session total volume from Stockbit intraday chart."""
    chart = get_stockbit_chart(ticker, timeframe="today")
    if not isinstance(chart, dict):
        return 0
    prices = chart.get("prices", [])
    return int(sum(float(p.get("volume") or 0) for p in prices))


def get_price_history(ticker: str, days: int = 30) -> list[dict]:
    """Get historical OHLCV for structure analysis."""
    candles = get_candles(ticker, timeframe="1d", limit=days)
    return [
        {
            "high": c.get("high", 0),
            "low": c.get("low", 0),
            "close": c.get("close", 0),
            "volume": c.get("volume", 0),
            "date": c.get("date", ""),
        }
        for c in candles
    ]


def get_avg_volume(ticker: str) -> float:
    """Compute 20-day average daily volume from Stockbit 3m chart."""
    candles = get_candles(ticker, timeframe="3m", limit=20)
    vols = [c.get("volume", 0) for c in candles if c.get("volume", 0) > 0]
    return sum(vols) / len(vols) if vols else 0.0


def get_volume_ratio(ticker: str) -> float:
    """Get intraday volume / 20-day avg volume ratio."""
    vol = get_volume(ticker)
    avg = get_avg_volume(ticker)
    return vol / avg if avg > 0 else 0.0


# ─── Stockbit + Local Compute: Technical ──────────────────────────────────────

@dataclass
class SupportResistance:
    support: float = 0.0
    resistance: float = 0.0
    raw: dict = field(default_factory=dict)


def get_support_resistance(ticker: str, timeframe: str = "1d") -> SupportResistance:
    """Compute support/resistance from recent candle pivots (Stockbit data)."""
    candles = get_candles(ticker, timeframe=timeframe, limit=30)
    if not candles:
        return SupportResistance()
    highs = [c["high"] for c in candles if c.get("high")]
    lows = [c["low"] for c in candles if c.get("low")]
    # Simple pivot: resistance = recent swing high, support = recent swing low
    resistance = max(highs[-10:]) if highs else 0.0
    support = min(lows[-10:]) if lows else 0.0
    return SupportResistance(support=support, resistance=resistance, raw={"method": "pivot_10d"})


def get_trend(ticker: str, timeframe: str = "1d") -> dict:
    """Determine trend direction from candle structure (Stockbit data)."""
    candles = get_candles(ticker, timeframe=timeframe, limit=20)
    if len(candles) < 5:
        return {"trend": "unknown"}
    closes = [c["close"] for c in candles if c.get("close")]
    if len(closes) < 5:
        return {"trend": "unknown"}
    short_avg = sum(closes[-5:]) / 5
    long_avg = sum(closes) / len(closes)
    if short_avg > long_avg * 1.01:
        trend = "uptrend"
    elif short_avg < long_avg * 0.99:
        trend = "downtrend"
    else:
        trend = "sideways"
    return {"trend": trend, "short_avg": short_avg, "long_avg": long_avg}


def _get_computed(ticker: str, key: str, timeframe: str = "1d") -> float:
    """Helper: run compute_indicators_from_price_data and extract a single key."""
    result = compute_indicators_from_price_data(ticker, timeframe=timeframe)
    if "error" in result:
        return 0.0
    return float(result.get(key) or 0)


def get_rsi(ticker: str, timeframe: str = "1d", period: int = 14) -> float:
    """Get RSI computed locally from Stockbit candle data."""
    return _get_computed(ticker, "rsi_14", timeframe)


def get_ema(ticker: str, timeframe: str = "1d", window: int = 20) -> float:
    """Get EMA computed locally from Stockbit candle data."""
    key = f"ema_{window}"
    return _get_computed(ticker, key, timeframe)


def get_atr(ticker: str, timeframe: str = "1d", period: int = 14) -> float:
    """Get ATR computed locally from Stockbit candle data."""
    return _get_computed(ticker, "atr_14", timeframe)


def get_golden_cross(ticker: str, timeframe: str = "1d", fast: int = 7, slow: int = 21) -> dict:
    """Compute MA crossover signal locally from Stockbit candle data."""
    result = compute_indicators_from_price_data(ticker, timeframe=timeframe)
    if "error" in result:
        return {"signal": "unknown", "error": result["error"]}
    fast_val = result.get(f"ema_{fast}") or result.get("ema_20")
    slow_val = result.get(f"ema_{slow}") or result.get("ema_50")
    if not fast_val or not slow_val:
        return {"signal": "unknown"}
    signal = "golden_cross" if float(fast_val) > float(slow_val) else "death_cross"
    return {"signal": signal, "fast_ema": fast_val, "slow_ema": slow_val}


def get_cycle_signal(ticker: str, timeframe: str = "1d") -> dict:
    """Simple cycle signal from RSI position (replaces backend cycle endpoint)."""
    rsi = get_rsi(ticker, timeframe)
    if rsi == 0:
        return {"signal": "unknown"}
    if rsi < 30:
        signal = "oversold"
    elif rsi > 70:
        signal = "overbought"
    elif rsi < 50:
        signal = "accumulation_zone"
    else:
        signal = "distribution_zone"
    return {"signal": signal, "rsi": rsi}


def get_indicators(ticker: str, timeframe: str = "1d", limit: int = 50) -> dict:
    """Get all technical indicators computed locally from Stockbit candle data."""
    return compute_indicators_from_price_data(ticker, timeframe=timeframe, limit=limit)


# ─── Backend API: Broker Analysis ──────────────────────────────────────────────

@dataclass
class BrokerEntry:
    code: str
    category: str
    movement: list[str] = field(default_factory=list)
    avg_price: float = 0.0
    inventory_val: float = 0.0
    inventory_vol: int = 0
    buy_days: int = 0
    sell_days: int = 0
    consistency: float = 0.0


@dataclass
class BrokerDistribution:
    ticker: str
    top_buyers: list[BrokerEntry] = field(default_factory=list)
    top_sellers: list[BrokerEntry] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def _parse_broker_entry(raw: dict) -> BrokerEntry:
    """Parse a single broker entry from API response."""
    code = raw.get("name", "??")
    movement = raw.get("movement", [])
    active_days = [d for d in movement if d]
    buy_days = sum(1 for d in movement if d == "Buy")
    sell_days = sum(1 for d in movement if d == "Sell")
    total_active = len(active_days) if active_days else 1
    
    # avg_price is per-LOT (100 shares), convert to per-share
    raw_avg = float(raw.get("avg_price", 0))
    per_share = raw_avg / 100 if raw_avg > 0 else 0.0
    
    return BrokerEntry(
        code=code,
        category=classify_broker(code),
        movement=movement,
        avg_price=per_share,
        inventory_val=float(raw.get("current_inventory_val", 0)),
        inventory_vol=int(raw.get("current_inventory_vol", 0)),
        buy_days=buy_days,
        sell_days=sell_days,
        consistency=buy_days / total_active if total_active > 0 else 0.0,
    )


def get_broker_distribution(ticker: str) -> BrokerDistribution:
    """
    Get 30-day broker distribution with movement history.
    Source: backend API (/data/raw/broker-distribution) — this is a backend-aggregated
    dataset (30-day accumulation tracking) not available as a single Stockbit call.
    Backend-only exception: token, RAG, watchlist, AND this aggregation.
    """
    data = _backend_get("/data/raw/broker-distribution", {"ticker": ticker})
    if "error" in data:
        return BrokerDistribution(ticker=ticker, raw=data)
    buyers = [_parse_broker_entry(b) for b in data.get("top_buy_brokers", [])]
    sellers = [_parse_broker_entry(s) for s in data.get("top_sell_brokers", [])]
    return BrokerDistribution(ticker=ticker, top_buyers=buyers, top_sellers=sellers, raw=data)


@dataclass
class BrokerInfo:
    ticker: str
    bandar_accdist: str = ""
    total_buyer: int = 0
    total_seller: int = 0
    value: float = 0.0
    top_buy_brokers: list[dict] = field(default_factory=list)
    top_sell_brokers: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def get_broker_info(ticker: str) -> BrokerInfo:
    """Get broker info with bandar detector directly from Stockbit."""
    data = get_stockbit_broker_info(ticker)
    if not data or "error" in data:
        return BrokerInfo(ticker=ticker, raw=data or {})
    bd = data.get("bandar_detector", {})
    bs = data.get("broker_summary", {})
    return BrokerInfo(
        ticker=ticker,
        bandar_accdist=bd.get("broker_accdist", ""),
        total_buyer=bd.get("total_buyer", 0),
        total_seller=bd.get("total_seller", 0),
        value=bd.get("value", 0),
        top_buy_brokers=bs.get("brokers_buy", []),
        top_sell_brokers=bs.get("brokers_sell", []),
        raw=data,
    )


def get_broker_movement(ticker: str, period: str = "1m") -> list[dict]:
    """Get broker movement history directly from Stockbit (period: 1w, 1m, 3m)."""
    data = get_stockbit_broker_movement(ticker, period=period)
    return data.get("brokers", data.get("data", [])) if isinstance(data, dict) else []


def analyze_bid_offer(ticker: str) -> dict:
    """
    Analyze bid/offer pressure from live Stockbit orderbook.
    Returns: bid_offer_ratio, total_bid_volume, total_offer_volume, pattern
    """
    ob = get_stockbit_orderbook(ticker)
    if not ob or "error" in ob:
        return {"ticker": ticker, "error": "No orderbook data"}
    bids = ob.get("bid", [])
    offers = ob.get("offer", [])
    total_bid_vol = sum(int(b.get("volume", 0) or 0) for b in bids)
    total_offer_vol = sum(int(o.get("volume", 0) or 0) for o in offers)
    total = total_bid_vol + total_offer_vol
    ratio = total_bid_vol / total if total > 0 else 0
    if ratio > 0.6:
        pattern, signal = "bid_pressure", "buyers_dominant"
    elif ratio < 0.4:
        pattern, signal = "offer_pressure", "sellers_dominant"
    else:
        pattern, signal = "balanced", "neutral"
    return {
        "ticker": ticker,
        "bid_offer_ratio": round(ratio, 2),
        "total_bid_volume": total_bid_vol,
        "total_offer_volume": total_offer_vol,
        "bid_count": len(bids),
        "offer_count": len(offers),
        "pattern": pattern,
        "signal": signal,
    }


# ─── Orderbook & Tape (Stockbit direct + local delta) ─────────────────────────

_ORDERBOOK_STATE_DIR = ORDERBOOK_STATE_DIR


def _num(v: Any) -> float:
    """Robust numeric parser for Stockbit payloads (string/int/float)."""
    if isinstance(v, (int, float)):
        return float(v)
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".-")
        try:
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0


def _parse_orderbook_levels(levels: list[dict]) -> list[dict]:
    """Normalize orderbook levels into numeric shape."""
    out: list[dict] = []
    for lv in levels or []:
        price = _num(lv.get("price"))
        volume = int(_num(lv.get("volume")))
        que_num = int(_num(lv.get("que_num")))
        if price <= 0:
            continue
        out.append({"price": price, "volume": volume, "que_num": que_num})
    return out


def _large_threshold(levels: list[dict], top_n: int = 10) -> int:
    """Dynamic large-lot threshold (waterseven-style, but simpler)."""
    sample = levels[:top_n]
    if not sample:
        return 1000
    avg = sum(x["volume"] for x in sample) / max(len(sample), 1)
    # 2.5x top-book average, with a sensible floor.
    return max(1000, int(avg * 2.5))


def _proximity(price: float, current_price: float) -> str:
    if current_price <= 0:
        return "unknown"
    dist = abs(price - current_price) / current_price
    return "near" if dist <= 0.01 else "far"


def _state_path(ticker: str) -> Path:
    _ORDERBOOK_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return _ORDERBOOK_STATE_DIR / f"{ticker.upper()}.json"


def get_orderbook_delta(ticker: str) -> dict:
    """
    Local orderbook delta (no backend dependency).

    Source:
    - Current snapshot from Stockbit direct orderbook.
    - Previous snapshot from local state file.

    Returns a waterseven-compatible delta summary + pressure metrics.
    """
    ticker = ticker.upper()
    ob = get_stockbit_orderbook(ticker)
    if not ob or "error" in ob:
        return {"ticker": ticker, "error": ob.get("error", "No orderbook data") if isinstance(ob, dict) else "No orderbook data"}

    bids = _parse_orderbook_levels(ob.get("bid", []))
    offers = _parse_orderbook_levels(ob.get("offer", []))
    if not bids and not offers:
        return {"ticker": ticker, "error": "Empty orderbook"}

    current_price = _num(ob.get("lastprice") or ob.get("close") or ob.get("previous"))

    top_n = 10
    top_bids = bids[:top_n]
    top_offers = offers[:top_n]

    total_bid_volume = sum(x["volume"] for x in top_bids)
    total_offer_volume = sum(x["volume"] for x in top_offers)
    total_bid_value = sum(x["price"] * x["volume"] for x in top_bids)
    total_offer_value = sum(x["price"] * x["volume"] for x in top_offers)

    bid_offer_ratio = (total_bid_volume / total_offer_volume) if total_offer_volume > 0 else 0.0
    bid_offer_value_ratio = (total_bid_value / total_offer_value) if total_offer_value > 0 else 0.0

    bid_thr = _large_threshold(top_bids)
    offer_thr = _large_threshold(top_offers)

    curr_bid_map = {int(x["price"]): int(x["volume"]) for x in bids[:20]}
    curr_offer_map = {int(x["price"]): int(x["volume"]) for x in offers[:20]}

    prev = {}
    p = _state_path(ticker)
    if p.exists():
        try:
            prev = json.loads(p.read_text())
        except Exception:
            prev = {}

    prev_bid_map = {int(k): int(v) for k, v in (prev.get("bid_map") or {}).items()}
    prev_offer_map = {int(k): int(v) for k, v in (prev.get("offer_map") or {}).items()}
    prev_bid_total = int(prev.get("total_bid_volume", 0))
    prev_offer_total = int(prev.get("total_offer_volume", 0))

    # Delta events
    new_large_bids = []
    withdrawn_bids = []
    reduced_bids = []
    new_large_offers = []
    withdrawn_offers = []
    reduced_offers = []

    for px, vol in curr_bid_map.items():
        prev_vol = prev_bid_map.get(px)
        if prev_vol is None and vol >= bid_thr:
            new_large_bids.append({"price": px, "lot": vol, "proximity": _proximity(px, current_price)})
        elif prev_vol is not None and prev_vol > 0 and vol < prev_vol * 0.6 and prev_vol >= max(1000, bid_thr // 2):
            reduced_bids.append({"price": px, "previous_lot": prev_vol, "current_lot": vol, "proximity": _proximity(px, current_price)})

    for px, prev_vol in prev_bid_map.items():
        if px not in curr_bid_map and prev_vol >= max(1000, bid_thr // 2):
            withdrawn_bids.append({"price": px, "previous_lot": prev_vol, "proximity": _proximity(px, current_price)})

    for px, vol in curr_offer_map.items():
        prev_vol = prev_offer_map.get(px)
        if prev_vol is None and vol >= offer_thr:
            new_large_offers.append({"price": px, "lot": vol, "proximity": _proximity(px, current_price)})
        elif prev_vol is not None and prev_vol > 0 and vol < prev_vol * 0.6 and prev_vol >= max(1000, offer_thr // 2):
            reduced_offers.append({"price": px, "previous_lot": prev_vol, "current_lot": vol, "proximity": _proximity(px, current_price)})

    for px, prev_vol in prev_offer_map.items():
        if px not in curr_offer_map and prev_vol >= max(1000, offer_thr // 2):
            withdrawn_offers.append({"price": px, "previous_lot": prev_vol, "proximity": _proximity(px, current_price)})

    total_bid_lot_change = total_bid_volume - prev_bid_total
    total_offer_lot_change = total_offer_volume - prev_offer_total

    bid_volume_trend = "up" if total_bid_lot_change > 0 else ("down" if total_bid_lot_change < 0 else "flat")
    offer_volume_trend = "up" if total_offer_lot_change > 0 else ("down" if total_offer_lot_change < 0 else "flat")

    # Persist snapshot for next delta
    try:
        p.write_text(json.dumps({
            "ts": int(time.time()),
            "current_price": current_price,
            "total_bid_volume": total_bid_volume,
            "total_offer_volume": total_offer_volume,
            "bid_map": {str(k): v for k, v in curr_bid_map.items()},
            "offer_map": {str(k): v for k, v in curr_offer_map.items()},
        }))
    except Exception as e:
        log.warning(f"Failed saving orderbook state for {ticker}: {e}")

    pressure_side = "buyers" if bid_offer_value_ratio > 1.2 else ("sellers" if bid_offer_value_ratio < 0.8 else "balanced")

    # --- Whale / institutional detection (lots-per-frequency analysis) ---
    # High lots with low que_num = big orders = institutional / whale
    # Low lots with high que_num = many small orders = retail
    bid_whale_ticks = []
    bid_retail_ticks = []
    for lv in top_bids:
        vol = lv["volume"]
        qn = lv.get("que_num", 0)
        if qn > 0 and vol > 0:
            lots_per_order = vol / qn
            if lots_per_order >= 100 and vol >= 1000:  # 100+ lots per order, min 1000 lots
                bid_whale_ticks.append({"price": lv["price"], "volume": vol, "que_num": qn, "lots_per_order": round(lots_per_order)})
            elif lots_per_order <= 20 and qn >= 20:
                bid_retail_ticks.append({"price": lv["price"], "volume": vol, "que_num": qn, "lots_per_order": round(lots_per_order)})

    offer_whale_ticks = []
    offer_retail_ticks = []
    for lv in top_offers:
        vol = lv["volume"]
        qn = lv.get("que_num", 0)
        if qn > 0 and vol > 0:
            lots_per_order = vol / qn
            if lots_per_order >= 100 and vol >= 1000:
                offer_whale_ticks.append({"price": lv["price"], "volume": vol, "que_num": qn, "lots_per_order": round(lots_per_order)})
            elif lots_per_order <= 20 and qn >= 20:
                offer_retail_ticks.append({"price": lv["price"], "volume": vol, "que_num": qn, "lots_per_order": round(lots_per_order)})

    # Bid depth shape: how evenly distributed is bid support?
    bid_volumes = [lv["volume"] for lv in top_bids] if top_bids else []
    bid_depth_shape = "empty"
    if bid_volumes:
        avg_bid = sum(bid_volumes) / len(bid_volumes)
        max_bid_vol = max(bid_volumes)
        if max_bid_vol > 0 and (max_bid_vol / avg_bid) <= 2.0:
            bid_depth_shape = "spread"  # support across multiple levels
        elif max_bid_vol > 0 and (max_bid_vol / avg_bid) > 3.0:
            bid_depth_shape = "concentrated"  # one big wall, rest thin
        else:
            bid_depth_shape = "moderate"

    # Dominance level (stronger signal tiers)
    dominance = "neutral"
    if bid_offer_value_ratio >= 3.0:
        dominance = "extreme_bid"      # like IMPC 3.6:1
    elif bid_offer_value_ratio >= 2.0:
        dominance = "strong_bid"       # like VKTR 2.7:1
    elif bid_offer_value_ratio >= 1.5:
        dominance = "moderate_bid"     # like ENRG 1.5-1.7:1
    elif bid_offer_value_ratio <= 0.33:
        dominance = "extreme_offer"
    elif bid_offer_value_ratio <= 0.5:
        dominance = "strong_offer"
    elif bid_offer_value_ratio <= 0.67:
        dominance = "moderate_offer"

    # --- Manipulation pattern detection ---
    # Uses tick_walls concentration analysis to identify mismatch between visible wall and whale activity
    walls = analyze_tick_walls(ob)
    offer_near_concentrated = walls.get('retail_blocking_risk') == 'high'
    nearest_bid_wall = walls.get('nearest_bid_wall') or {}
    bid_near_concentrated = (
        nearest_bid_wall.get('tick_index', 99) <= 1
        and walls.get('bid_wall_concentration', 0) >= 0.35
    )

    manipulation_setup = None
    contested_tape = None
    if offer_near_concentrated and bid_whale_ticks:
        # Concentrated offer wall scaring retail, but whale-sized bids sit underneath = accumulation trap
        manipulation_setup = 'accumulation_setup'
    elif bid_near_concentrated and offer_whale_ticks:
        # Concentrated bid wall attracting retail, but whale-sized offers sit behind = distribution trap
        manipulation_setup = 'distribution_setup'

    if (
        dominance in ('extreme_bid', 'strong_bid')
        and bid_whale_ticks
        and offer_whale_ticks
        and manipulation_setup == 'distribution_setup'
    ):
        contested_tape = 'controlled_bid_support'

    # --- Wick / shakeout detection ---
    # Compares current price to previous snapshot price to identify engineered dips
    wick_shakeout = None
    prev_price = float(prev.get('current_price') or 0)
    if prev_price > 0 and current_price and current_price > 0:
        price_drop_pct = (prev_price - current_price) / prev_price
        if price_drop_pct >= 0.015:  # >1.5% drop from previous snapshot
            if offer_near_concentrated and bid_whale_ticks:
                # New offer wall appeared at near ticks while whale bids held = engineered dip
                wick_shakeout = 'shakeout_trap'
            elif bid_whale_ticks:
                # Price dropped but whale bids still present = shakeout with accumulation underneath
                wick_shakeout = 'shakeout_with_accumulation'
            else:
                # Price dropped and no whale bid support visible = genuine selling
                wick_shakeout = 'genuine_selling'

    return {
        "ticker": ticker,
        "source": "stockbit_local_delta",
        "current_price": current_price,
        "total_bid_volume": total_bid_volume,
        "total_offer_volume": total_offer_volume,
        "total_bid_value": round(total_bid_value, 2),
        "total_ask_value": round(total_offer_value, 2),
        # Compatibility aliases used by psychology code
        "bid_value": round(total_bid_value, 2),
        "ask_value": round(total_offer_value, 2),
        # Ratios
        "bid_offer_ratio": round(bid_offer_ratio, 2),
        "bid_offer_value_ratio": round(bid_offer_value_ratio, 2),
        "pressure_side": pressure_side,
        "dominance": dominance,
        # Whale / institutional detection
        "bid_whale_ticks": bid_whale_ticks,
        "bid_retail_ticks": bid_retail_ticks,
        "offer_whale_ticks": offer_whale_ticks,
        "offer_retail_ticks": offer_retail_ticks,
        "bid_depth_shape": bid_depth_shape,
        # Delta fields (waterseven-style)
        "bid_volume_trend": bid_volume_trend,
        "offer_volume_trend": offer_volume_trend,
        "total_bid_lot_change": total_bid_lot_change,
        "total_offer_lot_change": total_offer_lot_change,
        "new_large_bids": new_large_bids,
        "withdrawn_bids": withdrawn_bids,
        "reduced_bids": reduced_bids,
        "new_large_offers": new_large_offers,
        "withdrawn_offers": withdrawn_offers,
        "reduced_offers": reduced_offers,
        "bid_withdrawal_detected": len(withdrawn_bids) > 0,
        "bid_reduction_detected": len(reduced_bids) > 0,
        "offer_pressure_detected": (offer_volume_trend == "up" and total_offer_lot_change > 0) or len(new_large_offers) > 0,
        "has_previous_snapshot": bool(prev),
        # Manipulation / contested tape detection
        "manipulation_setup": manipulation_setup,
        "contested_tape": contested_tape,
        "wick_shakeout": wick_shakeout,
    }


def get_running_trades(ticker: str, limit: int = 50) -> list[dict]:
    """Get recent trade executions directly from Stockbit."""
    data = get_stockbit_running_trade(ticker, limit=limit)
    if not isinstance(data, dict):
        return []
    return data.get("running_trade", data.get("rows", []))


def analyze_running_trades(ticker: str, limit: int = 100) -> dict:
    """
    Analyze running trades for patterns.
    
    Key patterns:
    - Big lot + low frequency = institutional/bandar accumulation
    - Small lot + high frequency = retail noise
    - Time clustering = coordinated buying/selling
    """
    trades = get_running_trades(ticker, limit)
    if not trades:
        return {"ticker": ticker, "status": "no_data", "pattern": "unknown"}
    
    total_volume = 0
    total_value = 0
    buy_volume = 0
    sell_volume = 0
    big_lot_count = 0  # >50 lot trades
    small_lot_count = 0
    
    for trade in trades:
        volume = trade.get("volume", 0)
        price = trade.get("price", 0)
        side = str(trade.get("side", "")).lower()
        
        total_volume += volume
        total_value += volume * price
        
        if side in ("buy", "b"):
            buy_volume += volume
        elif side in ("sell", "s"):
            sell_volume += volume
        
        lot_size = volume / 100
        if lot_size >= 50:
            big_lot_count += 1
        else:
            small_lot_count += 1
    
    trade_count = len(trades)
    big_lot_ratio = big_lot_count / trade_count if trade_count > 0 else 0
    avg_volume = total_volume / trade_count if trade_count > 0 else 0
    
    if big_lot_ratio > 0.3 and trade_count < 50:
        pattern = "institutional_accumulation"
        interpretation = "Big lots with low frequency - likely smart money"
    elif big_lot_ratio < 0.1 and trade_count > 80:
        pattern = "retail_noise"
        interpretation = "Small lots high frequency - retail dominated"
    elif buy_volume > sell_volume * 1.5:
        pattern = "buying_pressure"
        interpretation = "Strong buying imbalance"
    elif sell_volume > buy_volume * 1.5:
        pattern = "selling_pressure"
        interpretation = "Strong selling imbalance"
    else:
        pattern = "mixed"
        interpretation = "No clear pattern detected"
    
    return {
        "ticker": ticker,
        "status": "analyzed",
        "pattern": pattern,
        "interpretation": interpretation,
        "trade_count": trade_count,
        "big_lot_count": big_lot_count,
        "big_lot_ratio": round(big_lot_ratio, 2),
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "avg_volume_per_trade": round(avg_volume, 0),
        "total_value": total_value,
    }


# ─── Backend API: RAG & Insights ───────────────────────────────────────────────

def rag_search(
    query: str,
    ticker: Optional[str] = None,
    top_n: int = 5,
    min_confidence: int = 50,
    max_days: int = 30,
) -> list[dict]:
    """
    Search RAG with resilient fallback order:
    1) /rag/search source=insight (v3 insight)
    2) /rag/search sources=analysis+thesis
    3) /rag legacy endpoint with sources=insights+analysis_thesis

    Returns normalized list. Empty list if all sources return no results.
    """
    # 1) Insight-first (what we use for catalyst/news)
    payload_insight = {
        "query": query,
        "top_n": top_n,
        "sources": ["insight"],
        "filters": {
            "insight_min_confidence": min_confidence,
            "max_days": max_days,
        },
    }
    if ticker:
        payload_insight["filters"]["ticker"] = [ticker.upper()]

    data = _backend_post("/rag/search", payload_insight)
    rows = data.get("merged_results", data.get("results", [])) if isinstance(data, dict) else []
    if rows:
        return rows

    # 2) v3 analysis/thesis fallback
    payload_analysis = {
        "query": query,
        "top_n": top_n,
        "sources": ["analysis", "thesis"],
        "filters": {
            "min_confidence": min_confidence,
            "max_days": max_days,
        },
    }
    if ticker:
        payload_analysis["filters"]["ticker"] = [ticker.upper()]

    data2 = _backend_post("/rag/search", payload_analysis)
    rows2 = data2.get("merged_results", data2.get("results", [])) if isinstance(data2, dict) else []
    if rows2:
        return rows2

    # 3) Legacy /rag fallback (some deployments still serve this better)
    payload_legacy = {
        "text": query,
        "top_n": top_n,
        "sources": ["insights", "analysis_thesis"],
        "min_confidence": min_confidence,
        "timerange": max_days,
    }
    if ticker:
        payload_legacy["ticker"] = ticker.upper()

    data3 = _backend_post("/rag", payload_legacy)
    rows3 = data3.get("results", []) if isinstance(data3, dict) else []
    return rows3 if isinstance(rows3, list) else []


def get_insights(ticker: str, limit: int = 5, days: int = 7) -> list[dict]:
    """Get recent insights for a ticker."""
    data = _backend_get("/data/insight", {"ticker": ticker, "limit": limit, "days": days})
    return data.get("results", data.get("rows", []))


# ─── Backend API: Waterseven State ─────────────────────────────────────────────

def get_watchlist() -> list[dict]:
    """
    Get current watchlist from backend.

    Endpoint priority:
    1) /data/waterseven/strategy?status=watching&limit=100
       - Some backends return {items:[...]}, others {data:[...]}.
       - If empty, we also try status=holding for active positions context.
    2) /watchlist (legacy telegram watchlist)
    """
    # Primary: waterseven strategy state
    for status in ("watching", "holding"):
        data = _backend_get("/data/waterseven/strategy", {"status": status, "limit": 300})
        if isinstance(data, dict):
            rows = data.get("items", data.get("data", data.get("rows", [])))
            if isinstance(rows, list) and rows:
                return rows

    # Fallback: legacy watchlist endpoint
    alt = _backend_get("/watchlist")
    if isinstance(alt, dict):
        rows = alt.get("data", alt.get("items", alt.get("rows", [])))
        if isinstance(rows, list):
            return rows
    return []


def get_market_context(date: Optional[str] = None) -> dict:
    """Get market context from waterseven state."""
    params = {"date": date} if date else {}
    return _backend_get("/data/waterseven/context", params)


# ─── Waterseven CLI (slow, use sparingly) ───────────────────────────────────────

def run_waterseven_screener(tickers: list[str], min_score: int = 0, top_n: int = 20) -> dict:
    """Run waterseven remora screener via CLI. Returns parsed JSON output.
    
    WARNING: This is slow (30+ API calls per ticker). Use sparingly.
    """
    import subprocess
    cmd = [
        "python3", "-m", "remoratrader.cli_runner",
        "screener",
        "--tickers", ",".join(tickers),
        "--min-score", str(min_score),
        "--top-n", str(top_n),
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd="/home/lazywork/bitstock/waterseven",
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout.strip()
        if output:
            return json.loads(output)
    except Exception as e:
        log.error(f"Waterseven screener failed: {e}")
    return {}


# ─── Utility ────────────────────────────────────────────────────────────────────

def vol_label(ratio: float) -> str:
    """Human-readable volume label."""
    if ratio >= 2.0:   return f"🔥 {ratio:.1f}x (STRONG)"
    if ratio >= 1.3:   return f"📈 {ratio:.1f}x (GOOD)"
    if ratio >= 0.8:   return f"➡️ {ratio:.1f}x (NORMAL)"
    return                    f"💤 {ratio:.1f}x (THIN)"


def price_vs_level(price: float, level: float) -> str:
    """How far is price from a level, as %."""
    if level <= 0 or price <= 0:
        return "N/A"
    pct = ((price - level) / level) * 100
    return f"+{pct:.1f}% above" if pct > 0 else f"{pct:.1f}% below"


# ─── Local Indicators from OHLCV (open-skills integration) ───────────────────

def compute_indicators_from_price_data(
    ticker: str,
    timeframe: str = "1d",
    limit: int = 250,
) -> dict:
    """
    Compute 20 indicators locally from OHLCV candles.

    Source concept: open-skills/trading-indicators-from-price-data
    Requires: pandas + pandas-ta
    """
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        return {
            "error": f"pandas_not_available: {e}",
            "hint": "Install pandas (or use backend get_indicators fallback)",
        }

    try:
        import pandas_ta as ta  # type: ignore
    except Exception as e:
        return {
            "error": f"pandas_ta_not_available: {e}",
            "hint": "Install pandas-ta (or use backend get_indicators fallback)",
        }

    candles = get_candles(ticker, timeframe=timeframe, limit=limit)
    if not candles:
        return {"error": "no_candles"}

    df = pd.DataFrame(candles)
    rename_map = {
        "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
        "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    required = ["open", "high", "low", "close", "volume"]
    if any(c not in df.columns for c in required):
        return {"error": "invalid_candle_format", "columns": list(df.columns)}

    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 1 RSI(14)
    df["rsi_14"] = ta.rsi(df["close"], length=14)

    # 2-4 MACD(12,26,9)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        df["macd_line"] = macd.iloc[:, 0]
        df["macd_hist"] = macd.iloc[:, 1]
        df["macd_signal"] = macd.iloc[:, 2]

    # 5-9 MA family
    df["sma_20"] = ta.sma(df["close"], length=20)
    df["sma_50"] = ta.sma(df["close"], length=50)
    df["ema_20"] = ta.ema(df["close"], length=20)
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["wma_20"] = ta.wma(df["close"], length=20)

    # 10-12 Bollinger(20,2)
    bb = ta.bbands(df["close"], length=20, std=2)
    if bb is not None and not bb.empty:
        df["bb_upper"] = bb.iloc[:, 2]
        df["bb_mid"] = bb.iloc[:, 1]
        df["bb_lower"] = bb.iloc[:, 0]

    # 13-14 Stoch(14,3,3)
    stoch = ta.stoch(df["high"], df["low"], df["close"], k=14, d=3, smooth_k=3)
    if stoch is not None and not stoch.empty:
        df["stoch_k"] = stoch.iloc[:, 0]
        df["stoch_d"] = stoch.iloc[:, 1]

    # 15 ATR(14)
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # 16 ADX(14)
    adx = ta.adx(df["high"], df["low"], df["close"], length=14)
    if adx is not None and not adx.empty:
        df["adx_14"] = adx.iloc[:, 0]

    # 17 CCI(20)
    df["cci_20"] = ta.cci(df["high"], df["low"], df["close"], length=20)

    # 18 OBV
    df["obv"] = ta.obv(df["close"], df["volume"])

    # 19 MFI(14)
    df["mfi_14"] = ta.mfi(df["high"], df["low"], df["close"], df["volume"], length=14)

    # 20 ROC(12)
    df["roc_12"] = ta.roc(df["close"], length=12)

    indicator_cols = [
        "rsi_14", "macd_line", "macd_signal", "macd_hist",
        "sma_20", "sma_50", "ema_20", "ema_50", "wma_20",
        "bb_upper", "bb_mid", "bb_lower",
        "stoch_k", "stoch_d", "atr_14", "adx_14", "cci_20", "obv", "mfi_14", "roc_12",
    ]

    latest = {}
    for c in indicator_cols:
        if c in df.columns and not df[c].dropna().empty:
            latest[c] = float(df[c].dropna().iloc[-1])
        else:
            latest[c] = None

    return {
        "ticker": ticker.upper(),
        "timeframe": timeframe,
        "candles": int(len(df)),
        "latest": latest,
        "warmup_note": "Use >=200 candles for stable output; early rows may be NaN",
    }
