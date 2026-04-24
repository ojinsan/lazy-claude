"""Tests for spec #7 Task 6: l5_dim_gather graceful-degrade."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.trader.l5_dim_gather import (
    gather_cash_balance,
    gather_orders,
    gather_position_detail,
)


class GatherCashBalanceTest(unittest.TestCase):

    def test_returns_buying_power(self):
        fn = lambda: {"buying_power": 15_000_000, "cash_balance": 15_000_000}
        result = gather_cash_balance(cash_balance_fn=fn)
        self.assertEqual(result, 15_000_000.0)

    def test_fallback_to_cash_balance_key(self):
        fn = lambda: {"cash_balance": 12_000_000}
        result = gather_cash_balance(cash_balance_fn=fn)
        self.assertEqual(result, 12_000_000.0)

    def test_returns_none_on_exception(self):
        def bad():
            raise ConnectionError("timeout")
        result = gather_cash_balance(cash_balance_fn=bad)
        self.assertIsNone(result)

    def test_returns_none_when_fn_returns_none(self):
        result = gather_cash_balance(cash_balance_fn=lambda: None)
        self.assertIsNone(result)

    def test_scalar_float_response(self):
        result = gather_cash_balance(cash_balance_fn=lambda: 9_500_000)
        self.assertEqual(result, 9_500_000.0)


class GatherOrdersTest(unittest.TestCase):

    def _open_order(self):
        return [{
            "order_id": "CR-12345", "stock_code": "ADMR",
            "status": "open", "shares": 5000, "price": 1855,
        }]

    def test_returns_list(self):
        fn = lambda stock_code: self._open_order()
        result = gather_orders("ADMR", orders_fn=fn)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["order_id"], "CR-12345")

    def test_returns_empty_on_exception(self):
        def bad(stock_code):
            raise ConnectionError("timeout")
        result = gather_orders("ADMR", orders_fn=bad)
        self.assertEqual(result, [])

    def test_returns_empty_if_not_list(self):
        result = gather_orders("ADMR", orders_fn=lambda stock_code: None)
        self.assertEqual(result, [])

    def test_passes_ticker_to_fn(self):
        seen = []
        def fn(stock_code):
            seen.append(stock_code)
            return []
        gather_orders("BBCA", orders_fn=fn)
        self.assertEqual(seen, ["BBCA"])


class GatherPositionDetailTest(unittest.TestCase):

    def test_returns_position(self):
        pos = {"stock_code": "ADMR", "lot": 50, "avg_price": 1855}
        result = gather_position_detail("ADMR", position_fn=lambda t: pos)
        self.assertEqual(result["lot"], 50)

    def test_returns_none_on_exception(self):
        def bad(t):
            raise RuntimeError("API down")
        result = gather_position_detail("ADMR", position_fn=bad)
        self.assertIsNone(result)

    def test_returns_none_on_empty_dict(self):
        result = gather_position_detail("ADMR", position_fn=lambda t: {})
        self.assertIsNone(result)

    def test_returns_none_on_none(self):
        result = gather_position_detail("ADMR", position_fn=lambda t: None)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
