import json
import os
import unittest

from tools.trader import l3_synth

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "l3")


def _fix(name):
    with open(os.path.join(FIX, name)) as f:
        return json.load(f)


class TestParseJudgeResponse(unittest.TestCase):

    def test_intact(self):
        out = l3_synth.parse_judge_response(json.dumps(_fix("judge_response_intact.json")))
        self.assertEqual(out["label"], "intact")
        self.assertFalse(out["buy_now"])
        self.assertFalse(out["thesis_break"])

    def test_strengthening_buy_now(self):
        out = l3_synth.parse_judge_response(json.dumps(_fix("judge_response_strengthening_buy_now.json")))
        self.assertEqual(out["label"], "strengthening")
        self.assertTrue(out["buy_now"])

    def test_weakening(self):
        out = l3_synth.parse_judge_response(json.dumps(_fix("judge_response_weakening.json")))
        self.assertEqual(out["label"], "weakening")

    def test_broken(self):
        out = l3_synth.parse_judge_response(json.dumps(_fix("judge_response_broken.json")))
        self.assertEqual(out["label"], "broken")
        self.assertTrue(out["thesis_break"])

    def test_strips_fences(self):
        raw = "```json\n" + json.dumps(_fix("judge_response_intact.json")) + "\n```"
        out = l3_synth.parse_judge_response(raw)
        self.assertEqual(out["label"], "intact")

    def test_malformed_raises(self):
        with self.assertRaises(ValueError):
            l3_synth.parse_judge_response(json.dumps(_fix("judge_response_malformed.json")))

    def test_unknown_label_raises(self):
        with self.assertRaises(ValueError):
            l3_synth.parse_judge_response('{"label":"bogus","buy_now":false,"thesis_break":false,"rationale":"x"}')


class TestBuyNowGate(unittest.TestCase):

    def _judge(self, label="strengthening", buy_now=True, thesis_break=False):
        return {"label": label, "buy_now": buy_now, "thesis_break": thesis_break, "rationale": "x"}

    def _dim(self, tc_buy_strong=True, spring=True, composite="ideal_markup", confidence="high"):
        return {
            "thick_wall_buy_strong": tc_buy_strong,
            "thick_wall_buy": tc_buy_strong,
            "spring_confirmed": spring,
            "spring_confidence": confidence if spring else "low",
            "tape_composite": composite,
            "tape_confidence": confidence,
        }

    def _plan(self, mode="buy_at_price", price=1855):
        return {"mode": mode, "price": price}

    def test_fires_when_all_conditions_met(self):
        self.assertTrue(l3_synth.buy_now_gate(
            self._judge(), self._plan(), price_now=1856, intraday_notch=0, fired_set=set(),
            dim=self._dim(), is_superlist=True,
        ))

    def test_blocks_when_not_superlist(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(), self._plan(), 1856, 0, set(), self._dim(), is_superlist=False,
        ))

    def test_blocks_when_judge_buy_now_false(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(buy_now=False), self._plan(), 1856, 0, set(), self._dim(), is_superlist=True,
        ))

    def test_blocks_when_no_setup_hit(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(), self._plan(), 1856, 0, set(),
            self._dim(tc_buy_strong=False, spring=False, composite="neutral"),
            is_superlist=True,
        ))

    def test_blocks_when_price_far_from_plan(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(), self._plan(price=1855), price_now=1900, intraday_notch=0,
            fired_set=set(), dim=self._dim(), is_superlist=True,
        ))

    def test_blocks_when_notch_negative(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(), self._plan(), 1856, -1, set(), self._dim(), is_superlist=True,
        ))

    def test_blocks_when_already_fired(self):
        self.assertFalse(l3_synth.buy_now_gate(
            self._judge(), self._plan(), 1856, 0, {"ADMR"}, self._dim(),
            is_superlist=True, ticker="ADMR",
        ))

    def test_fires_on_spring_only_setup(self):
        self.assertTrue(l3_synth.buy_now_gate(
            self._judge(), self._plan(), 1856, 0, set(),
            self._dim(tc_buy_strong=False, spring=True, composite="neutral"),
            is_superlist=True,
        ))


