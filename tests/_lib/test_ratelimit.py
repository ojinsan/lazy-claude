import time
import unittest

from tools._lib.ratelimit import TokenBucket


class TokenBucketTest(unittest.TestCase):
    def test_acquire_returns_immediately_when_token_available(self):
        b = TokenBucket(rate_per_sec=10, capacity=10)
        start = time.monotonic()
        for _ in range(5):
            b.acquire()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.05)

    def test_acquire_blocks_when_empty(self):
        b = TokenBucket(rate_per_sec=5, capacity=1)
        b.acquire()
        start = time.monotonic()
        b.acquire()
        elapsed = time.monotonic() - start
        self.assertGreaterEqual(elapsed, 0.15)
        self.assertLess(elapsed, 0.5)

    def test_named_buckets_exist(self):
        from tools._lib import ratelimit
        self.assertTrue(hasattr(ratelimit, "stockbit"))
        self.assertTrue(hasattr(ratelimit, "claude_api"))


if __name__ == "__main__":
    unittest.main()
