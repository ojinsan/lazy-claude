"""Tests for spec #7 Tasks 3+4: l5_synth validators, builders, decision tree, formatters."""
import sys, os, unittest, datetime as _dt
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools._lib.current_trade import ExecutionState, FillEvent, TradePlan
from tools.trader.l5_synth import (
    validate_plan_for_execute,
    check_price_drift,
    check_cash_sufficient,
    check_holdings_sufficient,
    build_entry_payload,
    build_stop_payload,
    build_tp_payload,
    classify_order_state,
    is_order_stale,
    append_fill,
    fmt_place_event,
    fmt_fill_event,
    fmt_error_event,
    fmt_stale_event,
    fmt_circuit_breaker_event,
    fmt_daily_note_block,
)

_WIB = _dt.timezone(_dt.timedelta(hours=7))


def _plan(entry=1855, stop=1830, tp1=1955, tp2=None, lots=50, side="buy"):
    return TradePlan(entry=entry, stop=stop, tp1=tp1, tp2=tp2,
                     lots=lots, risk_idr=100000.0, mode="A")


# ── validate_plan_for_execute ──────────────────────────────────────────────

class ValidatePlanTest(unittest.TestCase):

    def test_valid_buy(self):
        self.assertIsNone(validate_plan_for_execute(_plan(), "buy"))

    def test_valid_sell(self):
        p = _plan(entry=1855, stop=1900, tp1=1750)
        self.assertIsNone(validate_plan_for_execute(p, "sell"))

    def test_zero_lots(self):
        p = _plan(lots=0)
        err = validate_plan_for_execute(p, "buy")
        self.assertIn("lots", err)

    def test_negative_lots(self):
        p = _plan(lots=-1)
        self.assertIn("lots", validate_plan_for_execute(p, "buy"))

    def test_zero_entry(self):
        p = _plan(entry=0)
        self.assertIn("entry", validate_plan_for_execute(p, "buy"))

    def test_zero_stop(self):
        p = _plan(stop=0)
        self.assertIn("stop", validate_plan_for_execute(p, "buy"))

    def test_zero_tp1(self):
        p = _plan(tp1=0)
        self.assertIn("tp1", validate_plan_for_execute(p, "buy"))

    def test_buy_stop_above_entry(self):
        p = _plan(entry=1855, stop=1900)
        self.assertIn("stop", validate_plan_for_execute(p, "buy"))

    def test_sell_stop_below_entry(self):
        p = _plan(entry=1855, stop=1800, tp1=1750)
        self.assertIn("stop", validate_plan_for_execute(p, "sell"))

    def test_buy_stop_equal_entry(self):
        p = _plan(entry=1855, stop=1855)
        self.assertIn("stop", validate_plan_for_execute(p, "buy"))


# ── check_price_drift ──────────────────────────────────────────────────────

class PriceDriftTest(unittest.TestCase):

    def test_no_drift(self):
        self.assertFalse(check_price_drift(1855, 1855))

    def test_small_drift(self):
        self.assertFalse(check_price_drift(1855, 1900))  # ~2.4%

    def test_exact_threshold(self):
        # exactly 5% → not triggered (> not >=)
        live = 1855 * 1.05
        self.assertFalse(check_price_drift(1855, live))

    def test_above_threshold(self):
        live = 1855 * 1.051
        self.assertTrue(check_price_drift(1855, live))

    def test_drop(self):
        live = 1855 * 0.94
        self.assertTrue(check_price_drift(1855, live))

    def test_custom_pct(self):
        self.assertTrue(check_price_drift(1855, 1875, pct=0.01))

    def test_zero_plan_price(self):
        self.assertTrue(check_price_drift(0, 1855))


# ── check_cash_sufficient ──────────────────────────────────────────────────

class CashSufficientTest(unittest.TestCase):

    def test_sufficient(self):
        # 50 lots * 100 shares * 1855 * 1.002 = 9,287,610
        self.assertTrue(check_cash_sufficient(10_000_000, 50, 1855))

    def test_exact_boundary(self):
        notional = 50 * 100 * 1855
        required = notional * 1.002
        self.assertTrue(check_cash_sufficient(required, 50, 1855))

    def test_insufficient(self):
        self.assertFalse(check_cash_sufficient(1_000_000, 50, 1855))

    def test_zero_lots(self):
        self.assertTrue(check_cash_sufficient(0, 0, 1855))


