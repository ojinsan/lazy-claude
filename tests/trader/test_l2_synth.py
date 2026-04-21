"""Unit tests for tools/trader/l2_synth.py — pure helpers, no I/O."""
from __future__ import annotations

import json
import pathlib
import unittest

from tools.trader import l2_synth

FIX = pathlib.Path(__file__).parent / "fixtures" / "l2"


def _counts(ss=0, s=0, w=0, r=0):
    """Build a 4-dim score dict given counts of each label."""
    labels = (["superstrong"] * ss + ["strong"] * s + ["weak"] * w + ["redflag"] * r)
    assert len(labels) == 4, f"labels must sum to 4, got {len(labels)}"
    return {"price": labels[0], "broker": labels[1], "book": labels[2], "narrative": labels[3]}


class PromotionDecisionTest(unittest.TestCase):
    # Superlist rules
    def test_one_superstrong_promotes(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(ss=1, w=3), is_holding=False), "superlist")

    def test_one_superstrong_with_redflag_still_promotes(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(ss=1, w=2, r=1), is_holding=False), "superlist")

    def test_three_strong_promotes(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(s=3, w=1), is_holding=False), "superlist")

    def test_three_strong_with_redflag_still_promotes(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(s=3, r=1), is_holding=False), "superlist")

    def test_two_strong_zero_redflag_promotes(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(s=2, w=2), is_holding=False), "superlist")

    def test_two_strong_with_redflag_does_not_promote(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(s=2, w=1, r=1), is_holding=False), "drop")

    # Exitlist rules (holding only)
    def test_two_redflags_holding_exits(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(w=2, r=2), is_holding=True), "exitlist")

    def test_three_redflags_holding_exits(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(w=1, r=3), is_holding=True), "exitlist")

    def test_two_redflags_nonholding_drops(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(w=2, r=2), is_holding=False), "drop")

    def test_one_redflag_holding_does_not_exit(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(w=3, r=1), is_holding=True), "drop")

    # Superlist wins over exitlist for holding with strong dims even with redflag
    def test_holding_with_superstrong_and_redflag_promotes(self):
        # 1 superstrong + 1 redflag + 2 weak → superlist, not exitlist (only 1 redflag)
        self.assertEqual(l2_synth.promotion_decision(_counts(ss=1, w=2, r=1), is_holding=True), "superlist")

    def test_holding_with_two_strong_and_two_redflag_exits(self):
        # 2 strong + 2 redflag → fails superlist (2 strong requires 0 redflag), 2 redflag → exit
        self.assertEqual(l2_synth.promotion_decision(_counts(s=2, r=2), is_holding=True), "exitlist")

    # Drop / default
    def test_all_weak_drops(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(w=4), is_holding=False), "drop")

    def test_one_strong_rest_weak_drops(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(s=1, w=3), is_holding=False), "drop")

    def test_all_redflag_holding_exits(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(r=4), is_holding=True), "exitlist")

    def test_all_redflag_nonholding_drops(self):
        self.assertEqual(l2_synth.promotion_decision(_counts(r=4), is_holding=False), "drop")


class ParseJudgeResponseTest(unittest.TestCase):
    def test_valid_fixture(self):
        raw = json.dumps(json.loads((FIX / "judge_response_valid.json").read_text()))
        scores, rationale = l2_synth.parse_judge_response(raw)
        self.assertEqual(scores, {"price": "strong", "broker": "superstrong", "book": "strong", "narrative": "strong"})
        self.assertIn("Wyckoff", rationale)

    def test_malformed_missing_dim_raises(self):
        raw = (FIX / "judge_response_malformed.json").read_text()
        with self.assertRaises(ValueError):
            l2_synth.parse_judge_response(raw)

    def test_strips_code_fences(self):
        valid = (FIX / "judge_response_valid.json").read_text()
        raw = f"```json\n{valid}\n```"
        scores, _ = l2_synth.parse_judge_response(raw)
        self.assertEqual(scores["price"], "strong")

    def test_strips_bare_fences(self):
        valid = (FIX / "judge_response_valid.json").read_text()
        raw = f"```\n{valid}\n```"
        scores, _ = l2_synth.parse_judge_response(raw)
        self.assertEqual(scores["price"], "strong")

    def test_unknown_label_raises(self):
        raw = '{"scores": {"price": "maybe", "broker": "strong", "book": "weak", "narrative": "weak"}, "rationale": "x"}'
        with self.assertRaises(ValueError):
            l2_synth.parse_judge_response(raw)

    def test_garbage_json_raises(self):
        with self.assertRaises(ValueError):
            l2_synth.parse_judge_response("not json at all")


