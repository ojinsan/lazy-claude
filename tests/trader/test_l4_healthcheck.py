import unittest
from datetime import datetime, timezone, timedelta

from tools._lib.current_trade import (
    CurrentTrade, ListItem, CurrentPlan, TradePlan, TraderStatus, Balance, Lists,
)
from tools.trader.l4_healthcheck import check

WIB = timezone(timedelta(hours=7))
NOW = datetime(2026, 4, 22, 10, 0, 0, tzinfo=WIB)
TODAY_ISO = NOW.isoformat()
YDAY_ISO = (NOW.replace(day=21)).isoformat()


def _ct(
    aggressiveness="med",
    bp=100_000_000,
    superlist=None,
    exitlist=None,
):
    ct = CurrentTrade()
    ct.trader_status = TraderStatus(
        aggressiveness=aggressiveness,
        balance=Balance(cash=bp, buying_power=bp),
    )
    ct.lists = Lists(
        superlist=list(superlist or []),
        exitlist=list(exitlist or []),
    )
    return ct


def _item(ticker, mode="buy_at_price", price=1850, plan=None, details=""):
    return ListItem(
        ticker=ticker,
        confidence=80,
        current_plan=CurrentPlan(mode=mode, price=price),
        details=details,
        plan=plan,
    )


class HealthCheckSingleTest(unittest.TestCase):
    def test_aggressiveness_off_aborts(self):
        ct = _ct(aggressiveness="off", superlist=[_item("ADMR")])
        r = check(ct, mode="A", ticker="ADMR", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("kill-switch", r["reason"])

    def test_invalid_ticker_aborts(self):
        ct = _ct(superlist=[_item("ADMR")])
        r = check(ct, mode="B", ticker="foo!", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("invalid", r["reason"])

    def test_lowercase_ticker_aborts(self):
        ct = _ct(superlist=[_item("ADMR")])
        r = check(ct, mode="B", ticker="admr", now=NOW)
        self.assertFalse(r["ok"])

    def test_not_in_lists_aborts(self):
        ct = _ct(superlist=[_item("ADMR")])
        r = check(ct, mode="B", ticker="BUMI", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("not in", r["reason"])

    def test_wait_bid_offer_aborts(self):
        ct = _ct(superlist=[_item("ADMR", mode="wait_bid_offer")])
        r = check(ct, mode="B", ticker="ADMR", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("wait_bid_offer", r["reason"])

    def test_duplicate_same_mode_today_aborts(self):
        plan = TradePlan(entry=1850, stop=1830, tp1=1950, lots=50, mode="A", updated_at=TODAY_ISO)
        ct = _ct(superlist=[_item("ADMR", plan=plan)])
        r = check(ct, mode="A", ticker="ADMR", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("duplicate", r["reason"])

    def test_duplicate_yesterday_allowed(self):
        plan = TradePlan(entry=1850, stop=1830, tp1=1950, lots=50, mode="A", updated_at=YDAY_ISO)
        ct = _ct(superlist=[_item("ADMR", plan=plan)])
        r = check(ct, mode="A", ticker="ADMR", now=NOW)
        self.assertTrue(r["ok"])

    def test_duplicate_different_mode_allowed(self):
        plan = TradePlan(entry=1850, stop=1830, tp1=1950, lots=50, mode="A", updated_at=TODAY_ISO)
        ct = _ct(superlist=[_item("ADMR", plan=plan)])
        r = check(ct, mode="B", ticker="ADMR", now=NOW)
        self.assertTrue(r["ok"])

    def test_buy_bp_zero_aborts(self):
        ct = _ct(bp=0, superlist=[_item("ADMR")])
        r = check(ct, mode="B", ticker="ADMR", now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("buying_power", r["reason"])

    def test_sell_bp_zero_ok(self):
        ct = _ct(bp=0, exitlist=[_item("BUMI", mode="sell_at_price")])
        r = check(ct, mode="A", ticker="BUMI", now=NOW)
        self.assertTrue(r["ok"])

    def test_single_happy_path(self):
        ct = _ct(superlist=[_item("ADMR")])
        r = check(ct, mode="B", ticker="ADMR", now=NOW)
        self.assertTrue(r["ok"])
        self.assertEqual(r["ticker"], "ADMR")


class HealthCheckBatchTest(unittest.TestCase):
    def test_batch_builds_queue(self):
        ct = _ct(superlist=[
            _item("ADMR", mode="buy_at_price"),
            _item("BBCA", mode="wait_bid_offer"),
            _item("TLKM", mode="buy_at_price"),
        ], exitlist=[_item("BUMI", mode="sell_at_price")])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertTrue(r["ok"])
        self.assertEqual(set(r["queue"]), {"ADMR", "TLKM", "BUMI"})

    def test_batch_skips_already_planned_today(self):
        plan = TradePlan(entry=1850, stop=1830, tp1=1950, lots=50, mode="A", updated_at=TODAY_ISO)
        ct = _ct(superlist=[
            _item("ADMR", plan=plan),
            _item("TLKM"),
        ])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertEqual(r["queue"], ["TLKM"])

    def test_batch_empty_aborts(self):
        ct = _ct(superlist=[_item("BBCA", mode="wait_bid_offer")])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("empty queue", r["reason"])

    def test_batch_buy_bp_zero_aborts(self):
        ct = _ct(bp=0, superlist=[_item("ADMR", mode="buy_at_price")])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertFalse(r["ok"])
        self.assertIn("buying_power", r["reason"])

    def test_batch_sell_only_bp_zero_ok(self):
        ct = _ct(bp=0, exitlist=[_item("BUMI", mode="sell_at_price")])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertTrue(r["ok"])
        self.assertEqual(r["queue"], ["BUMI"])

    def test_batch_aggressiveness_off_aborts(self):
        ct = _ct(aggressiveness="off", superlist=[_item("ADMR")])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertFalse(r["ok"])

    def test_batch_plan_yesterday_included(self):
        plan = TradePlan(entry=1850, stop=1830, tp1=1950, lots=50, mode="A", updated_at=YDAY_ISO)
        ct = _ct(superlist=[_item("ADMR", plan=plan)])
        r = check(ct, mode="A", ticker=None, now=NOW)
        self.assertEqual(r["queue"], ["ADMR"])


if __name__ == "__main__":
    unittest.main()
