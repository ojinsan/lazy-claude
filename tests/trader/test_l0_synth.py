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


import datetime as dt
from tools._lib.current_trade import PnL


class PnLRollupFromOrdersTest(unittest.TestCase):
    def test_sums_filled_sells_in_current_month_for_mtd(self):
        resp = _load("carina_orders.json")
        # today = 2026-04-20 → April window
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=0.0, ytd=0.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        # Only the 2026-04-15 BUMI sell counts for MtD (-125000).
        self.assertEqual(pnl.mtd, -125000.0)
        # YtD = MtD + 2026-03-20 AADI sell (1325000) = 1200000.
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_empty_window_falls_back_to_prior_values(self):
        resp = {"orders": []}
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=-250000.0, ytd=1200000.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        self.assertEqual(pnl.mtd, -250000.0)
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_cancelled_orders_excluded(self):
        resp = _load("carina_orders.json")
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=0.0, ytd=0.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        # Cancelled ADMR order on 2026-04-18 must not change MtD.
        self.assertEqual(pnl.mtd, -125000.0)


from tools._lib.current_trade import TraderStatus


class AssembleTraderStatusDraftTest(unittest.TestCase):
    def test_combines_balance_holdings_pnl_leaves_judgment_fields_empty(self):
        cash = _load("carina_cash.json")
        positions = _load("carina_positions.json")
        orders = _load("carina_orders.json")
        today = dt.date(2026, 4, 20)
        prior = TraderStatus()  # regime="", aggressiveness="", blank PnL

        draft = l0_synth.assemble_trader_status_draft(
            carina_cash=cash,
            carina_positions=positions,
            carina_orders=orders,
            prior_status=prior,
            today=today,
        )

        self.assertIsInstance(draft, TraderStatus)
        # Balance populated.
        self.assertEqual(draft.balance.cash, 19612924.64)
        # Holdings populated, details left empty for Opus.
        self.assertEqual(len(draft.holdings), 2)
        self.assertTrue(all(h.details == "" for h in draft.holdings))
        # PnL rolled up.
        self.assertEqual(draft.pnl.mtd, -125000.0)
        self.assertEqual(draft.pnl.ytd, 1200000.0)
        # Unrealized = sum of position unrealized_pnl fields.
        self.assertAlmostEqual(draft.pnl.unrealized, 60000.0)  # -40000 + 100000
        # Judgment fields untouched — Opus fills later.
        self.assertEqual(draft.aggressiveness, "")
        # Regime/sectors/narratives remain whatever prior was (L0 does not write).
        self.assertEqual(draft.regime, prior.regime)
        self.assertEqual(draft.sectors, prior.sectors)
        self.assertEqual(draft.narratives, prior.narratives)
