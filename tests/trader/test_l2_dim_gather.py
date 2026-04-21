"""Unit tests for tools/trader/l2_dim_gather.py — 4 gatherers, all I/O mocked."""
from __future__ import annotations

import json
import pathlib
import unittest
from unittest.mock import patch, MagicMock

from tools.trader import l2_dim_gather as dg

FIX = pathlib.Path(__file__).parent / "fixtures" / "l2"


def _load(name: str):
    return json.loads((FIX / name).read_text())


class GatherPriceTest(unittest.TestCase):
    def _common_mocks(self, ticker="ADMR", spring_hit=False, spring_conf="low", vp_state="accumulation", wyckoff_phase="ACCUMULATION"):
        bars = _load(f"eod_bars_{ticker}.json")
        wyck = MagicMock()
        wyck.phase = wyckoff_phase
        wyck.structure = "HH-HL"
        wyck.volume_pattern = "HEALTHY"
        wyck.confidence = "HIGH"
        wyck.signals = ["spring"] if spring_hit else []
        return {
            "price_history": bars,
            "wyckoff": wyck,
            "spring": {"is_spring": spring_hit, "confidence": spring_conf},
            "vp": {"state": vp_state, "note": "x"},
            "rs_result": [{"ticker": ticker, "rs": 4.2, "return_pct": 5.0, "ihsg_ret": 0.8, "days": 20}],
        }

    def test_spring_hit_promotes_judge_floor(self):
        m = self._common_mocks(spring_hit=True, spring_conf="high")
        with patch.object(dg.api, "get_price_history", return_value=m["price_history"]), \
             patch.object(dg.wyckoff, "analyze_wyckoff", return_value=m["wyckoff"]), \
             patch.object(dg.spring_detector, "detect", return_value=m["spring"]), \
             patch.object(dg.vp_analyzer, "classify", return_value=m["vp"]), \
             patch.object(dg.relative_strength, "rank", return_value=m["rs_result"]):
            out = dg.gather_price("ADMR", sector="coal")
        self.assertTrue(out["spring_hit"])
        self.assertEqual(out["spring_confidence"], "high")
        self.assertEqual(out["judge_floor"], "strong")

    def test_spring_low_confidence_no_floor(self):
        m = self._common_mocks(spring_hit=True, spring_conf="low")
        with patch.object(dg.api, "get_price_history", return_value=m["price_history"]), \
             patch.object(dg.wyckoff, "analyze_wyckoff", return_value=m["wyckoff"]), \
             patch.object(dg.spring_detector, "detect", return_value=m["spring"]), \
             patch.object(dg.vp_analyzer, "classify", return_value=m["vp"]), \
             patch.object(dg.relative_strength, "rank", return_value=m["rs_result"]):
            out = dg.gather_price("ADMR", sector="coal")
        self.assertIsNone(out.get("judge_floor"))

    def test_vp_redflag_when_weak_rally_no_spring(self):
        m = self._common_mocks(spring_hit=False, vp_state="weak_rally")
        with patch.object(dg.api, "get_price_history", return_value=m["price_history"]), \
             patch.object(dg.wyckoff, "analyze_wyckoff", return_value=m["wyckoff"]), \
             patch.object(dg.spring_detector, "detect", return_value=m["spring"]), \
             patch.object(dg.vp_analyzer, "classify", return_value=m["vp"]), \
             patch.object(dg.relative_strength, "rank", return_value=m["rs_result"]):
            out = dg.gather_price("ADMR", sector="coal")
        self.assertTrue(out["vp_redflag"])

    def test_vp_redflag_canceled_by_spring(self):
        m = self._common_mocks(spring_hit=True, spring_conf="med", vp_state="distribution")
        with patch.object(dg.api, "get_price_history", return_value=m["price_history"]), \
             patch.object(dg.wyckoff, "analyze_wyckoff", return_value=m["wyckoff"]), \
             patch.object(dg.spring_detector, "detect", return_value=m["spring"]), \
             patch.object(dg.vp_analyzer, "classify", return_value=m["vp"]), \
             patch.object(dg.relative_strength, "rank", return_value=m["rs_result"]):
            out = dg.gather_price("ADMR", sector="coal")
        self.assertFalse(out["vp_redflag"])
        self.assertEqual(out["judge_floor"], "strong")

    def test_missing_bars_returns_unavailable(self):
        with patch.object(dg.api, "get_price_history", side_effect=Exception("boom")):
            out = dg.gather_price("XXXX", sector="coal")
        self.assertEqual(out["status"], "unavailable")
        self.assertIn("boom", out["reason"])


