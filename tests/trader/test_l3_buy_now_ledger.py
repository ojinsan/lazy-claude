import tempfile
import unittest
from unittest.mock import patch
from datetime import date

from tools.trader import l3_buy_now_ledger


class TestL3BuyNowLedger(unittest.TestCase):

    def test_load_missing_file_empty_set(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(l3_buy_now_ledger, "LEDGER_DIR", d):
                self.assertEqual(l3_buy_now_ledger.load(date(2026, 4, 22)), set())

    def test_record_then_load(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(l3_buy_now_ledger, "LEDGER_DIR", d):
                l3_buy_now_ledger.record("ADMR", d=date(2026, 4, 22))
                self.assertEqual(l3_buy_now_ledger.load(date(2026, 4, 22)), {"ADMR"})

    def test_record_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(l3_buy_now_ledger, "LEDGER_DIR", d):
                l3_buy_now_ledger.record("ADMR", d=date(2026, 4, 22))
                l3_buy_now_ledger.record("ADMR", d=date(2026, 4, 22))
                self.assertEqual(l3_buy_now_ledger.load(date(2026, 4, 22)), {"ADMR"})

    def test_record_multiple_tickers(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(l3_buy_now_ledger, "LEDGER_DIR", d):
                l3_buy_now_ledger.record("ADMR", d=date(2026, 4, 22))
                l3_buy_now_ledger.record("BUMI", d=date(2026, 4, 22))
                self.assertEqual(l3_buy_now_ledger.load(date(2026, 4, 22)), {"ADMR", "BUMI"})

    def test_different_dates_isolated(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(l3_buy_now_ledger, "LEDGER_DIR", d):
                l3_buy_now_ledger.record("ADMR", d=date(2026, 4, 22))
                self.assertEqual(l3_buy_now_ledger.load(date(2026, 4, 23)), set())


if __name__ == "__main__":
    unittest.main()
