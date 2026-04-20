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
