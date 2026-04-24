"""Tests for spec #7 Task 7: l5_healthcheck gates."""
import sys, os, unittest, datetime as _dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools._lib.current_trade import (
    CurrentTrade, TraderStatus, Balance, Lists, ListItem,
    CurrentPlan, TradePlan, LayerRun
)
from tools.trader.l5_healthcheck import check

WIB = _dt.timezone(_dt.timedelta(hours=7))


def _ct(aggressiveness="high", bp=10_000_000, superlist=None):
    ts = TraderStatus(aggressiveness=aggressiveness,
                      balance=Balance(buying_power=bp))
    ct = CurrentTrade(trader_status=ts)
    if superlist:
        ct.lists = Lists(superlist=superlist)
    return ct


def _item(ticker="ADMR", mode="buy_at_price", plan=None):
    cp = CurrentPlan(mode=mode, price=1855)
    return ListItem(ticker=ticker, confidence=80, current_plan=cp, plan=plan)


def _plan(updated_at="2026-04-24T06:00:00+07:00"):
    return TradePlan(entry=1855, stop=1830, tp1=1955, lots=50,
                     risk_idr=100000.0, mode="A", updated_at=updated_at)


def _t(h, m=0):
    return _dt.datetime(2026, 4, 24, h, m, 0, tzinfo=WIB)


class KillSwitchTest(unittest.TestCase):

    def test_off_aborts_all_paths(self):
        ct = _ct(aggressiveness="off")
        for path in ("pre_open", "reconcile", "intraday"):
            r = check(ct, path, now=_t(8, 30))
            self.assertFalse(r["ok"])
            self.assertIn("kill-switch", r["reason"])


class PreOpenWindowTest(unittest.TestCase):

    def test_in_window(self):
        ct = _ct()
        r = check(ct, "pre_open", now=_t(8, 30))
        self.assertTrue(r["ok"])

    def test_start_boundary(self):
        r = check(_ct(), "pre_open", now=_t(8, 0))
        self.assertTrue(r["ok"])

    def test_end_boundary(self):
        r = check(_ct(), "pre_open", now=_t(8, 45))
        self.assertTrue(r["ok"])

    def test_too_early(self):
        r = check(_ct(), "pre_open", now=_t(7, 59))
        self.assertFalse(r["ok"])
        self.assertIn("08:00", r["reason"])

    def test_too_late(self):
        r = check(_ct(), "pre_open", now=_t(9, 0))
        self.assertFalse(r["ok"])

    def test_market_hours(self):
        r = check(_ct(), "pre_open", now=_t(10, 30))
        self.assertFalse(r["ok"])


class ReconcileWindowTest(unittest.TestCase):

    def test_in_window(self):
        r = check(_ct(), "reconcile", now=_t(10, 0))
        self.assertTrue(r["ok"])

    def test_start_boundary(self):
        r = check(_ct(), "reconcile", now=_t(9, 0))
        self.assertTrue(r["ok"])

    def test_end_boundary(self):
        r = check(_ct(), "reconcile", now=_t(15, 15))
        self.assertTrue(r["ok"])

    def test_too_early(self):
        r = check(_ct(), "reconcile", now=_t(8, 59))
        self.assertFalse(r["ok"])

    def test_too_late(self):
        r = check(_ct(), "reconcile", now=_t(15, 16))
        self.assertFalse(r["ok"])


class IntradayPathTest(unittest.TestCase):

    def test_valid_ticker_with_plan(self):
        item = _item(plan=_plan())
        ct = _ct(superlist=[item])
        r = check(ct, "intraday", ticker="ADMR", now=_t(10, 0))
        self.assertTrue(r["ok"])

    def test_no_ticker_arg(self):
        r = check(_ct(), "intraday", ticker=None, now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("--ticker", r["reason"])

    def test_invalid_ticker(self):
        r = check(_ct(), "intraday", ticker="admr", now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("invalid ticker", r["reason"])

    def test_ticker_not_in_lists(self):
        ct = _ct(superlist=[_item("BBCA")])
        r = check(ct, "intraday", ticker="ADMR", now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("not in", r["reason"])

    def test_no_plan(self):
        item = _item(plan=None)
        ct = _ct(superlist=[item])
        r = check(ct, "intraday", ticker="ADMR", now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("no plan", r["reason"])

    def test_stale_plan(self):
        item = _item(plan=_plan(updated_at="2026-04-22T06:00:00+07:00"))  # 2d old
        ct = _ct(superlist=[item])
        r = check(ct, "intraday", ticker="ADMR", now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("stale", r["reason"])

    def test_fresh_plan_24h_boundary(self):
        # exactly 24h old — not stale (> not >=)
        now = _t(10, 0)
        updated = now - _dt.timedelta(hours=24)
        item = _item(plan=_plan(updated_at=updated.isoformat()))
        ct = _ct(superlist=[item])
        r = check(ct, "intraday", ticker="ADMR", now=now)
        self.assertTrue(r["ok"])

    def test_slightly_over_24h_is_stale(self):
        now = _t(10, 0)
        updated = now - _dt.timedelta(hours=24, seconds=1)
        item = _item(plan=_plan(updated_at=updated.isoformat()))
        ct = _ct(superlist=[item])
        r = check(ct, "intraday", ticker="ADMR", now=now)
        self.assertFalse(r["ok"])


class TokenCheckTest(unittest.TestCase):

    def test_fresh_token(self):
        r = check(_ct(), "pre_open", now=_t(8, 30),
                  token_age_sec=600)
        self.assertTrue(r["ok"])

    def test_expired_token(self):
        r = check(_ct(), "pre_open", now=_t(8, 30),
                  token_age_sec=3700)
        self.assertFalse(r["ok"])
        self.assertIn("expired", r["reason"])

    def test_no_token_check_when_none(self):
        r = check(_ct(), "pre_open", now=_t(8, 30),
                  token_age_sec=None)
        self.assertTrue(r["ok"])


class UnknownPathTest(unittest.TestCase):

    def test_unknown(self):
        r = check(_ct(), "batch", now=_t(10, 0))
        self.assertFalse(r["ok"])
        self.assertIn("unknown path", r["reason"])


if __name__ == "__main__":
    unittest.main()