class TestMergePlanUpdate(unittest.TestCase):

    def test_intact_returns_none(self):
        prior = {"mode": "buy_at_price", "price": 1855}
        out = l3_synth.merge_plan_update("ADMR", "intact", False, prior, is_holding=False)
        self.assertIsNone(out)

    def test_broken_on_holding_flips_to_sell(self):
        prior = {"mode": "buy_at_price", "price": 1855}
        out = l3_synth.merge_plan_update("BUMI", "broken", False, prior, is_holding=True)
        self.assertEqual(out["current_plan"]["mode"], "sell_at_price")

    def test_weakening_on_superlist_sets_wait(self):
        prior = {"mode": "buy_at_price", "price": 1855}
        out = l3_synth.merge_plan_update("ADMR", "weakening", False, prior, is_holding=False)
        self.assertEqual(out["current_plan"]["mode"], "wait_bid_offer")

    def test_strengthening_with_buy_now_keeps_mode(self):
        prior = {"mode": "buy_at_price", "price": 1855}
        out = l3_synth.merge_plan_update("ADMR", "strengthening", True, prior, is_holding=False)
        self.assertEqual(out["current_plan"]["mode"], "buy_at_price")


class TestFormatHelpers(unittest.TestCase):

    def test_format_judge_prompt_has_all_fields(self):
        dim = {"tape_composite": "healthy_markup", "thick_wall_buy_strong": True, "spring_confirmed": False}
        ctx = {"is_holding": False, "is_superlist": True, "is_exitlist": False, "prior_plan": {"mode": "buy_at_price", "price": 1855}, "regime": "risk-on", "sectors": ["coal"], "intraday_notch": 0}
        p = l3_synth.format_judge_prompt("ADMR", dim, ctx)
        self.assertIn("ADMR", p)
        self.assertIn("healthy_markup", p)
        self.assertIn("risk-on", p)
        self.assertIn("1855", p)
        self.assertIn("intraday_notch", p)
        for label in ("intact", "strengthening", "weakening", "broken"):
            self.assertIn(label, p)

    def test_format_intraday_notch_alert(self):
        msg = l3_synth.format_intraday_notch_alert(ihsg_pct=-1.2, foreign_delta=-850.0)
        self.assertIn("-1.2", msg)
        self.assertIn("notch", msg.lower())

    def test_format_telegram_events_empty_returns_none(self):
        self.assertIsNone(l3_synth.format_telegram_events([]))

    def test_format_telegram_events_buy_now(self):
        msg = l3_synth.format_telegram_events([
            {"kind": "buy_now", "ticker": "ADMR", "price": 1860, "rationale": "thick wall withdrawn"},
        ])
        self.assertIn("ADMR", msg)
        self.assertIn("BUY-NOW", msg.upper())

    def test_format_telegram_events_thesis_break(self):
        msg = l3_synth.format_telegram_events([
            {"kind": "thesis_break", "ticker": "BUMI", "rationale": "support broken"},
        ])
        self.assertIn("BUMI", msg)

    def test_parse_opus_confirm_approve(self):
        with open(os.path.join(FIX, "opus_confirm_approve.json")) as f:
            raw = f.read()
        out = l3_synth.parse_opus_confirm_response(raw)
        self.assertTrue(out["approve"])

    def test_parse_opus_confirm_reject(self):
        with open(os.path.join(FIX, "opus_confirm_reject.json")) as f:
            raw = f.read()
        out = l3_synth.parse_opus_confirm_response(raw)
        self.assertFalse(out["approve"])

    def test_format_daily_note_events_empty_returns_none(self):
        self.assertIsNone(l3_synth.format_daily_note_events([], "12:10"))

    def test_format_daily_note_events_has_timestamp(self):
        out = l3_synth.format_daily_note_events(
            [{"kind": "buy_now", "ticker": "ADMR", "price": 1860, "rationale": "x"}],
            "12:10",
        )
        self.assertIn("12:10", out)


if __name__ == "__main__":
    unittest.main()
