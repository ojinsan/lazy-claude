import unittest

from tools.trader.l4_synth import get_tick, round_to_tick, size_plan, TIER, BP_SINGLE_NAME_CAP


class GetTickTest(unittest.TestCase):
    def test_band_lt_200(self):
        self.assertEqual(get_tick(0), 1)
        self.assertEqual(get_tick(150), 1)
        self.assertEqual(get_tick(199), 1)

    def test_band_200_500(self):
        self.assertEqual(get_tick(200), 2)
        self.assertEqual(get_tick(350), 2)
        self.assertEqual(get_tick(499), 2)

    def test_band_500_2000(self):
        self.assertEqual(get_tick(500), 5)
        self.assertEqual(get_tick(1870), 5)
        self.assertEqual(get_tick(1999), 5)

    def test_band_2000_5000(self):
        self.assertEqual(get_tick(2000), 10)
        self.assertEqual(get_tick(3500), 10)
        self.assertEqual(get_tick(4999), 10)

    def test_band_ge_5000(self):
        self.assertEqual(get_tick(5000), 25)
        self.assertEqual(get_tick(12500), 25)
        self.assertEqual(get_tick(100000), 25)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            get_tick(-5)


class RoundToTickBuyTest(unittest.TestCase):
    def test_buy_entry_rounds_down(self):
        self.assertEqual(round_to_tick(1872, "buy", "entry"), 1870)
        self.assertEqual(round_to_tick(1874, "buy", "entry"), 1870)

    def test_buy_stop_rounds_down(self):
        self.assertEqual(round_to_tick(1833, "buy", "stop"), 1830)

    def test_buy_tp_rounds_up(self):
        self.assertEqual(round_to_tick(1951, "buy", "tp"), 1955)
        self.assertEqual(round_to_tick(1950, "buy", "tp"), 1950)


class RoundToTickSellTest(unittest.TestCase):
    def test_sell_entry_rounds_up(self):
        self.assertEqual(round_to_tick(1872, "sell", "entry"), 1875)

    def test_sell_stop_rounds_up(self):
        self.assertEqual(round_to_tick(1921, "sell", "stop"), 1925)

    def test_sell_tp_rounds_down(self):
        self.assertEqual(round_to_tick(1832, "sell", "tp"), 1830)


class RoundToTickEdgeTest(unittest.TestCase):
    def test_exact_tick_noop(self):
        self.assertEqual(round_to_tick(1870, "buy", "entry"), 1870)
        self.assertEqual(round_to_tick(1870, "sell", "entry"), 1870)

    def test_band_crossover_200(self):
        self.assertEqual(round_to_tick(201, "buy", "entry"), 200)
        self.assertEqual(round_to_tick(201, "sell", "entry"), 202)

    def test_band_crossover_500(self):
        self.assertEqual(round_to_tick(502, "buy", "entry"), 500)
        self.assertEqual(round_to_tick(502, "sell", "entry"), 505)

    def test_band_crossover_2000(self):
        self.assertEqual(round_to_tick(2003, "buy", "entry"), 2000)
        self.assertEqual(round_to_tick(2003, "sell", "entry"), 2010)

    def test_band_crossover_5000(self):
        self.assertEqual(round_to_tick(5008, "buy", "entry"), 5000)
        self.assertEqual(round_to_tick(5008, "sell", "entry"), 5025)

    def test_invalid_side_raises(self):
        with self.assertRaises(ValueError):
            round_to_tick(1000, "hold", "entry")


class SizePlanTest(unittest.TestCase):
    def test_normal_buy_risk_bound(self):
        # entry=1850, stop=1830, dist=20, BP=10M, tier=med(2%) → risk=200k, shares=10000, lots=100
        # cap: 10M * 0.30 / (1850*100) = 16 lots → cap binds
        r = size_plan(1850, 1830, 10_000_000, "med", 0)
        self.assertFalse(r.get("abort"))
        self.assertEqual(r["lots"], 16)
        self.assertEqual(r["tier"], 0.02)

    def test_normal_risk_not_bp_capped(self):
        # entry=1000, stop=990, dist=10, BP=100M, tier=low(1%) → risk=1M, shares=100000, lots=1000
        # cap: 100M * 0.30 / (1000*100) = 300 lots → cap binds
        r = size_plan(1000, 990, 100_000_000, "low", 0)
        self.assertFalse(r.get("abort"))
        self.assertEqual(r["lots"], 300)

    def test_risk_bound_not_cap(self):
        # entry=100, stop=50, dist=50, BP=100M, tier=low(1%) → risk=1M, shares=20k, lots=200
        # cap: 100M*0.30 / (100*100) = 3000 lots → risk binds, lots=200
        r = size_plan(100, 50, 100_000_000, "low", 0)
        self.assertEqual(r["lots"], 200)
        self.assertEqual(r["notional"], 2_000_000)
        self.assertEqual(r["risk_idr"], 1_000_000)

    def test_notch_shrinks_high_to_med(self):
        r = size_plan(1850, 1830, 10_000_000, "high", intraday_notch=-1)
        self.assertEqual(r["tier"], 0.02)

    def test_notch_shrinks_med_to_low(self):
        r = size_plan(1850, 1830, 10_000_000, "med", intraday_notch=-1)
        self.assertEqual(r["tier"], 0.01)

    def test_notch_floor_1pct(self):
        r = size_plan(1850, 1830, 10_000_000, "low", intraday_notch=-1)
        self.assertEqual(r["tier"], 0.01)

    def test_positive_notch_no_shrink(self):
        r = size_plan(1850, 1830, 10_000_000, "med", intraday_notch=0)
        self.assertEqual(r["tier"], 0.02)

    def test_off_aborts(self):
        r = size_plan(1850, 1830, 10_000_000, "off", 0)
        self.assertTrue(r["abort"])
        self.assertIn("off", r["reason"])

    def test_empty_aggressiveness_aborts(self):
        r = size_plan(1850, 1830, 10_000_000, "", 0)
        self.assertTrue(r["abort"])

    def test_zero_bp_aborts(self):
        r = size_plan(1850, 1830, 0, "med", 0)
        self.assertTrue(r["abort"])
        self.assertIn("buying_power", r["reason"])

    def test_zero_dist_aborts(self):
        r = size_plan(1850, 1850, 10_000_000, "med", 0)
        self.assertTrue(r["abort"])
        self.assertIn("zero", r["reason"])

    def test_sub_lot_aborts(self):
        # entry=50000, stop=49999, dist=1, BP=100k, tier=low(1%) → risk=1000, shares=1000, lots=10
        # cap: 100k * 0.30 / (50000*100) = 0 → sub-lot
        r = size_plan(50000, 49999, 100_000, "low", 0)
        self.assertTrue(r["abort"])
        self.assertIn("sub-lot", r["reason"])

    def test_case_insensitive_tier(self):
        r = size_plan(1850, 1830, 10_000_000, "HIGH", 0)
        self.assertEqual(r["tier"], 0.03)

    def test_sell_side_same_math(self):
        r = size_plan(1850, 1870, 10_000_000, "med", 0, side="sell")
        self.assertFalse(r.get("abort"))
        self.assertGreater(r["lots"], 0)


if __name__ == "__main__":
    unittest.main()
