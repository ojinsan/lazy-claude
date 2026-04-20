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


class SaveTest(unittest.TestCase):
    def test_save_bumps_version_and_updates_layer_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "current_trade.json")
            hist = os.path.join(tmp, "history")
            with patch.object(ct_mod, "LIVE_PATH", live), \
                 patch.object(ct_mod, "HISTORY_DIR", hist):
                ct = ct_mod.load()
                self.assertEqual(ct.version, 0)
                ct_mod.save(ct, layer="l0", status="ok", note="hello")
                self.assertEqual(ct.version, 1)
                self.assertEqual(ct.layer_runs["l0"].status, "ok")
                self.assertEqual(ct.layer_runs["l0"].note, "hello")
                self.assertIsNotNone(ct.layer_runs["l0"].last_run)
                self.assertIsNotNone(ct.updated_at)
                reloaded = ct_mod.load()
                self.assertEqual(reloaded.version, 1)
                self.assertEqual(reloaded.layer_runs["l0"].status, "ok")


class AtomicWriteTest(unittest.TestCase):
    def test_crash_between_tmp_and_rename_preserves_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "current_trade.json")
            hist = os.path.join(tmp, "history")
            with patch.object(ct_mod, "LIVE_PATH", live), \
                 patch.object(ct_mod, "HISTORY_DIR", hist):
                ct = ct_mod.load()
                ct.version = 5
                ct_mod._write_live(ct)
                def boom(src, dst):
                    raise OSError("crash")
                with patch.object(ct_mod.os, "replace", boom):
                    try:
                        ct.version = 99
                        ct_mod._write_live(ct)
                    except OSError:
                        pass
                reloaded = ct_mod.load()
                self.assertEqual(reloaded.version, 5)


class SnapshotTest(unittest.TestCase):
    def test_save_writes_snapshot_with_layer_and_time_in_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "current_trade.json")
            hist = os.path.join(tmp, "history")
            with patch.object(ct_mod, "LIVE_PATH", live), \
                 patch.object(ct_mod, "HISTORY_DIR", hist):
                ct = ct_mod.load()
                ct_mod.save(ct, layer="l2", status="ok", note="screening done")
            days = os.listdir(hist)
            self.assertEqual(len(days), 1)
            day = days[0]
            self.assertRegex(day, r"^\d{4}-\d{2}-\d{2}$")
            files = os.listdir(os.path.join(hist, day))
            self.assertEqual(len(files), 1)
            self.assertRegex(files[0], r"^l2-\d{4}\.json$")


class HoldingDetailsRoundTripTest(unittest.TestCase):
    def test_details_field_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            live = os.path.join(tmp, "current_trade.json")
            hist = os.path.join(tmp, "history")
            with patch.object(ct_mod, "LIVE_PATH", live), \
                 patch.object(ct_mod, "HISTORY_DIR", hist):
                ct = ct_mod.load()
                ct.trader_status.holdings.append(
                    ct_mod.Holding(
                        ticker="ADMR",
                        lot=40,
                        avg_price=1950.0,
                        current_price=1940.0,
                        pnl_pct=-0.5,
                        details="thesis-drift: supply wall unbroken 3d",
                    )
                )
                ct_mod.save(ct, layer="l0", status="ok", note="test")
                ct2 = ct_mod.load()
        self.assertEqual(len(ct2.trader_status.holdings), 1)
        self.assertEqual(
            ct2.trader_status.holdings[0].details,
            "thesis-drift: supply wall unbroken 3d",
        )


if __name__ == "__main__":
    unittest.main()