# ── check_holdings_sufficient ──────────────────────────────────────────────

class HoldingsSufficientTest(unittest.TestCase):

    def test_sufficient(self):
        self.assertTrue(check_holdings_sufficient(50, 50))

    def test_more_than_enough(self):
        self.assertTrue(check_holdings_sufficient(100, 50))

    def test_insufficient(self):
        self.assertFalse(check_holdings_sufficient(30, 50))

    def test_zero_held(self):
        self.assertFalse(check_holdings_sufficient(0, 50))


# ── Payload builders ───────────────────────────────────────────────────────

class PayloadBuildersTest(unittest.TestCase):

    def _p(self):
        return _plan()

    def test_entry_buy(self):
        payload = build_entry_payload("ADMR", self._p(), "buy")
        self.assertEqual(payload["stock_code"], "ADMR")
        self.assertEqual(payload["shares"], 5000)
        self.assertEqual(payload["price"], 1855)
        self.assertEqual(payload["side"], "buy")
        self.assertEqual(payload["order_type"], "LIMIT_DAY")

    def test_entry_sell(self):
        payload = build_entry_payload("ADMR", self._p(), "sell")
        self.assertEqual(payload["side"], "sell")

    def test_stop_buy_position(self):
        payload = build_stop_payload("ADMR", self._p(), "buy")
        self.assertEqual(payload["price"], 1830)
        self.assertEqual(payload["side"], "sell")  # stop for buy = sell order

    def test_stop_sell_position(self):
        p = _plan(entry=1855, stop=1900, tp1=1750)
        payload = build_stop_payload("ADMR", p, "sell")
        self.assertEqual(payload["side"], "buy")  # stop for sell = buy order

    def test_tp1_buy(self):
        payload = build_tp_payload("ADMR", self._p(), "buy", "tp1")
        self.assertEqual(payload["price"], 1955)
        self.assertEqual(payload["side"], "sell")

    def test_tp2_buy(self):
        p = _plan(tp2=2050)
        payload = build_tp_payload("ADMR", p, "buy", "tp2")
        self.assertEqual(payload["price"], 2050)

    def test_tp2_fallback_when_none(self):
        p = _plan(tp2=None)
        payload = build_tp_payload("ADMR", p, "buy", "tp2")
        self.assertEqual(payload["price"], p.tp1)

    def test_shares_is_lots_times_100(self):
        p = _plan(lots=10)
        payload = build_entry_payload("ADMR", p, "buy")
        self.assertEqual(payload["shares"], 1000)


# ── classify_order_state ───────────────────────────────────────────────────

class ClassifyOrderStateTest(unittest.TestCase):

    def test_filled(self):
        self.assertEqual(classify_order_state({"status": "filled"}), "filled")

    def test_filled_done(self):
        self.assertEqual(classify_order_state({"status": "done"}), "filled")

    def test_partial(self):
        self.assertEqual(classify_order_state({"status": "partial"}), "partial")

    def test_open(self):
        self.assertEqual(classify_order_state({"status": "open"}), "open")

    def test_cancelled(self):
        self.assertEqual(classify_order_state({"status": "cancelled"}), "cancelled")

    def test_canceled_alt_spelling(self):
        self.assertEqual(classify_order_state({"status": "canceled"}), "cancelled")

    def test_expired(self):
        self.assertEqual(classify_order_state({"status": "expired"}), "cancelled")

    def test_rejected(self):
        self.assertEqual(classify_order_state({"status": "rejected"}), "failed")

    def test_case_insensitive(self):
        self.assertEqual(classify_order_state({"status": "FILLED"}), "filled")

    def test_unknown_status(self):
        self.assertEqual(classify_order_state({"status": "pending_review"}), "open")

    def test_missing_status(self):
        self.assertEqual(classify_order_state({}), "open")


# ── is_order_stale ─────────────────────────────────────────────────────────

