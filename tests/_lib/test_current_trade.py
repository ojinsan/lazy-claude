import os
import tempfile
import unittest
from unittest.mock import patch

from tools._lib import current_trade as ct_mod


class LoadEmptyTest(unittest.TestCase):
    def test_load_returns_skeleton_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ct_mod, "LIVE_PATH", os.path.join(tmp, "current_trade.json")):
                ct = ct_mod.load()
        self.assertEqual(ct.schema_version, "1.0.0")
        self.assertEqual(ct.version, 0)
        self.assertEqual(ct.lists.filtered, [])
        self.assertEqual(ct.lists.watchlist, [])
        self.assertEqual(ct.lists.superlist, [])
        self.assertEqual(ct.lists.exitlist, [])
        self.assertEqual(ct.trader_status.sectors, [])
        self.assertEqual(ct.trader_status.holdings, [])
        self.assertEqual(ct.layer_runs["l0"].status, "pending")
        self.assertEqual(ct.layer_runs["l5"].status, "pending")


class LoadExistingTest(unittest.TestCase):
    def test_load_valid_roundtrip(self):
        import json as _json
        payload = {
            "schema_version": "1.0.0",
            "version": 7,
            "updated_at": "2026-04-19T05:30:00+07:00",
            "lists": {"filtered": [], "watchlist": [
                {"ticker": "BBCA", "confidence": 60, "current_plan": None, "details": "x"}
            ], "superlist": [], "exitlist": []},
            "trader_status": {
                "regime": "risk-on", "aggressiveness": "medium",
                "sectors": ["banking"], "narratives": [],
                "balance": {"cash": 100.0, "buying_power": 200.0},
                "pnl": {"realized": 0, "unrealized": 0, "mtd": 0, "ytd": 0},
                "holdings": [],
            },
            "layer_runs": {
                "l0": {"last_run": None, "status": "pending", "note": None},
                "l1": {"last_run": None, "status": "pending", "note": None},
                "l2": {"last_run": None, "status": "pending", "note": None},
                "l3": {"last_run": None, "status": "pending", "note": None},
                "l4": {"last_run": None, "status": "pending", "note": None},
                "l5": {"last_run": None, "status": "pending", "note": None},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "current_trade.json")
            with open(path, "w") as f:
                _json.dump(payload, f)
            with patch.object(ct_mod, "LIVE_PATH", path):
                ct = ct_mod.load()
        self.assertEqual(ct.version, 7)
        self.assertEqual(ct.lists.watchlist[0].ticker, "BBCA")
        self.assertEqual(ct.trader_status.regime, "risk-on")
        self.assertEqual(ct.trader_status.balance.cash, 100.0)

    def test_load_schema_version_mismatch_raises(self):
        import json as _json
        payload = {"schema_version": "0.9.0", "version": 1, "updated_at": None,
                   "lists": {"filtered": [], "watchlist": [], "superlist": [], "exitlist": []},
                   "trader_status": {"regime": "", "aggressiveness": "", "sectors": [], "narratives": [],
                                     "balance": {"cash": 0, "buying_power": 0},
                                     "pnl": {"realized": 0, "unrealized": 0, "mtd": 0, "ytd": 0},
                                     "holdings": []},
                   "layer_runs": {n: {"last_run": None, "status": "pending", "note": None}
                                  for n in ("l0", "l1", "l2", "l3", "l4", "l5")}}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "current_trade.json")
            with open(path, "w") as f:
                _json.dump(payload, f)
            with patch.object(ct_mod, "LIVE_PATH", path):
                with self.assertRaises(ValueError):
                    ct_mod.load()


if __name__ == "__main__":
    unittest.main()
