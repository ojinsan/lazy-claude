import unittest

from tools._lib.current_trade import Holding, ListItem, Narrative
from tools.trader import l1_synth as ls


class ValidRegimeTest(unittest.TestCase):
    def test_accepts_three_literals(self):
        for r in ("risk_on", "cautious", "risk_off"):
            self.assertTrue(ls.valid_regime(r))

    def test_rejects_anything_else(self):
        for r in ("RISK_ON", "neutral", "", None, "risk on"):
            self.assertFalse(ls.valid_regime(r))


class SectorsCountValidTest(unittest.TestCase):
    def test_three_to_five_valid(self):
        self.assertTrue(ls.sectors_count_valid(["a", "b", "c"]))
        self.assertTrue(ls.sectors_count_valid(["a", "b", "c", "d", "e"]))

    def test_too_few_or_too_many_invalid(self):
        self.assertFalse(ls.sectors_count_valid(["a", "b"]))
        self.assertFalse(ls.sectors_count_valid(["a", "b", "c", "d", "e", "f"]))

    def test_empty_or_non_lowercase_invalid(self):
        self.assertFalse(ls.sectors_count_valid([]))
        self.assertFalse(ls.sectors_count_valid(["a", "", "c"]))
        self.assertFalse(ls.sectors_count_valid(["a", "B", "c"]))


class NarrativesCountValidTest(unittest.TestCase):
    def _n(self, ticker="ADMR"):
        return Narrative(ticker=ticker, content="x", source="rag", confidence=70)

    def test_three_to_five_valid(self):
        self.assertTrue(ls.narratives_count_valid([self._n() for _ in range(3)]))
        self.assertTrue(ls.narratives_count_valid([self._n() for _ in range(5)]))

    def test_boundaries_invalid(self):
        self.assertFalse(ls.narratives_count_valid([self._n() for _ in range(2)]))
        self.assertFalse(ls.narratives_count_valid([self._n() for _ in range(6)]))


class NarrativeAnchorsInWatchlistTest(unittest.TestCase):
    def _wl(self, tickers):
        return [ListItem(ticker=t, confidence=70) for t in tickers]

    def test_all_anchors_in_watchlist(self):
        narratives = [Narrative("ADMR", "x", "rag", 70), Narrative("BBCA", "y", "rag", 60)]
        self.assertTrue(ls.narrative_anchors_in_watchlist(narratives, self._wl(["ADMR", "BBCA", "BMRI"])))

    def test_missing_anchor_invalid(self):
        narratives = [Narrative("ADMR", "x", "rag", 70), Narrative("GOTO", "y", "rag", 60)]
        self.assertFalse(ls.narrative_anchors_in_watchlist(narratives, self._wl(["ADMR", "BBCA"])))

    def test_case_insensitive(self):
        narratives = [Narrative("admr", "x", "rag", 70)]
        self.assertTrue(ls.narrative_anchors_in_watchlist(narratives, self._wl(["ADMR"])))


class UnionCandidatePoolTest(unittest.TestCase):
    def test_deduped_preserves_first_seen_order(self):
        rag = [{"ticker": "ADMR"}, {"ticker": "BBCA"}]
        hapcu = [{"ticker": "BBCA"}, {"ticker": "BMRI"}]
        retail = {"tickers": [{"ticker": "ADRO"}, {"ticker": "BBCA"}]}
        lark = [{"ticker": "MBMA"}]
        holdings = [Holding("BRPT", 10, 100.0, 110.0, 10.0)]
        pool = ls.union_candidate_pool(rag, hapcu, retail, lark, holdings)
        self.assertEqual(pool, ["ADMR", "BBCA", "BMRI", "ADRO", "MBMA", "BRPT"])

    def test_holdings_always_included(self):
        pool = ls.union_candidate_pool([], [], {"tickers": []}, [], [Holding("GOTO", 5, 100, 100, 0)])
        self.assertIn("GOTO", pool)

    def test_accepts_empty_inputs(self):
        self.assertEqual(ls.union_candidate_pool([], [], {"tickers": []}, [], []), [])

    def test_uppercases_tickers(self):
        pool = ls.union_candidate_pool([{"ticker": "admr"}], [], {"tickers": []}, [], [])
        self.assertEqual(pool, ["ADMR"])

    def test_retail_avoider_list_shape_accepted(self):
        pool = ls.union_candidate_pool([], [], [{"ticker": "EMAS"}], [], [])
        self.assertEqual(pool, ["EMAS"])


