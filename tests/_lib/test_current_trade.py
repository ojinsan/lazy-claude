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


if __name__ == "__main__":
    unittest.main()
