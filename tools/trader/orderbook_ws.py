"""
Lazyboy Orderbook WebSocket Listener
=====================================
Real-time bid/offer streaming from Stockbit.

Based on waterseven/agent/market_data_listener.py (reference only).

Runs as background service, stores snapshots to Redis.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo
from stockbit_headers import STOCKBIT_BROWSER_HEADERS, stockbit_headers

try:
    import websockets
except ImportError:
    websockets = None

try:
    import redis
except ImportError:
    redis = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
STOCKBIT_WS_URL = "wss://wss-trading.stockbit.com/ws"

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
ORDERBOOK_KEY_PREFIX = "lazyboy:orderbook:"
ORDERBOOK_TTL = 300  # 5 minutes

# Token: use api.py local-cache loader


@dataclass
class OrderbookSnapshot:
    ticker: str
    bids: List[Dict[str, Any]] = field(default_factory=list)
    offers: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "bids": self.bids,
            "offers": self.offers,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OrderbookSnapshot":
        return cls(
            ticker=data.get("ticker", ""),
            bids=data.get("bids", []),
            offers=data.get("offers", []),
            timestamp=data.get("timestamp", 0.0),
        )


class OrderbookWSListener:
    """WebSocket listener for real-time orderbook data."""
    
    def __init__(self, tickers: List[str]):
        self.tickers = tickers
        self.ws = None
        self.token = None
        self.redis_client = None
        self.running = False
        self.last_snapshots: Dict[str, OrderbookSnapshot] = {}
        
        # Initialize Redis
        if redis:
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    decode_responses=True,
                )
                self.redis_client.ping()
                log.info("Redis connected")
            except Exception as e:
                log.warning(f"Redis not available: {e}")
                self.redis_client = None
    
    def get_token(self) -> Optional[str]:
        """Delegate to api.py local-cache loader."""
        try:
            import api as trader_api
            return trader_api.get_stockbit_token()
        except Exception as e:
            log.error(f"Failed to fetch token: {e}")
        return None
    
    def store_snapshot(self, snapshot: OrderbookSnapshot):
        """Store snapshot to Redis."""
        if self.redis_client:
            try:
                key = f"{ORDERBOOK_KEY_PREFIX}{snapshot.ticker}"
                self.redis_client.setex(
                    key,
                    ORDERBOOK_TTL,
                    json.dumps(snapshot.to_dict()),
                )
            except Exception as e:
                log.warning(f"Redis store failed: {e}")
        
        # Also store in memory
        self.last_snapshots[snapshot.ticker] = snapshot
    
    def get_snapshot(self, ticker: str) -> Optional[OrderbookSnapshot]:
        """Get latest snapshot for ticker."""
        # Try memory first
        if ticker in self.last_snapshots:
            return self.last_snapshots[ticker]
        
        # Try Redis
        if self.redis_client:
            try:
                key = f"{ORDERBOOK_KEY_PREFIX}{ticker}"
                data = self.redis_client.get(key)
                if data:
                    return OrderbookSnapshot.from_dict(json.loads(data))
            except Exception as e:
                log.warning(f"Redis read failed: {e}")
        
        return None
    
    async def connect(self):
        """Connect to Stockbit WebSocket."""
        if not websockets:
            log.error("websockets library not installed")
            return False
        
        self.token = self.get_token()
        if not self.token:
            log.error("No Stockbit token available")
            return False
        
        try:
            headers = stockbit_headers(self.token)
            self.ws = await websockets.connect(
                STOCKBIT_WS_URL,
                additional_params=headers,
                ping_interval=30,
                ping_timeout=10,
            )
            log.info("WebSocket connected")
            return True
        except Exception as e:
            log.error(f"WebSocket connection failed: {e}")
            return False
    
    async def subscribe(self):
        """Subscribe to orderbook updates for all tickers."""
        if not self.ws:
            return
        
        # Subscribe to orderbook for each ticker
        for ticker in self.tickers:
            msg = {
                "type": "subscribe",
                "channel": "orderbook",
                "symbol": ticker,
            }
            await self.ws.send(json.dumps(msg))
            log.info(f"Subscribed to {ticker} orderbook")
    
    async def handle_message(self, data: dict):
        """Handle incoming WebSocket message."""
        msg_type = data.get("type", "")
        symbol = data.get("symbol", data.get("ticker", ""))
        
        if msg_type == "orderbook" and symbol:
            # Parse orderbook data
            bids = data.get("bid", data.get("bids", []))
            offers = data.get("offer", data.get("asks", data.get("offers", [])))
            
            snapshot = OrderbookSnapshot(
                ticker=symbol,
                bids=bids[:10],  # Top 10 levels
                offers=offers[:10],
                timestamp=time.time(),
            )
            
            self.store_snapshot(snapshot)
            log.debug(f"Updated {symbol} orderbook")
    
    async def listen(self):
        """Listen for WebSocket messages."""
        if not self.ws:
            return
        
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    log.warning(f"Invalid JSON: {message[:100]}")
                except Exception as e:
                    log.error(f"Message handling error: {e}")
        except Exception as e:
            log.error(f"WebSocket listen error: {e}")
    
    async def run(self):
        """Main run loop."""
        if not await self.connect():
            return
        
        await self.subscribe()
        self.running = True
        
        while self.running:
            try:
                await self.listen()
            except Exception as e:
                log.error(f"Listen loop error: {e}")
                if self.running:
                    log.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                    if not await self.connect():
                        break
                    await self.subscribe()
    
    def stop(self):
        """Stop the listener."""
        self.running = False


def is_market_hours() -> bool:
    """Check if we're in IDX trading hours."""
    now = datetime.now(WIB)
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return 900 <= hour_min <= 1515


async def main():
    """Run the WebSocket listener."""
    # Get tickers from watchlist
    import sys
    from pathlib import Path
    
    watchlist_file = Path("/home/lazywork/workspace/vault/data/watchlist.json")
    tickers = []
    
    if watchlist_file.exists():
        data = json.loads(watchlist_file.read_text())
        tickers = [k for k in data.keys() if not k.startswith("_")]
    
    if not tickers:
        log.error("No tickers to monitor")
        return
    
    log.info(f"Monitoring {len(tickers)} tickers: {', '.join(tickers[:10])}...")
    
    listener = OrderbookWSListener(tickers)
    
    try:
        await listener.run()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        listener.stop()


if __name__ == "__main__":
    asyncio.run(main())
