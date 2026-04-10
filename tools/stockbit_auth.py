"""
Stockbit Auto-Login Trigger
============================
Detects 401 Unauthorized and triggers login refresh via scrapper_client.

Usage:
    from skills.stockbit_auth import ensure_stockbit_token, StockbitAuthError
    
    try:
        ensure_stockbit_token()
    except StockbitAuthError as e:
        print(f"Login failed: {e}")
"""

import subprocess
import json
import time
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def _first_existing_dir(*paths: str) -> Path:
    for raw in paths:
        p = Path(raw).expanduser()
        if p.exists():
            return p
    return Path(paths[0]).expanduser()


# Paths
SCRAPPER_DIR = _first_existing_dir(
    "/home/lazywork/bitstock/scrapper_client",
    "/home/lazywork/Documents/reference-only-dont-use/bitstock/scrapper_client",
)
STOCKBIT_DIR = SCRAPPER_DIR / "stockbit"
TOKEN_CACHE = STOCKBIT_DIR / "token_cache.json"
WATERSEVEN_TOKEN = Path("/home/lazywork/bitstock/waterseven/stockbit_token.json")
LAZYBOY_TOKEN = Path("/home/lazywork/lazyboy/trade/data/stockbit_token.json")

# Login cooldown (don't spam login attempts)
LOGIN_COOLDOWN_SEC = 60
_last_login_attempt = 0


class StockbitAuthError(Exception):
    """Raised when Stockbit authentication fails."""
    pass


def read_token_cache() -> Optional[dict]:
    """Read token from cache files (priority: lazyboy > waterseven > scrapper)."""
    for path in [LAZYBOY_TOKEN, WATERSEVEN_TOKEN, TOKEN_CACHE]:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if data.get("token"):
                    return data
            except:
                continue
    return None


def is_token_valid(cache: dict, skew_ms: int = 300000) -> bool:
    """Check if token is still valid (with 5 min skew)."""
    expires_at = cache.get("expires_at", cache.get("expiresAt", 0))
    if not expires_at:
        return False
    return time.time() * 1000 < (expires_at - skew_ms)


def trigger_node_login() -> bool:
    """
    Trigger login via Node.js scrapper_client.
    
    Returns True if login successful, False otherwise.
    """
    global _last_login_attempt
    
    # Cooldown check
    now = time.time()
    if now - _last_login_attempt < LOGIN_COOLDOWN_SEC:
        log.warning(f"Login cooldown active, wait {LOGIN_COOLDOWN_SEC - int(now - _last_login_attempt)}s")
        return False
    
    _last_login_attempt = now
    
    log.info("🔄 Triggering Stockbit login via scrapper_client...")
    
    try:
        # Run the login command
        result = subprocess.run(
            ["node", "main.js", "--login-only"],
            cwd=str(STOCKBIT_DIR),
            capture_output=True,
            text=True,
            timeout=120,  # 2 min timeout
            env={
                **dict(os.environ),
                "STOCKBIT_HEADLESS": "true",
            }
        )
        
        if result.returncode == 0:
            log.info("✅ Login successful")
            return True
        else:
            log.error(f"❌ Login failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log.error("❌ Login timeout (120s)")
        return False
    except Exception as e:
        log.error(f"❌ Login error: {e}")
        return False


def ensure_stockbit_token(force: bool = False) -> str:
    """
    Ensure we have a valid Stockbit token.
    
    Checks cache first, triggers login if expired/missing.
    
    Args:
        force: Force login even if token appears valid
        
    Returns:
        Valid token string
        
    Raises:
        StockbitAuthError: If login fails
    """
    # Check cache
    cache = read_token_cache()
    
    if cache and not force:
        if is_token_valid(cache):
            return cache["token"]
        else:
            log.warning("Token expired, refreshing...")
    
    # Need to login
    success = trigger_node_login()
    
    if not success:
        raise StockbitAuthError("Failed to refresh Stockbit token")
    
    # Read new token
    cache = read_token_cache()
    if not cache or not cache.get("token"):
        raise StockbitAuthError("Token not found after login")
    
    return cache["token"]


def handle_401_unauthorized():
    """
    Call this when you get 401 from Stockbit API.
    
    Triggers token refresh and returns new token.
    """
    log.warning("🔐 401 Unauthorized - refreshing token...")
    return ensure_stockbit_token(force=True)


# ─── Decorator for auto-retry on 401 ────────────────────────────────────────

def with_auth_retry(func):
    """
    Decorator that auto-retries on 401 Unauthorized.
    
    Usage:
        @with_auth_retry
        def call_stockbit_api():
            # ... make API call ...
            pass
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if 401
            if "401" in str(e) or "Unauthorized" in str(e):
                log.warning("Got 401, attempting auth refresh...")
                try:
                    handle_401_unauthorized()
                    # Retry the function
                    return func(*args, **kwargs)
                except StockbitAuthError:
                    raise
            else:
                raise
    return wrapper


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    print("🔑 Stockbit Auth Utility")
    print()
    
    # Check current token
    cache = read_token_cache()
    if cache:
        token = cache.get("token", "")
        valid = is_token_valid(cache)
        status = "✅ VALID" if valid else "❌ EXPIRED"
        print(f"Token: {token[:30]}... {status}")
    else:
        print("Token: ❌ NOT FOUND")
    
    print()
    
    # If --refresh flag, trigger login
    if "--refresh" in sys.argv:
        print("Refreshing token...")
        try:
            new_token = ensure_stockbit_token(force=True)
            print(f"✅ New token: {new_token[:30]}...")
        except StockbitAuthError as e:
            print(f"❌ Failed: {e}")
