#!/usr/bin/env python3
"""
Stockbit Auto-Login
====================
Python port of scrapper_client/stockbit/core/auth-api.js

Flow:
  POST /login/v6/username  →  known device: token returned directly
                           →  new device: phone approval required

On success: saves token to runtime/tokens/stockbit_token.json
            + pushes to backend POST /token-store/stockbit

Usage:
    python3 stockbit_login.py            # login, refresh if expired
    python3 stockbit_login.py --force    # force re-login even if valid
    python3 stockbit_login.py --status   # check token status only

Env vars required:
    STOCKBIT_USERNAME
    STOCKBIT_PASSWORD
    STOCKBIT_PLAYER_ID   (optional — auto-derived from machine-id if absent)
"""

from __future__ import annotations
import base64
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from config import load_env, stockbit_token_cache

log = logging.getLogger(__name__)

# ─── Endpoints ────────────────────────────────────────────────────────────────

LOGIN_URL        = "https://exodus.stockbit.com/login/v6/username"
PROMPT_SEND_URL  = "https://exodus.stockbit.com/login/v4/new-device/prompt/send"
PROMPT_RESULT_URL = "https://exodus.stockbit.com/mfa/v1/prompt/verified/result"
PROMPT_VERIFY_URL = "https://exodus.stockbit.com/login/v4/new-device/prompt/verify"

APPROVAL_TIMEOUT_SEC  = 5 * 60   # 5 minutes
APPROVAL_POLL_SEC     = 2

MOBILE_HEADERS = {
    "Content-Type": "application/json",
    "X-Appversion": "3.17.3",
    "X-Platform": "ios",
    "X-Devicetype": "iPhone 17 Pro",
}

TOKEN_CACHE: Path = stockbit_token_cache()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_expires_at(value) -> int:
    """Parse expired_at to Unix milliseconds. Accepts int (ms or s) or ISO string."""
    if not value:
        return 0
    if isinstance(value, (int, float)):
        v = int(value)
        return v * 1000 if v < 1e10 else v  # seconds → ms
    if isinstance(value, str):
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            pass
    return 0