class IsOrderStaleTest(unittest.TestCase):

    def _now(self):
        return _dt.datetime(2026, 4, 24, 12, 0, 0, tzinfo=_WIB)

    def test_fresh_order(self):
        order = {
            "status": "open",
            "created_at": "2026-04-24T10:00:00+07:00",
        }
        self.assertFalse(is_order_stale(order, stale_hours=3.0, now=self._now()))

    def test_stale_order(self):
        order = {
            "status": "open",
            "created_at": "2026-04-24T08:00:00+07:00",  # 4h ago
        }
        self.assertTrue(is_order_stale(order, stale_hours=3.0, now=self._now()))

    def test_filled_not_stale(self):
        order = {
            "status": "filled",
            "created_at": "2026-04-24T06:00:00+07:00",
        }
        self.assertFalse(is_order_stale(order, stale_hours=3.0, now=self._now()))

    def test_missing_created_at(self):
        order = {"status": "open"}
        self.assertFalse(is_order_stale(order, stale_hours=3.0, now=self._now()))

    def test_custom_threshold(self):
        order = {
            "status": "open",
            "created_at": "2026-04-24T10:30:00+07:00",  # 1.5h ago
        }
        self.assertTrue(is_order_stale(order, stale_hours=1.0, now=self._now()))
        self.assertFalse(is_order_stale(order, stale_hours=2.0, now=self._now()))


# ── append_fill ────────────────────────────────────────────────────────────

class AppendFillTest(unittest.TestCase):

    def test_appends_fill(self):
        ex = ExecutionState(status="filled", entry_order_id="CR-12345")
        order = {
            "order_id": "CR-12345",
            "filled_shares": 5000,
            "avg_fill_price": 1855.0,
            "updated_at": "2026-04-24T09:12:00+07:00",
        }
        append_fill(ex, order, "entry")
        self.assertEqual(len(ex.fills), 1)
        fill = ex.fills[0]
        self.assertEqual(fill.lot, 50)
        self.assertEqual(fill.price, 1855.0)
        self.assertEqual(fill.leg, "entry")
        self.assertEqual(fill.order_id, "CR-12345")

    def test_zero_filled_shares_skipped(self):
        ex = ExecutionState()
        order = {"order_id": "CR-x", "filled_shares": 0}
        append_fill(ex, order, "entry")
        self.assertEqual(ex.fills, [])

    def test_returns_same_object(self):
        ex = ExecutionState()
        order = {"order_id": "x", "filled_shares": 100,
                 "avg_fill_price": 1000.0, "updated_at": "t"}
        result = append_fill(ex, order, "tp1")
        self.assertIs(result, ex)

    def test_partial_lots_rounded(self):
        ex = ExecutionState()
        order = {"order_id": "x", "filled_shares": 2000,
                 "avg_fill_price": 1854.0, "updated_at": "t"}
        append_fill(ex, order, "entry")
        self.assertEqual(ex.fills[0].lot, 20)


# ── Telegram formatters ────────────────────────────────────────────────────

class FormattersTest(unittest.TestCase):

    def test_fmt_place_event(self):
        msg = fmt_place_event("ADMR", "buy", 50, 1855, "CR-12345")
        self.assertIn("PLACE", msg)
        self.assertIn("ADMR", msg)
        self.assertIn("50lot", msg)
        self.assertIn("CR-12345", msg)

    def test_fmt_fill_event(self):
        msg = fmt_fill_event("ADMR", 50, 1855, 1830, 1955)
        self.assertIn("FILL", msg)
        self.assertIn("1,830", msg)
        self.assertIn("1,955", msg)

    def test_fmt_error_event_simple(self):
        msg = fmt_error_event("ADMR", "insufficient_funds")
        self.assertIn("ERROR", msg)
        self.assertIn("insufficient_funds", msg)

    def test_fmt_error_event_with_amounts(self):
        msg = fmt_error_event("ADMR", "insufficient_funds",
                              cash=2_100_000, notional=9_250_000)
        self.assertIn("2.1M", msg)
        self.assertIn("9.25M", msg)

    def test_fmt_stale_event(self):
        msg = fmt_stale_event("ADMR", 6.3)
        self.assertIn("STALE", msg)
        self.assertIn("6h", msg)

    def test_fmt_circuit_breaker(self):
        msg = fmt_circuit_breaker_event("ADMR", 1855, 1952)
        self.assertIn("DRIFT", msg)
        self.assertIn("ADMR", msg)

    def test_fmt_daily_note_block_empty(self):
        block = fmt_daily_note_block("2026-04-24", [])
        self.assertIn("L5 Execution", block)
        self.assertIn("No L5 activity", block)

    def test_fmt_daily_note_block_with_events(self):
        events = ["[L5 place] ADMR buy 50lot @ 1855 (order CR-12345)"]
        block = fmt_daily_note_block("2026-04-24", events)
        self.assertIn("ADMR", block)
        self.assertIn("2026-04-24", block)


if __name__ == "__main__":
    unittest.main()
