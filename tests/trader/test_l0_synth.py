import datetime as dt
import json
import unittest
from pathlib import Path

from tools._lib import current_trade as ct
from tools._lib.current_trade import PnL, TraderStatus
from tools.trader import l0_synth

FIXTURES = Path(__file__).parent / "fixtures" / "l0"


def _load(name: str):
    with open(FIXTURES / name) as f:
        return json.load(f)


class BalanceFromPortfolioTest(unittest.TestCase):
    def test_parses_cash_from_summary(self):
        resp = _load("carina_portfolio.json")
        balance = l0_synth.balance_from_portfolio(resp)
        self.assertIsInstance(balance, ct.Balance)
        self.assertEqual(balance.cash, 19612924.64)
        self.assertEqual(balance.buying_power, 19612924.64)


class HoldingsFromPortfolioTest(unittest.TestCase):
    def test_parses_each_position_into_holding(self):
        resp = _load("carina_portfolio.json")
        holdings = l0_synth.holdings_from_portfolio(resp)
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


class PnLRollupFromOrdersTest(unittest.TestCase):
    def test_fifo_pairing_produces_mtd_and_ytd(self):
        rows = _load("journal_orders.json")
        today = dt.date(2026, 4, 20)
        prior = PnL()
        pnl = l0_synth.pnl_rollup_from_orders(rows, prior_pnl=prior, today=today)
        # BUMI: BUY 500@500 + SELL 500@250 on 2026-04-15 → realized = -125000 (MtD + YtD).
        self.assertEqual(pnl.mtd, -125000.0)
        # AADI: BUY 100@10000 + SELL 100@23250 on 2026-03-20 → realized = +1325000 (YtD only).
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_empty_rows_falls_back_to_prior(self):
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=-250000.0, ytd=1200000.0)
        pnl = l0_synth.pnl_rollup_from_orders([], prior_pnl=prior, today=today)
        self.assertEqual(pnl.mtd, -250000.0)
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_non_buysell_actions_ignored(self):
        rows = _load("journal_orders.json")
        today = dt.date(2026, 4, 20)
        prior = PnL()
        pnl = l0_synth.pnl_rollup_from_orders(rows, prior_pnl=prior, today=today)
        # CANCEL row for ADMR on 2026-04-18 must not leak into MtD.
        self.assertEqual(pnl.mtd, -125000.0)


class AssembleTraderStatusDraftTest(unittest.TestCase):
    def test_combines_balance_holdings_pnl_leaves_judgment_fields_empty(self):
        portfolio = _load("carina_portfolio.json")
        orders = _load("journal_orders.json")
        today = dt.date(2026, 4, 20)
        prior = TraderStatus()

        draft = l0_synth.assemble_trader_status_draft(
            carina_portfolio=portfolio,
            journal_rows=orders,
            prior_status=prior,
            today=today,
        )

        self.assertIsInstance(draft, TraderStatus)
        self.assertEqual(draft.balance.cash, 19612924.64)
        self.assertEqual(len(draft.holdings), 2)
        self.assertTrue(all(h.details == "" for h in draft.holdings))
        self.assertEqual(draft.pnl.mtd, -125000.0)
        self.assertEqual(draft.pnl.ytd, 1200000.0)
        # Unrealized comes from portfolio summary, not per-position sum.
        self.assertAlmostEqual(draft.pnl.unrealized, 60000.0)
        self.assertEqual(draft.aggressiveness, "")
        self.assertEqual(draft.regime, prior.regime)
        self.assertEqual(draft.sectors, prior.sectors)
        self.assertEqual(draft.narratives, prior.narratives)


if __name__ == "__main__":
    unittest.main()