def _decode_jwt_exp_ms(token: str) -> int:
    """Decode JWT expiry → Unix milliseconds (0 if undecodable)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return 0
        pad = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(pad).decode())
        exp = payload.get("exp", 0)
        return int(exp) * 1000 if exp else 0
    except Exception:
        return 0


def _is_expired(exp_ms: int, skew_ms: int = 300_000) -> bool:
    if not exp_ms:
        return False
    return time.time() * 1000 >= exp_ms - skew_ms


def _get_player_id() -> str:
    """Return stable player_id: env var > derived from machine-id."""
    pid = os.environ.get("STOCKBIT_PLAYER_ID", "").strip()
    if pid:
        return pid
    try:
        machine_id = Path("/etc/machine-id").read_text().strip()
        return str(uuid.UUID(machine_id[:32]))
    except Exception:
        return str(uuid.uuid4())


# ─── Token cache I/O ──────────────────────────────────────────────────────────

def read_token_cache() -> Optional[dict]:
    if not TOKEN_CACHE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE.read_text())
    except Exception:
        return None


def save_token_cache(data: dict) -> None:
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(data, indent=2))
    log.info(f"Token saved to {TOKEN_CACHE}")


# ─── Login flow ───────────────────────────────────────────────────────────────

def _login_with_credentials(username: str, password: str, player_id: str) -> dict:
    r = httpx.post(
        LOGIN_URL,
        headers=MOBILE_HEADERS,
        json={"user": username, "password": password, "player_id": player_id},
        timeout=30,
    )
    if not r.is_success:
        raise RuntimeError(f"Login request failed: {r.status_code} {r.text[:200]}")
    data = r.json()

    # Known device — tokens returned directly
    td = (data.get("data") or {}).get("login", {}).get("token_data")
    if td:
        return {
            "needs_approval": False,
            "access_token":   td["access"]["token"],
            "refresh_token":  td["refresh"]["token"],
            "expires_at":     _parse_expires_at(td["access"].get("expired_at")),
            "user":           (data["data"]["login"].get("user") or {}),
        }

    # Alternative flat format
    alt = (data.get("data") or {})
    if alt.get("access", {}).get("token"):
        return {
            "needs_approval": False,
            "access_token":   alt["access"]["token"],
            "refresh_token":  alt.get("refresh", {}).get("token", ""),
            "expires_at":     _parse_expires_at(alt["access"].get("expired_at")),
            "user":           alt.get("user", {}),
        }

    # New device — needs phone approval
    nd = (data.get("data") or {}).get("new_device", {}).get("trusted_device", {})
    if nd.get("login_token"):
        return {
            "needs_approval": True,
            "login_token":    nd["login_token"],
            "device_name":    nd.get("device_name", ""),
        }

    raise RuntimeError(f"Unexpected login response: {json.dumps(data)[:300]}")


def _send_approval_prompt(login_token: str) -> dict:
    r = httpx.post(
        PROMPT_SEND_URL,
        headers={"accept": "application/json", "content-type": "application/json"},
        json={"token": login_token},
        timeout=15,
    )
    data = r.json()
    pt = (data.get("data") or {}).get("prompt_token")
    if not pt:
        raise RuntimeError(f"Failed to send approval prompt: {data}")
    return {"prompt_token": pt, "target": (data.get("data") or {}).get("target", "")}


def _poll_for_approval(prompt_token: str) -> dict:
    import urllib.parse
    print(f"  Waiting for approval in Stockbit app (up to {APPROVAL_TIMEOUT_SEC}s)...")
    deadline = time.time() + APPROVAL_TIMEOUT_SEC
    encoded = urllib.parse.quote(prompt_token)
    while time.time() < deadline:
        try:
            r = httpx.get(
                f"{PROMPT_RESULT_URL}?token={encoded}",
                headers={"accept": "application/json"},
                timeout=10,
            )
            status = ((r.json().get("data") or {}).get("status", ""))
            print(f"  Poll status: {status}")
            if status == "PROMPT_STATUS_APPROVED":
                ack = (r.json()["data"].get("acknowledge_token") or "")
                return {"approved": True, "acknowledge_token": ack}
            if status == "PROMPT_STATUS_REJECTED":
                raise RuntimeError("Login request rejected on phone")
        except RuntimeError:
            raise
        except Exception as e:
            log.debug(f"Poll error: {e}")
        time.sleep(APPROVAL_POLL_SEC)
    return {"approved": False, "timed_out": True}


def _verify_approval(login_token: str, acknowledge_token: str) -> dict:
    r = httpx.post(
        PROMPT_VERIFY_URL,
        headers={"accept": "application/json", "content-type": "application/json"},
        json={"token": login_token, "acknowledge_token": acknowledge_token},
        timeout=15,
    )
    data = (r.json().get("data") or {})
    if not data.get("access", {}).get("token"):
        raise RuntimeError(f"Verification failed: {r.text[:200]}")
    return {
        "access_token":  data["access"]["token"],
        "refresh_token": data.get("refresh", {}).get("token", ""),
        "expires_at":    _parse_expires_at(data["access"].get("expired_at")),
        "user":          data.get("user", {}),
    }


# ─── Main entry ───────────────────────────────────────────────────────────────

def login(force: bool = False) -> dict:
    """
    Ensure a valid Stockbit token exists.
    Returns the token dict. Raises on failure.
    """
    load_env()

    # Check cache first
    if not force:
        cached = read_token_cache()
        if cached:
            exp = cached.get("expires_at", cached.get("expiresAt", 0))
            if exp and not _is_expired(exp):
                log.info("Cached token still valid — skipping login")
                return cached
            log.info("Cached token expired — re-logging in")

    username  = os.environ.get("STOCKBIT_USERNAME", "").strip()
    password  = os.environ.get("STOCKBIT_PASSWORD", "").strip()
    player_id = _get_player_id()

    if not username or not password:
        raise RuntimeError("STOCKBIT_USERNAME and STOCKBIT_PASSWORD must be set in .env.local")

    print(f"[stockbit_login] Logging in as {username} (player_id={player_id[:8]}...)")

    result = _login_with_credentials(username, password, player_id)

    if result.get("needs_approval"):
        print("[stockbit_login] New device detected — sending approval to phone...")
        prompt = _send_approval_prompt(result["login_token"])
        print(f"[stockbit_login] Approval prompt sent to: {prompt['target']}")

        approval = _poll_for_approval(prompt["prompt_token"])
        if not approval.get("approved"):
            raise RuntimeError("Device approval timed out — approve in Stockbit app and retry")

        result = _verify_approval(result["login_token"], approval["acknowledge_token"])

    exp_ms = result.get("expires_at", 0) or _decode_jwt_exp_ms(result["access_token"]) or int((time.time() + 86400 * 30) * 1000)

    token_data = {
        "token":         result["access_token"],
        "refresh_token": result.get("refresh_token", ""),
        "expires_at":    exp_ms,
        "user":          result.get("user", {}),
    }

    save_token_cache(token_data)

    exp_str = time.strftime("%Y-%m-%d %H:%M WIB", time.localtime(exp_ms / 1000))
    print(f"[stockbit_login] Login successful. Token expires: {exp_str}")
    return token_data


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = set(sys.argv[1:])

    if "--status" in args:
        load_env()
        cached = read_token_cache()
        if not cached:
            print("No token cache found")
            sys.exit(1)
        exp = cached.get("expires_at", 0)
        expired = _is_expired(exp) if exp else True
        user = cached.get("user", {})
        print(json.dumps({
            "token_prefix":  cached.get("token", "")[:30] + "...",
            "expires_at_ms": exp,
            "expires_human": time.strftime("%Y-%m-%d %H:%M", time.localtime(exp / 1000)) if exp else "unknown",
            "expired":       expired,
            "user":          user.get("username") or user.get("email") or "(unknown)",
        }, indent=2))
        sys.exit(0 if not expired else 1)

    force = "--force" in args
    try:
        login(force=force)
    except Exception as e:
        print(f"[stockbit_login] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
