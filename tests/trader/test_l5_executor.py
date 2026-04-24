"""Tests for spec #7 Task 8: l5_executor retry + idempotency key."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.trader.l5_executor import (
    place_entry, place_stop, place_tp, cancel_order, make_idempotency_key, _retry
)


def _ok(order_id="CR-12345"):
    return {"order_id": order_id, "status": "open"}


def _err(reason="insufficient_funds"):
    return {"error": reason}


# ── _retry ─────────────────────────────────────────────────────────────────

class RetryTest(unittest.TestCase):

    def test_success_first_try(self):
        calls = []
        def fn():
            calls.append(1)
            return _ok()
        result = _retry(fn, attempts=3, delays=(0, 0, 0))
        self.assertEqual(result["order_id"], "CR-12345")
        self.assertEqual(len(calls), 1)

    def test_retry_on_exception(self):
        calls = []
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionError("timeout")
            return _ok()
        result = _retry(fn, attempts=3, delays=(0, 0, 0))
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["order_id"], "CR-12345")

    def test_raises_after_all_attempts(self):
        def fn():
            raise ConnectionError("always fails")
        with self.assertRaises(ConnectionError):
            _retry(fn, attempts=3, delays=(0, 0, 0))

    def test_api_error_no_retry(self):
        calls = []
        def fn():
            calls.append(1)
            return _err("insufficient_funds")
        result = _retry(fn, attempts=3, delays=(0, 0, 0))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["error"], "insufficient_funds")


# ── place_entry ────────────────────────────────────────────────────────────

class PlaceEntryTest(unittest.TestCase):

    def _buy_fn(self):
        calls = []
        def fn(**kwargs):
            calls.append(kwargs)
            return _ok()
        return fn, calls

    def test_buy_side_calls_buy_fn(self):
        fn, calls = self._buy_fn()
        result = place_entry("ADMR", "buy", 5000, 1855, buy_fn=fn, sell_fn=None)
        self.assertEqual(result["order_id"], "CR-12345")
        self.assertEqual(calls[0]["stock_code"], "ADMR")
        self.assertEqual(calls[0]["shares"], 5000)
        self.assertEqual(calls[0]["price"], 1855)
        self.assertEqual(calls[0]["order_type"], "LIMIT_DAY")

    def test_sell_side_calls_sell_fn(self):
        calls = []
        def sell_fn(**kwargs):
            calls.append(kwargs)
            return _ok("CR-12347")
        result = place_entry("ADMR", "sell", 5000, 1900,
                             buy_fn=lambda **k: _ok(), sell_fn=sell_fn)
        self.assertEqual(result["order_id"], "CR-12347")
        self.assertEqual(calls[0]["stock_code"], "ADMR")

    def test_api_error_returned(self):
        result = place_entry("ADMR", "buy", 5000, 1855,
                             buy_fn=lambda **k: _err(), sell_fn=None)
        self.assertIn("error", result)


# ── place_stop ─────────────────────────────────────────────────────────────

class PlaceStopTest(unittest.TestCase):

    def test_buy_position_stop_uses_sell_fn(self):
        calls = []
        def sell_fn(**kwargs):
            calls.append(kwargs)
            return _ok("CR-99")
        result = place_stop("ADMR", "buy", 5000, 1830,
                            buy_fn=lambda **k: _ok(), sell_fn=sell_fn)
        self.assertEqual(result["order_id"], "CR-99")
        self.assertEqual(calls[0]["price"], 1830)

    def test_sell_position_stop_uses_buy_fn(self):
        calls = []
        def buy_fn(**kwargs):
            calls.append(kwargs)
            return _ok("CR-88")
        result = place_stop("ADMR", "sell", 5000, 1900,
                            buy_fn=buy_fn, sell_fn=lambda **k: _ok())
        self.assertEqual(result["order_id"], "CR-88")


# ── place_tp ───────────────────────────────────────────────────────────────

class PlaceTpTest(unittest.TestCase):

    def test_buy_position_tp_uses_sell_fn(self):
        calls = []
        def sell_fn(**kwargs):
            calls.append(kwargs)
            return _ok("CR-77")
        result = place_tp("ADMR", "buy", 5000, 1955,
                          buy_fn=lambda **k: _ok(), sell_fn=sell_fn)
        self.assertEqual(result["order_id"], "CR-77")
        self.assertEqual(calls[0]["price"], 1955)


# ── cancel_order ───────────────────────────────────────────────────────────

class CancelOrderTest(unittest.TestCase):

    def test_cancel_calls_fn(self):
        calls = []
        def fn(**kwargs):
            calls.append(kwargs)
            return {"cancelled": True}
        result = cancel_order("CR-12345", cancel_fn=fn)
        self.assertTrue(result["cancelled"])
        self.assertEqual(calls[0]["order_id"], "CR-12345")

    def test_retry_on_exception(self):
        calls = []
        def fn(**kwargs):
            calls.append(1)
            if len(calls) < 2:
                raise TimeoutError("network")
            return {"cancelled": True}
        result = cancel_order("CR-x", cancel_fn=fn)
        self.assertTrue(result["cancelled"])
        self.assertEqual(len(calls), 2)


# ── make_idempotency_key ───────────────────────────────────────────────────

class IdempotencyKeyTest(unittest.TestCase):

    def test_same_inputs_same_key(self):
        k1 = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        k2 = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        self.assertEqual(k1, k2)

    def test_different_leg_different_key(self):
        k1 = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        k2 = make_idempotency_key("ADMR", "stop", "2026-04-24T06:00:00+07:00")
        self.assertNotEqual(k1, k2)

    def test_different_plan_timestamp_different_key(self):
        k1 = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        k2 = make_idempotency_key("ADMR", "entry", "2026-04-24T07:00:00+07:00")
        self.assertNotEqual(k1, k2)

    def test_different_ticker_different_key(self):
        k1 = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        k2 = make_idempotency_key("BBCA", "entry", "2026-04-24T06:00:00+07:00")
        self.assertNotEqual(k1, k2)

    def test_key_contains_components(self):
        k = make_idempotency_key("ADMR", "entry", "2026-04-24T06:00:00+07:00")
        self.assertIn("ADMR", k)
        self.assertIn("entry", k)


if __name__ == "__main__":
    unittest.main()
