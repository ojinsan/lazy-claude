import unittest

from tools.trader.l4_synth import get_tick, round_to_tick


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


if __name__ == "__main__":
    unittest.main()
