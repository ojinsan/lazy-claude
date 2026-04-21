"""Unit tests for tools/trader/l2_healthcheck.py."""
from __future__ import annotations

import datetime as dt
import pathlib
import tempfile
import unittest

from tools._lib.current_trade import (
    CurrentTrade, Lists, ListItem, TraderStatus, Holding, LayerRun,
)
from tools.trader import l2_healthcheck as hc


def _fresh_l1(minutes_ago: int = 30) -> LayerRun:
    ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).isoformat()
    return LayerRun(last_run=ts, status="ok", note="fresh")


def _stale_l1(hours_ago: int = 8) -> LayerRun:
    ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours_ago)).isoformat()
    return LayerRun(last_run=ts, status="ok", note="stale")


def _ct(watchlist=None, holdings=None, l1_run=None) -> CurrentTrade:
    ct = CurrentTrade()
    ct.lists = Lists(watchlist=watchlist or [], superlist=[], exitlist=[], filtered=[])
    ct.trader_status = TraderStatus(holdings=holdings or [])
    if l1_run is not None:
        ct.layer_runs["l1"] = l1_run
    return ct


class L2HealthcheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = pathlib.Path(self.tmp.name)
        self.hapcu = self.tmp_dir / "hapcu.json"
        self.retail = self.tmp_dir / "retail.json"
        self.hapcu.write_text('{"calcs": [{"ticker": "ADMR"}]}')
        self.retail.write_text('{"tickers": [{"ticker": "ADMR"}]}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_ok_with_watchlist_and_fresh_l1(self):
        ct = _ct(
            watchlist=[ListItem(ticker="ADMR", confidence=80)],
            l1_run=_fresh_l1(),
        )
        r = hc.check(ct, str(self.hapcu), str(self.retail))
        self.assertTrue(r["ok"], r)

    def test_ok_with_holdings_only(self):
        ct = _ct(
            holdings=[Holding(ticker="BUMI", lot=100, avg_price=240, current_price=232, pnl_pct=-3.3)],
            l1_run=_fresh_l1(),
        )
        r = hc.check(ct, str(self.hapcu), str(self.retail))
        self.assertTrue(r["ok"], r)

    def test_fails_empty_watchlist_and_empty_holdings(self):
        ct = _ct(l1_run=_fresh_l1())
        r = hc.check(ct, str(self.hapcu), str(self.retail))
        self.assertFalse(r["ok"])
        self.assertIn("empty", r["reason"].lower())

    def test_fails_stale_l1(self):
        ct = _ct(
            watchlist=[ListItem(ticker="ADMR", confidence=80)],
            l1_run=_stale_l1(),
        )
        r = hc.check(ct, str(self.hapcu), str(self.retail))
        self.assertFalse(r["ok"])
        self.assertIn("l1", r["reason"].lower())

    def test_fails_missing_l1_run(self):
        ct = _ct(watchlist=[ListItem(ticker="ADMR", confidence=80)], l1_run=LayerRun())
        r = hc.check(ct, str(self.hapcu), str(self.retail))
        self.assertFalse(r["ok"])

    def test_fails_both_caches_missing(self):
        ct = _ct(
            watchlist=[ListItem(ticker="ADMR", confidence=80)],
            l1_run=_fresh_l1(),
        )
        r = hc.check(ct, str(self.tmp_dir / "nope1.json"), str(self.tmp_dir / "nope2.json"))
        self.assertFalse(r["ok"])
        self.assertIn("cache", r["reason"].lower())

    def test_ok_with_only_hapcu_cache(self):
        ct = _ct(
            watchlist=[ListItem(ticker="ADMR", confidence=80)],
            l1_run=_fresh_l1(),
        )
        r = hc.check(ct, str(self.hapcu), str(self.tmp_dir / "nope.json"))
        self.assertTrue(r["ok"])


if __name__ == "__main__":
    unittest.main()
