#!/usr/bin/env python3
"""
Lazyboy Orderbook Poller (HTTP fallback)
==========================================
Poll orderbook via HTTP every 60 seconds.
"""

import time
import httpx
import logging
import json
import os
import sys

from stockbit_headers import stockbit_headers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

STOCKBIT_BASE_URL = "https://exodus.stockbit.com"
POLL_INTERVAL = 60
from config import load_env, backend_url, backend_token
load_env()
BACKEND_URL = backend_url()
BACKEND_TOKEN = backend_token()
BACKEND_HEADERS = {"Authorization": f"Bearer {BACKEND_TOKEN}"} if BACKEND_TOKEN else {}

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
ORDERBOOK_KEY_PREFIX = "lazyboy:orderbook:"
ORDERBOOK_TTL = 300

WATCHLIST = ["ESSA", "ITMG", "BUMI", "PTRO", "BULL", "VKTR", "ENRG", "BIPI", "KETR", "INCO", "CLEO", "AADI"]

def get_stockbit_token():
    """Get token from backend."""
    try:
        r = httpx.get(f"{BACKEND_URL}/token-store/stockbit", headers=BACKEND_HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("token")
    except Exception as e:
        log.error(f"Failed to get token: {e}")
    return None

def poll_orderbook(token):
    """Poll orderbook for all tickers with rate limiting."""
    import redis
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
    except Exception as e:
        log.error(f"Redis connection failed: {e}")
        return
    
    for i, ticker in enumerate(WATCHLIST):
        try:
            # Rate limiting: delay between requests
            if i > 0:
                time.sleep(0.5)  # 500ms delay between tickers
            
            url = f"{STOCKBIT_BASE_URL}/company-price-feed/v2/orderbook/companies/{ticker}"
            headers = stockbit_headers(token)
            
            resp = httpx.get(url, headers=headers, timeout=10)
            
            # Handle rate limiting
            if resp.status_code == 429:
                log.warning(f"Rate limited for {ticker}, waiting 5s...")
                time.sleep(5)
                continue
            
            if resp.status_code != 200:
                log.error(f"Orderbook fetch failed for {ticker}: {resp.status_code}")
                continue
            
            data = resp.json()
            ob_data = data.get("data", {})
            bids = ob_data.get("bid", [])
            offers = ob_data.get("offer", [])
            
            # Calculate mid price
            best_bid = float(bids[0].get("price", 0)) if bids else 0
            best_offer = float(offers[0].get("price", 0)) if offers else 0
            mid_price = (best_bid + best_offer) / 2 if (best_bid and best_offer) else 0
            
            # Store to Redis
            key = f"{ORDERBOOK_KEY_PREFIX}{ticker}"
            snapshot = {
                "ticker": ticker,
                "bids": bids[:5],
                "offers": offers[:5],
                "mid_price": mid_price,
                "timestamp": time.time(),
            }
            r.setex(key, ORDERBOOK_TTL, json.dumps(snapshot))
            log.info(f"✅ {ticker}: stored orderbook (mid={mid_price})")
            
        except Exception as e:
            log.error(f"Failed to poll {ticker}: {e}")

def main():
    log.info("🚀 Starting Orderbook HTTP Poller")
    log.info(f"Monitoring {len(WATCHLIST)} tickers")
    
    while True:
        try:
            token = get_stockbit_token()
            if not token:
                log.error("No token available, retrying in 10s...")
                time.sleep(10)
                continue
            
            log.info("📊 Polling orderbooks...")
            poll_orderbook(token)
            log.info(f"✅ Poll complete. Sleeping {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            log.error(f"Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