class FormatTelegramRecapTest(unittest.TestCase):
    def _narratives(self):
        return [
            Narrative("ADMR", "coal exporters China winter", "rag", 75),
            Narrative("BBCA", "banking BI cut repricing", "rag", 70),
            Narrative("ICBP", "consumer Lebaran restock", "rag", 65),
        ]

    def _wl(self, tickers):
        return [ListItem(ticker=t, confidence=70) for t in tickers]

    def test_baseline_no_prefixes(self):
        s = ls.format_telegram_recap(
            regime="cautious",
            sectors=["coal", "banking", "consumer"],
            narratives=self._narratives(),
            watchlist=self._wl(["ADMR", "BUMI", "BBCA", "BMRI", "ICBP"]),
            prev_regime="cautious",
            l1a_fresh_minutes=10,
            rag_empty=False,
            now_hhmm="04:00",
        )
        self.assertIn("<b>L1 Insight — 04:00</b>", s)
        self.assertIn("<b>Regime:</b> CAUTIOUS", s)
        self.assertIn("<b>Sectors:</b> coal, banking, consumer", s)
        self.assertIn("<b>Themes (3):</b>", s)
        self.assertIn("• coal exporters China winter", s)
        self.assertIn("<b>Watchlist:</b> 5 (ADMR, BUMI, BBCA …)", s)
        self.assertIn("Scarlett · L1 · fresh 10min", s)
        self.assertNotIn("⚠️", s)

    def test_regime_flip_prefix(self):
        s = ls.format_telegram_recap(
            regime="risk_off", sectors=["a", "b", "c"], narratives=self._narratives(),
            watchlist=self._wl(["A", "B", "C"]),
            prev_regime="risk_on", l1a_fresh_minutes=10, rag_empty=False, now_hhmm="04:00",
        )
        self.assertIn("⚠️", s)
        self.assertIn("regime flipped:", s)
        self.assertIn("risk_on → risk_off", s)

    def test_rag_empty_prefix(self):
        s = ls.format_telegram_recap(
            regime="cautious", sectors=["a", "b", "c"], narratives=self._narratives(),
            watchlist=self._wl(["A"]),
            prev_regime="cautious", l1a_fresh_minutes=10, rag_empty=True, now_hhmm="04:00",
        )
        self.assertIn("⚠️", s)
        self.assertIn("RAG empty", s)

    def test_both_prefixes_rag_first_then_flip(self):
        s = ls.format_telegram_recap(
            regime="risk_off", sectors=["a", "b", "c"], narratives=self._narratives(),
            watchlist=self._wl(["A"]),
            prev_regime="risk_on", l1a_fresh_minutes=10, rag_empty=True, now_hhmm="04:00",
        )
        rag_idx = s.index("RAG empty")
        flip_idx = s.index("regime flipped")
        self.assertLess(rag_idx, flip_idx)

    def test_watchlist_three_or_fewer_no_ellipsis(self):
        s = ls.format_telegram_recap(
            regime="cautious", sectors=["a", "b", "c"], narratives=self._narratives(),
            watchlist=self._wl(["ADMR", "BBCA", "BMRI"]),
            prev_regime="cautious", l1a_fresh_minutes=10, rag_empty=False, now_hhmm="04:00",
        )
        self.assertIn("Watchlist:", s)
        self.assertIn("3 (ADMR, BBCA, BMRI)", s)
        self.assertNotIn("…", s)


if __name__ == "__main__":
    unittest.main()
