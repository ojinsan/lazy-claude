"""Token-bucket rate limiter.

Named buckets guard Stockbit and Anthropic (Opus SDK + openclaude subprocess).
"""
from __future__ import annotations

import os
import threading
import time


class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float):
        self.rate = float(rate_per_sec)
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, cost: float = 1.0) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                self._last = now
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                deficit = cost - self._tokens
                wait = deficit / self.rate
            time.sleep(wait)


def _rps_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


stockbit = TokenBucket(
    rate_per_sec=_rps_env("RATELIMIT_STOCKBIT_RPS", 5.0),
    capacity=_rps_env("RATELIMIT_STOCKBIT_BURST", 10.0),
)

claude_api = TokenBucket(
    rate_per_sec=_rps_env("RATELIMIT_CLAUDE_RPM", 10.0) / 60.0,
    capacity=_rps_env("RATELIMIT_CLAUDE_BURST", 5.0),
)
