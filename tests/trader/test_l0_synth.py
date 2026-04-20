import json
import os
import unittest
from pathlib import Path

from tools._lib import current_trade as ct
from tools.trader import l0_synth

FIXTURES = Path(__file__).parent / "fixtures" / "l0"


def _load(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


class BalanceFromCashTest(unittest.TestCase):
    def test_parses_cash_and_buying_power(self):
        resp = _load("carina_cash.json")
        balance = l0_synth.balance_from_cash(resp)
        self.assertIsInstance(balance, ct.Balance)
        self.assertEqual(balance.cash, 19612924.64)
        self.assertEqual(balance.buying_power, 19612924.64)


class HoldingsFromPositionsTest(unittest.TestCase):
    def test_parses_each_position_into_holding(self):
        resp = _load("carina_positions.json")
        holdings = l0_synth.holdings_from_positions(resp)
        self.assertEqual(len(holdings), 2)

        admr = next(h for h in holdings if h.ticker == "ADMR")
        self.assertEqual(admr.lot, 40)
        self.assertEqual(admr.avg_price, 1950.0)
        self.assertEqual(admr.current_price, 1940.0)
        self.assertAlmostEqual(admr.pnl_pct, -0.51)
        self.assertEqual(admr.details, "")

        impc = next(h for h in holdings if h.ticker == "IMPC")
        self.assertEqual(impc.lot, 20)
        self.assertAlmostEqual(impc.pnl_pct, 4.17)
