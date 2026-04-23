import unittest
from tools.trader import bid_offer_patterns as bop


class TestAnalyzeNearBook(unittest.TestCase):

    def test_spike_pattern(self):
        bids   = [{"price": 1855, "lot": 100}] + [{"price": 1850 - i*5, "lot": 1000} for i in range(6)]
        offers = [{"price": 1860, "lot": 400}] + [{"price": 1865 + i*5, "lot": 1500} for i in range(6)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertEqual(out["pattern"], "spike")
        self.assertGreaterEqual(out["level_1_ratio"], 3.0)

    def test_gradient_pattern(self):
        bids   = [{"price": 1855 - i*5, "lot": 500} for i in range(7)]
        offers = [{"price": 1860 + i*5, "lot": 500 * (i+1)} for i in range(7)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertEqual(out["pattern"], "gradient")

    def test_normal_pattern(self):
        bids   = [{"price": 1855 - i*5, "lot": 1000} for i in range(7)]
        offers = [{"price": 1860 + i*5, "lot": 1000} for i in range(7)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertEqual(out["pattern"], "normal")

    def test_retail_scared_true(self):
        bids   = [{"price": 1855, "lot": 100}, {"price": 1850, "lot": 150}, {"price": 1845, "lot": 100},
                  {"price": 1840, "lot": 800}, {"price": 1835, "lot": 700}, {"price": 1830, "lot": 900}, {"price": 1825, "lot": 600}]
        offers = [{"price": 1860 + i*5, "lot": 500} for i in range(7)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertTrue(out["retail_scared"])

    def test_retail_scared_false(self):
        bids   = [{"price": 1855 - i*5, "lot": 1000} for i in range(7)]
        offers = [{"price": 1860 + i*5, "lot": 500} for i in range(7)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertFalse(out["retail_scared"])

    def test_zero_bid_lot_no_div_by_zero(self):
        bids   = [{"price": 1855, "lot": 0}] + [{"price": 1850 - i*5, "lot": 100} for i in range(6)]
        offers = [{"price": 1860 + i*5, "lot": 200} for i in range(7)]
        out = bop.analyze_near_book(bids, offers, n=7)
        self.assertEqual(out["ratios"][0], 999)


class TestWallWithdrawn(unittest.TestCase):

    def test_large_offer_withdrawn_true(self):
        prev = {"1880": 15000}
        now  = {"1880": 0}
        self.assertTrue(bop.wall_withdrawn(prev, now, threshold_lot=5000))

    def test_offer_partially_reduced_below_threshold(self):
        prev = {"1880": 15000}
        now  = {"1880": 12000}
        self.assertFalse(bop.wall_withdrawn(prev, now, threshold_lot=5000))

    def test_offer_unchanged_false(self):
        prev = {"1880": 15000}
        now  = {"1880": 15000}
        self.assertFalse(bop.wall_withdrawn(prev, now, threshold_lot=5000))

    def test_multi_level_any_withdrawn_true(self):
        prev = {"1880": 3000, "1885": 15000}
        now  = {"1880": 3000, "1885": 0}
        self.assertTrue(bop.wall_withdrawn(prev, now, threshold_lot=5000))

    def test_missing_level_in_now_counts_as_withdrawn(self):
        prev = {"1880": 12000}
        now  = {}
        self.assertTrue(bop.wall_withdrawn(prev, now, threshold_lot=5000))


if __name__ == "__main__":
    unittest.main()
