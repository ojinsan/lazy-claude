"""Opus ↔ openclaude CLI wrapper with bidirectional fallback.

- model="opus": uses Anthropic HTTP API directly (urllib, no SDK dep).
- model="openclaude": subprocess `claude --settings .claude/settings.openclaude.json -p PROMPT`.
- Fallback on 429, 5xx, timeout, or RateLimitError.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal

from tools._lib.ratelimit import claude_api

WORKSPACE = Path(__file__).resolve().parents[2]
OPENCLAUDE_SETTINGS = WORKSPACE / ".claude" / "settings.openclaude.json"
OPUS_MODEL_ID = os.environ.get("CLAUDE_OPUS_MODEL_ID", "claude-opus-4-7")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

ModelName = Literal["opus", "openclaude"]


class ModelError(Exception):
    pass


class RateLimitError(Exception):
    pass


def _call_opus(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ModelError("ANTHROPIC_API_KEY not set")
    claude_api.acquire()
    body = json.dumps({
        "model": OPUS_MODEL_ID,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429 or e.code >= 500:
            raise RateLimitError(f"opus http {e.code}") from e
        raise ModelError(f"opus http {e.code}: {e.reason}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RateLimitError(f"opus transport: {e}") from e
    content = data.get("content", [])
    parts = [p.get("text", "") for p in content if p.get("type") == "text"]
    return "".join(parts)


def _call_openclaude(prompt: str) -> str:
    claude_api.acquire()
    try:
        proc = subprocess.run(
            ["claude", "--settings", str(OPENCLAUDE_SETTINGS), "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as e:
        raise RateLimitError("openclaude timeout") from e
    if proc.returncode != 0:
        err = (proc.stderr or "").lower()
        if "rate" in err or "429" in err or "overloaded" in err:
            raise RateLimitError(proc.stderr.strip())
        raise ModelError(f"openclaude exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


_DISPATCH_NAMES = {"opus": "_call_opus", "openclaude": "_call_openclaude"}


def _dispatch(model: ModelName):
    import sys
    mod = sys.modules[__name__]
    return getattr(mod, _DISPATCH_NAMES[model])


def run(prompt: str, model: ModelName = "opus", fallback: ModelName = "openclaude") -> str:
    try:
        return _dispatch(model)(prompt)
    except RateLimitError:
        pass
    try:
        return _dispatch(fallback)(prompt)
    except Exception as e:
        raise ModelError(f"both models failed: primary={model} fallback={fallback}: {e}") from e
