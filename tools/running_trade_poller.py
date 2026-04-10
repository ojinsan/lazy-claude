"""
Lazyboy Running Trade Poller
=============================
Poll running trade from Stockbit every 60 seconds.
Store to Redis for 10-minute window.

Usage:
    python3 running_trade_poller.py

Runs as separate service from monitor.py.
"""

import time
import json
import logging
import os
import httpx
from stockbit_headers import stockbit_headers
from datetime import datetime
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")

# Backend API
from config import load_env, backend_url, backend_token, stockbit_token_cache, ensure_watchlist_file
load_env()
BACKEND_URL = backend_url()
BACKEND_TOKEN = backend_token()
BACKEND_HEADERS = {"Authorization": f"Bearer {BACKEND_TOKEN}"} if BACKEND_TOKEN else {}

# Stockbit API
STOCKBIT_BASE_URL = "https://exodus.stockbit.com"

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
RUNNING_TRADE_KEY_PREFIX = "lazyboy:running_trade:"
RUNNING_TRADE_TTL = 600  # 10 minutes

# Token cache
STOCKBIT_TOKEN = None
STOCKBIT_TOKEN_EXPIRES = 0
TOKEN_FILE = str(stockbit_token_cache())

# Watchlist
WATCHLIST_FILE = str(ensure_watchlist_file())


def load_watchlist(limit: int = 20):
    """Load tickers from local watchlist, fallback to backend watchlist."""
    try:
        with open(WATCHLIST_FILE) as f:
            data = json.load(f)
        local = [k.upper() for k in data.keys() if not k.startswith("_")]
        if local:
            return local[:limit]
    except Exception:
        pass
    try:
        r = httpx.get(f"{BACKEND_URL}/watchlist", headers=BACKEND_HEADERS, timeout=10)
        if r.status_code == 200:
            rows = r.json().get('data', [])
            out = []
            for row in rows:
                ticker = (row.get('stock') or row.get('ticker') or '').upper()
                if ticker and ticker not in out:
                    out.append(ticker)
                if len(out) >= limit:
                    break
            return out
    except Exception as e:
        log.warning(f"Backend watchlist fallback failed: {e}")
    return []


def get_stockbit_token():
    """Reuse the main api.py token loader so poller matches the working request path."""
    global STOCKBIT_TOKEN, STOCKBIT_TOKEN_EXPIRES
    try:
        import api as trader_api
        token = trader_api.get_stockbit_token()
        if token:
            STOCKBIT_TOKEN = token
            return token
    except Exception as e:
        log.warning(f"Failed to load token from main api.py path: {e}")
    return None


def get_running_trade_stockbit(ticker, limit=100):
    """Fetch running trades from Stockbit API with rate limit handling."""
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
        
        # Handle rate limiting
        if r.status_code == 429:
            log.warning(f"Rate limited for {ticker}, skipping...")
            return []
        
        if r.status_code == 200:
            data = r.json().get("data", {})
            return data.get("running_trade", [])
    except Exception as e:
        log.warning(f"Running trade fetch failed for {ticker}: {e}")
    
    return []


def get_redis():
    """Get Redis client."""
    try:
        import redis
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception as e:
        log.warning(f"Redis not available: {e}")
        return None


def store_trades_to_redis(ticker, trades):
    """Store trades to Redis with timestamp."""
    r = get_redis()
    if not r:
        return
    
    now = time.time()
    key = f"{RUNNING_TRADE_KEY_PREFIX}{ticker}"
    
    try:
        # Add timestamp to each trade
        for trade in trades:
            trade["_ts"] = now
            r.rpush(key, json.dumps(trade))
        
        # Set expiry
        r.expire(key, RUNNING_TRADE_TTL)
        
        log.debug(f"Stored {len(trades)} trades for {ticker}")
    except Exception as e:
        log.warning(f"Redis store failed for {ticker}: {e}")


def is_market_hours():
    """Check if we're in IDX trading hours."""
    now = datetime.now(WIB)
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return 900 <= hour_min <= 1515


def run():
    log.info("🛋️  Lazyboy Running Trade Poller started")
    log.info(f"Polling interval: 60s (backend watchlist fallback enabled)")
    
    tickers = load_watchlist()
    if not tickers:
        log.error("No tickers in watchlist")
        return
    
    log.info(f"Watching: {', '.join(tickers)}")
    
    # Check token
    token = get_stockbit_token()
    if token:
        log.info("✅ Stockbit token OK")
    else:
        log.warning("⚠️ No Stockbit token")
    
    # Check Redis
    r = get_redis()
    if r:
        log.info("✅ Redis connected")
    else:
        log.warning("⚠️ Redis not available - will not store")
    
    while True:
        if not is_market_hours():
            log.info(f"Market closed. Sleeping 60s...")
            time.sleep(60)
            continue
        
        now_str = datetime.now(WIB).strftime("%H:%M:%S")
        log.info(f"[{now_str}] Polling running trades...")
        
        for i, ticker in enumerate(tickers):
            # Rate limiting: delay between requests
            if i > 0:
                time.sleep(0.6)  # 600ms delay between tickers to reduce 429 risk
            
            trades = get_running_trade_stockbit(ticker, limit=100)
            if trades:
                store_trades_to_redis(ticker, trades)
                log.info(f"  {ticker}: {len(trades)} trades")
            else:
                log.debug(f"  {ticker}: no trades")
        
        time.sleep(60)


if __name__ == "__main__":
    run()