class GatherBrokerTest(unittest.TestCase):
    def test_merges_hapcu_retail_sid_broker_konglo(self):
        hapcu = _load("hapcu_cache.json")
        retail = _load("retail_cache.json")
        sid_obj = MagicMock()
        sid_obj.ticker = "ADMR"
        sid_obj.direction = "accumulation"
        sid_obj.streak_days = 5
        sid_obj.change_pct = 8.4
        bp_obj = MagicMock()
        bp_obj.key_insight = "smart money buying 3 days"
        bp_obj.top_buyers = [MagicMock(code="CG", role="smart", net_value=18500000000)]
        bp_obj.top_sellers = []
        with patch.object(dg.sid_tracker, "check_sid", return_value=sid_obj), \
             patch.object(dg.broker_profile, "analyze_players", return_value=bp_obj), \
             patch.object(dg.konglo_loader, "group_for", return_value={"id": "astra", "sector": "coal", "name": "Astra"}):
            out = dg.gather_broker("ADMR", hapcu, retail, l1_sectors=["coal", "banking"])
        self.assertEqual(out["hapcu_net_buy"], 42800000000)
        self.assertEqual(out["retail_ratio"], 13.375)
        self.assertEqual(out["sid_direction"], "accumulation")
        self.assertEqual(out["sid_streak_days"], 5)
        self.assertTrue(out["konglo_in_l1_sectors"])
        self.assertIsNotNone(out.get("top_buyer_code"))

    def test_konglo_not_in_sectors(self):
        hapcu = _load("hapcu_cache.json")
        retail = _load("retail_cache.json")
        sid_obj = MagicMock()
        sid_obj.ticker = "ADMR"
        sid_obj.direction = "accumulation"
        sid_obj.streak_days = 5
        sid_obj.change_pct = 8.4
        bp_obj = MagicMock()
        bp_obj.key_insight = "x"
        bp_obj.top_buyers = []
        bp_obj.top_sellers = []
        with patch.object(dg.sid_tracker, "check_sid", return_value=sid_obj), \
             patch.object(dg.broker_profile, "analyze_players", return_value=bp_obj), \
             patch.object(dg.konglo_loader, "group_for", return_value={"id": "x", "sector": "tech", "name": "X"}):
            out = dg.gather_broker("ADMR", hapcu, retail, l1_sectors=["coal", "banking"])
        self.assertFalse(out["konglo_in_l1_sectors"])

    def test_missing_ticker_in_caches_still_returns_dict(self):
        with patch.object(dg.sid_tracker, "check_sid", side_effect=Exception("no data")), \
             patch.object(dg.broker_profile, "analyze_players", side_effect=Exception("no data")), \
             patch.object(dg.konglo_loader, "group_for", return_value=None):
            out = dg.gather_broker("XXXX", {"calcs": []}, {"tickers": []}, l1_sectors=[])
        self.assertIsNone(out.get("hapcu_net_buy"))
        self.assertIsNone(out.get("retail_ratio"))
        self.assertFalse(out["konglo_in_l1_sectors"])


class GatherBookTest(unittest.TestCase):
    def test_reads_orderbook_state_and_notes(self):
        with patch.object(dg, "_orderbook_state_path", return_value=str(FIX / "orderbook_state_ADMR.json")), \
             patch.object(dg, "_latest_notes_path", return_value=str(FIX / "notes_10m_latest.jsonl")):
            out = dg.gather_book("ADMR")
        self.assertIn("last_price", out)
        self.assertIn("bid_walls_top3", out)
        self.assertIn("offer_walls_top3", out)
        self.assertIn("stance", out)

    def test_missing_state_returns_unavailable(self):
        with patch.object(dg, "_orderbook_state_path", return_value=str(FIX / "does_not_exist.json")), \
             patch.object(dg, "_latest_notes_path", return_value=str(FIX / "notes_10m_latest.jsonl")):
            out = dg.gather_book("ADMR")
        self.assertEqual(out["status"], "unavailable")

    def test_state_present_notes_missing_still_returns_partial(self):
        with patch.object(dg, "_orderbook_state_path", return_value=str(FIX / "orderbook_state_ADMR.json")), \
             patch.object(dg, "_latest_notes_path", return_value=None):
            out = dg.gather_book("ADMR")
        self.assertIn("last_price", out)
        self.assertIsNone(out.get("stance"))


class GatherNarrativeTest(unittest.TestCase):
    def test_hit_in_narratives(self):
        narratives = _load("narratives.json")
        out = dg.gather_narrative("ADMR", narratives)
        self.assertTrue(out["hit"])
        self.assertIn("Coal", out["content"])
        self.assertEqual(out["confidence"], 82)

    def test_miss_in_narratives(self):
        narratives = _load("narratives.json")
        out = dg.gather_narrative("BUMI", narratives)
        self.assertFalse(out["hit"])
        self.assertIsNone(out["content"])


if __name__ == "__main__":
    unittest.main()
