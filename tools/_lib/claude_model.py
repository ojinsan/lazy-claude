"""Opus ↔ openclaude CLI wrapper with bidirectional fallback.

- model="opus": subprocess `claude -p PROMPT --model opus` — uses Boss's Claude
  Code subscription (OAuth). No ANTHROPIC_API_KEY needed. --settings deliberately
  omitted so the default user auth path is used.
- model="openclaude": subprocess `claude --settings .claude/settings.openclaude.json -p PROMPT` — routes
  to the local proxy (gpt-5.x) via ANTHROPIC_BASE_URL override.
- Fallback on 429, overload, timeout, or RateLimitError.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal

from tools._lib.ratelimit import claude_api

# Strip vars that block nested claude invocations (set by parent Claude Code session).
_BLOCKED_ENV_VARS = {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH"}

def _clean_env() -> dict:
    return {k: v for k, v in os.environ.items() if k not in _BLOCKED_ENV_VARS}

WORKSPACE = Path(__file__).resolve().parents[2]
OPENCLAUDE_SETTINGS = WORKSPACE / ".claude" / "settings.openclaude.json"
OPUS_MODEL_ALIAS = os.environ.get("CLAUDE_OPUS_MODEL_ALIAS", "sonnet")

# Resolve full path at import time so cron/subprocess contexts without ~/.local/bin on PATH work.
_CLAUDE_BIN = shutil.which("claude") or "/home/lazywork/.local/bin/claude"

ModelName = Literal["opus", "openclaude"]


class ModelError(Exception):
    pass


class RateLimitError(Exception):
    pass


def _call_opus(prompt: str) -> str:
    claude_api.acquire()
    try:
        proc = subprocess.run(
            [_CLAUDE_BIN, "-p", prompt, "--model", OPUS_MODEL_ALIAS],
            capture_output=True,
            text=True,
            timeout=300,
            env=_clean_env(),
        )
    except subprocess.TimeoutExpired as e:
        raise RateLimitError("opus timeout") from e
    if proc.returncode != 0:
        err = (proc.stderr or "").lower()
        if "rate" in err or "429" in err or "overloaded" in err or "usage limit" in err:
            raise RateLimitError(proc.stderr.strip())
        raise ModelError(f"opus exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _call_openclaude(prompt: str) -> str:
    claude_api.acquire()
    try:
        proc = subprocess.run(
            [_CLAUDE_BIN, "--settings", str(OPENCLAUDE_SETTINGS), "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,
            env=_clean_env(),
        )
    except subprocess.TimeoutExpired as e:
        raise RateLimitError("openclaude timeout") from e
    if proc.returncode != 0:
        # Claude CLI emits 429/cooldown messages on stdout (not stderr) when the
        # proxy rejects the request — check both to trigger the opus fallback.
        err = ((proc.stderr or "") + (proc.stdout or "")).lower()
        if "rate" in err or "429" in err or "overloaded" in err or "cooling down" in err:
            raise RateLimitError((proc.stderr or proc.stdout).strip())
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