class FormatJudgePromptTest(unittest.TestCase):
    def test_contains_required_sections(self):
        dims = {
            1: {"wyckoff_phase": "accumulation", "spring_hit": True, "vp_state": "accumulation", "rs_rank": 2},
            2: {"hapcu_net_buy": 42800000000, "konglo_in_l1_sectors": True},
            3: {"last_price": 1855, "pressure_side": "buyers", "stance": "strong_accumulation"},
            4: {"hit": True, "content": "coal theme"},
        }
        context = {"regime": "cautious", "sectors": ["coal", "banking"], "aggressiveness": "neutral", "is_holding": False}
        p = l2_synth.format_judge_prompt("ADMR", dims, context)
        self.assertIn("ADMR", p)
        self.assertIn("cautious", p)
        self.assertIn("coal", p)
        self.assertIn("neutral", p)
        self.assertIn("superstrong", p)  # enum guardrails
        self.assertIn("redflag", p)
        self.assertIn("accumulation", p)  # dim-1 blob
        self.assertIn("42800000000", p)  # dim-2 blob
        self.assertIn("strong_accumulation", p)  # dim-3 blob

    def test_holding_flag_surfaced(self):
        context = {"regime": "risk_on", "sectors": ["coal"], "aggressiveness": "aggressive", "is_holding": True}
        p = l2_synth.format_judge_prompt("BUMI", {1: {}, 2: {}, 3: {}, 4: {}}, context)
        self.assertIn("is_holding=True", p)


class ParseMergeResponseTest(unittest.TestCase):
    def test_valid_fixture(self):
        raw = (FIX / "merge_response.json").read_text()
        out = l2_synth.parse_merge_response(raw)
        self.assertEqual(out["ADMR"]["current_plan"], "buy_at_price")
        self.assertEqual(out["GOTO"]["current_plan"], "wait_bid_offer")
        self.assertEqual(out["BUMI"]["current_plan"], "sell_at_price")

    def test_invalid_current_plan_raises(self):
        raw = '{"ADMR": {"current_plan": "moon_at_price", "details": "x"}}'
        with self.assertRaises(ValueError):
            l2_synth.parse_merge_response(raw)

    def test_strips_fences(self):
        valid = (FIX / "merge_response.json").read_text()
        out = l2_synth.parse_merge_response(f"```json\n{valid}\n```")
        self.assertIn("ADMR", out)


class FormatMergePromptTest(unittest.TestCase):
    def test_contains_promoted_and_exits(self):
        promoted = [{"ticker": "ADMR", "scores": {"price": "strong"}, "rationale": "foo"}]
        exits = [{"ticker": "BUMI", "scores": {"price": "redflag"}, "rationale": "bar"}]
        p = l2_synth.format_merge_prompt(promoted, exits, holdings=["BUMI"], regime="cautious")
        self.assertIn("ADMR", p)
        self.assertIn("BUMI", p)
        self.assertIn("cautious", p)
        self.assertIn("current_plan", p)
        self.assertIn("buy_at_price", p)
        self.assertIn("sell_at_price", p)
        self.assertIn("wait_bid_offer", p)


class FormatTelegramRecapTest(unittest.TestCase):
    def test_empty_superlist_path(self):
        out = l2_synth.format_telegram_recap(
            superlist=[], exitlist=[], n_judged=14, regime="cautious", prev_superlist_count=3, now_hhmm="05:18",
        )
        self.assertIn("0 promoted", out)
        self.assertIn("14 judged", out)
        self.assertIn("cautious", out)

    def test_full_path_shows_top_tickers(self):
        superlist = [
            {"ticker": "ADMR", "current_plan": "buy_at_price", "details": "foo"},
            {"ticker": "PWON", "current_plan": "buy_at_price", "details": "bar"},
            {"ticker": "GOTO", "current_plan": "wait_bid_offer", "details": "baz"},
        ]
        exitlist = [{"ticker": "BUMI", "current_plan": "sell_at_price", "details": "exit now"}]
        out = l2_synth.format_telegram_recap(
            superlist=superlist, exitlist=exitlist, n_judged=15, regime="risk_on", prev_superlist_count=1, now_hhmm="05:22",
        )
        self.assertIn("ADMR", out)
        self.assertIn("PWON", out)
        self.assertIn("GOTO", out)
        self.assertIn("BUMI", out)
        self.assertIn("risk_on", out)
        self.assertIn("05:22", out)

    def test_caps_top_three_per_bucket(self):
        superlist = [
            {"ticker": f"T{i}", "current_plan": "buy_at_price", "details": "x"} for i in range(8)
        ]
        out = l2_synth.format_telegram_recap(
            superlist=superlist, exitlist=[], n_judged=8, regime="cautious", prev_superlist_count=0, now_hhmm="05:00",
        )
        self.assertIn("T0", out)
        self.assertIn("T1", out)
        self.assertIn("T2", out)
        # beyond top-3 should not appear
        self.assertNotIn("T5", out)
        self.assertNotIn("T7", out)


if __name__ == "__main__":
    unittest.main()
