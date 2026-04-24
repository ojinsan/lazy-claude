import json
import unittest
from pathlib import Path

from tools.trader.l4_synth import (
    get_tick,
    round_to_tick,
    size_plan,
    TIER,
    BP_SINGLE_NAME_CAP,
    format_plan_prompt_a,
    format_plan_prompt_b,
    parse_opus_plan_response,
)

FIX = Path(__file__).resolve().parent / "fixtures" / "l4"


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


class FormatPlanPromptATest(unittest.TestCase):
    def _ctx(self):
        return {
            "ticker": "ADMR",
            "regime": "bullish",
            "aggressiveness": "med",
            "side": "buy",
            "bp_idr": 100_000_000,
            "conf": 82,
            "details": "3 strong dims",
            "narrative": "coal theme",
            "structure": {
                "trend": "uptrend", "wyckoff_phase": "accumulation",
                "support": 1820, "resistance": 1960,
                "last_swing_low": {"price": 1830},
            },
            "atr": 32, "close": 1870, "hi60": 1960, "lo60": 1620,
        }

    def test_contains_ticker_and_side(self):
        p = format_plan_prompt_a(self._ctx())
        self.assertIn("ADMR", p)
        self.assertIn("side=buy", p)

    def test_renders_structure(self):
        p = format_plan_prompt_a(self._ctx())
        self.assertIn("support=1820", p)
        self.assertIn("last_swing_low=1830", p)
        self.assertIn("wyckoff=accumulation", p)

    def test_renders_numeric_bp(self):
        p = format_plan_prompt_a(self._ctx())
        self.assertIn("100,000,000", p)

    def test_missing_optional_narrative(self):
        ctx = self._ctx(); ctx.pop("narrative")
        p = format_plan_prompt_a(ctx)
        self.assertIn("narrative: —", p)

    def test_sell_side(self):
        ctx = self._ctx(); ctx["side"] = "sell"
        p = format_plan_prompt_a(ctx)
        self.assertIn("side=sell", p)


class FormatPlanPromptBTest(unittest.TestCase):
    def _ctx(self):
        return {
            "ticker": "ADMR",
            "conf": 82,
            "orderbook": {"best_bid": 1870, "best_offer": 1875, "last_price": 1875},
            "last_note": {"composite": "ideal_markup", "thick_wall_buy_strong": True, "spring_confirmed": True},
            "support": 1820,
            "last_swing_low": 1830,
            "atr": 32,
            "intraday_notch": 0,
        }

    def test_contains_orderbook(self):
        p = format_plan_prompt_b(self._ctx())
        self.assertIn("best_offer=1875", p)
        self.assertIn("last=1875", p)

    def test_contains_tape_flags(self):
        p = format_plan_prompt_b(self._ctx())
        self.assertIn("thick_wall_buy_strong=True", p)
        self.assertIn("spring_confirmed=True", p)

    def test_mentions_abort_option(self):
        p = format_plan_prompt_b(self._ctx())
        self.assertIn("abort", p)


class ParseOpusPlanResponseTest(unittest.TestCase):
    def test_parse_approve_full(self):
        raw = (FIX / "opus_plan_A_approve.json").read_text()
        d = parse_opus_plan_response(raw)
        self.assertFalse(d.get("abort"))
        self.assertEqual(d["entry"], 1855)
        self.assertEqual(d["tp2"], 2050)
        self.assertIn("Accumulation", d["rationale"])

    def test_parse_mode_b_approve(self):
        raw = (FIX / "opus_plan_B_approve.json").read_text()
        d = parse_opus_plan_response(raw)
        self.assertEqual(d["entry"], 1875)
        self.assertEqual(d["stop"], 1825)

    def test_parse_abort(self):
        raw = (FIX / "opus_plan_B_abort.json").read_text()
        d = parse_opus_plan_response(raw)
        self.assertTrue(d["abort"])
        self.assertIn("too loose", d["reason"])

    def test_parse_malformed_missing_key_raises(self):
        raw = (FIX / "opus_malformed.json").read_text()
        with self.assertRaises(ValueError) as cm:
            parse_opus_plan_response(raw)
        self.assertIn("tp1", str(cm.exception))

    def test_parse_fenced_json(self):
        raw = '```json\n{"entry":1,"stop":0.5,"tp1":2,"tp2":null,"rationale":"x"}\n```'
        d = parse_opus_plan_response(raw)
        self.assertEqual(d["entry"], 1.0)
        self.assertIsNone(d["tp2"])

    def test_parse_fenced_no_lang(self):
        raw = '```\n{"entry":1,"stop":0.5,"tp1":2,"rationale":"x"}\n```'
        d = parse_opus_plan_response(raw)
        self.assertEqual(d["stop"], 0.5)

    def test_parse_rationale_truncated_to_180(self):
        long = "x" * 300
        raw = json.dumps({"entry": 1, "stop": 0.5, "tp1": 2, "rationale": long})
        d = parse_opus_plan_response(raw)
        self.assertEqual(len(d["rationale"]), 180)

    def test_parse_abort_missing_reason_raises(self):
        with self.assertRaises(ValueError):
            parse_opus_plan_response('{"abort": true}')

    def test_parse_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            parse_opus_plan_response("not json at all")

    def test_parse_non_object_raises(self):
        with self.assertRaises(ValueError):
            parse_opus_plan_response("[1,2,3]")

    def test_parse_abort_reason_truncated_to_80(self):
        raw = json.dumps({"abort": True, "reason": "y" * 200})
        d = parse_opus_plan_response(raw)
        self.assertEqual(len(d["reason"]), 80)


if __name__ == "__main__":
    unittest.main()
