import datetime as dt
import os
import tempfile
import unittest

from tools._lib import current_trade as ct_mod
from tools.trader import l3_healthcheck


def _wib(h, m=0):
    return dt.datetime(2026, 4, 22, h, m, tzinfo=dt.timezone(dt.timedelta(hours=7)))


class TestL3Healthcheck(unittest.TestCase):

    def test_market_hours_ok(self):
        ct = ct_mod.CurrentTrade()
        ct.trader_status.holdings.append(ct_mod.Holding(ticker="ADMR", lot=10, avg_price=1855, current_price=1860, pnl_pct=0.27))
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ob"))
            out = l3_healthcheck.check(ct, now_wib=_wib(12, 10), orderbook_state_dir=os.path.join(d, "ob"))
        self.assertTrue(out["ok"], out.get("reason"))

    def test_pre_open_rejects(self):
        ct = ct_mod.CurrentTrade()
        ct.trader_status.holdings.append(ct_mod.Holding(ticker="ADMR", lot=10, avg_price=1855, current_price=1860, pnl_pct=0.27))
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ob"))
            out = l3_healthcheck.check(ct, now_wib=_wib(8, 30), orderbook_state_dir=os.path.join(d, "ob"))
        self.assertFalse(out["ok"])
        self.assertIn("market closed", out["reason"].lower())

    def test_post_close_rejects(self):
        ct = ct_mod.CurrentTrade()
        ct.trader_status.holdings.append(ct_mod.Holding(ticker="ADMR", lot=10, avg_price=1855, current_price=1860, pnl_pct=0.27))
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ob"))
            out = l3_healthcheck.check(ct, now_wib=_wib(16, 0), orderbook_state_dir=os.path.join(d, "ob"))
        self.assertFalse(out["ok"])

    def test_empty_universe_rejects(self):
        ct = ct_mod.CurrentTrade()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ob"))
            out = l3_healthcheck.check(ct, now_wib=_wib(12, 10), orderbook_state_dir=os.path.join(d, "ob"))
        self.assertFalse(out["ok"])
        self.assertIn("empty universe", out["reason"].lower())

    def test_missing_orderbook_dir_rejects(self):
        ct = ct_mod.CurrentTrade()
        ct.trader_status.holdings.append(ct_mod.Holding(ticker="ADMR", lot=10, avg_price=1855, current_price=1860, pnl_pct=0.27))
        out = l3_healthcheck.check(ct, now_wib=_wib(12, 10), orderbook_state_dir="/nonexistent/ob_dir_zzz")
        self.assertFalse(out["ok"])
        self.assertIn("tape", out["reason"].lower())


if __name__ == "__main__":
    unittest.main()
