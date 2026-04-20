import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.trader import sb_screener_retail_avoider as ra

FIX = Path(__file__).resolve().parent / "fixtures" / "l1" / "broker_activity_raw.json"


def load_retail_raw():
    with open(FIX) as f:
        return json.load(f)


def synth_smart_raw(date="2026-04-17"):
    """Smart money heavily BUYING tickers retail is DUMPING, SELLING ones retail buys."""
    return {
        "data": {
            "broker_activity_transaction": {
                "brokers_buy": [
                    {"stock_code": "ADRO", "broker_code": "CG", "date": date, "value": 60000000000, "lot": 10, "avg_price": 1, "freq": 1},
                    {"stock_code": "AADI", "broker_code": "CS", "date": date, "value": 50000000000, "lot": 10, "avg_price": 1, "freq": 1},
                    {"stock_code": "EMAS", "broker_code": "RG", "date": date, "value": 35000000000, "lot": 10, "avg_price": 1, "freq": 1},
                ],
                "brokers_sell": [
                    {"stock_code": "BBCA", "broker_code": "CC", "date": date, "value": -220000000000, "lot": -10, "avg_price": 1, "freq": 1},
                ],
            },
            "from": date, "to": date,
        }
    }


class ParseNetsTest(unittest.TestCase):
    def test_sums_buy_and_sell_values_per_ticker(self):
        raw = load_retail_raw()
        date, nets = ra.parse_nets(raw)
        self.assertEqual(date, "2026-04-17")
        self.assertAlmostEqual(nets["BBCA"], 230751955000)
        self.assertAlmostEqual(nets["ADRO"], -42255450000)

    def test_empty_payload_returns_empty_dict(self):
        date, nets = ra.parse_nets({"data": {"broker_activity_transaction": {"brokers_buy": [], "brokers_sell": []}, "from": "2026-04-17", "to": "2026-04-17"}})
        self.assertEqual(date, "2026-04-17")
        self.assertEqual(nets, {})

    def test_malformed_returns_empty(self):
        date, nets = ra.parse_nets({})
        self.assertEqual(nets, {})


class ComputeRetailAvoiderTest(unittest.TestCase):
    def test_joins_retail_sell_and_smart_buy(self):
        out = ra.compute_retail_avoider(load_retail_raw(), synth_smart_raw())
        self.assertEqual(out["date"], "2026-04-17")
        tickers = {t["ticker"]: t for t in out["tickers"]}
        self.assertIn("ADRO", tickers)
        self.assertEqual(tickers["ADRO"]["retail_net_sell"], 42255450000)
        self.assertEqual(tickers["ADRO"]["smart_net_buy"], 60000000000)
        self.assertAlmostEqual(tickers["ADRO"]["ratio"], 60000000000 / 42255450000, places=4)

    def test_excludes_tickers_without_both_sides(self):
        out = ra.compute_retail_avoider(load_retail_raw(), synth_smart_raw())
        codes = {t["ticker"] for t in out["tickers"]}
        # BBCA: retail NET BUY — excluded
        self.assertNotIn("BBCA", codes)
        # TLKM: retail buy, not in smart — excluded
        self.assertNotIn("TLKM", codes)

    def test_excludes_zero_activity(self):
        empty = {"data": {"broker_activity_transaction": {"brokers_buy": [], "brokers_sell": []}, "from": "2026-04-17", "to": "2026-04-17"}}
        out = ra.compute_retail_avoider(empty, synth_smart_raw())
        self.assertEqual(out["tickers"], [])

    def test_sorted_by_ratio_desc(self):
        out = ra.compute_retail_avoider(load_retail_raw(), synth_smart_raw())
        ratios = [t["ratio"] for t in out["tickers"]]
        self.assertEqual(ratios, sorted(ratios, reverse=True))

    def test_date_echoed_from_retail_payload(self):
        out = ra.compute_retail_avoider(load_retail_raw(), synth_smart_raw())
        self.assertEqual(out["date"], "2026-04-17")


class RunTest(unittest.TestCase):
    def test_run_calls_fetch_twice_and_composes(self):
        with patch.object(ra, "fetch_broker_activity") as m:
            m.side_effect = [load_retail_raw(), synth_smart_raw()]
            out = ra.run(date="2026-04-17")
        self.assertEqual(m.call_count, 2)
        self.assertIn("tickers", out)
        self.assertEqual(out["date"], "2026-04-17")


if __name__ == "__main__":
    unittest.main()
