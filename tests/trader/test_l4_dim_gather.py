import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

from tools.trader.l4_dim_gather import gather_structure, gather_orderbook, gather_last_tape_note

FIX = Path(__file__).resolve().parent / "fixtures" / "l4"


@dataclass
class _SP:
    price: float
    time: str = "2026-04-18"
    strength: int = 3


@dataclass
class _MS:
    trend: str = "uptrend"
    wyckoff_phase: str = "accumulation"
    support: float = 1820
    resistance: float = 1960
    last_swing_low: _SP = None
    last_swing_high: _SP = None


def _ok_structure_fn(ticker, days=30):
    return _MS(
        last_swing_low=_SP(price=1830),
        last_swing_high=_SP(price=1920, strength=2),
    )


def _ok_indicators_fn(ticker, timeframe="1d", limit=60):
    return {"ticker": ticker, "close": 1870, "atr_14": 32, "high_60d": 1960, "low_60d": 1620}


class GatherStructureTest(unittest.TestCase):
    def test_happy_path(self):
        r = gather_structure("ADMR", market_structure_fn=_ok_structure_fn, indicators_fn=_ok_indicators_fn)
        self.assertEqual(r["structure"]["trend"], "uptrend")
        self.assertEqual(r["structure"]["support"], 1820)
        self.assertEqual(r["structure"]["last_swing_low"]["price"], 1830)
        self.assertEqual(r["atr"], 32)
        self.assertEqual(r["close"], 1870)
        self.assertEqual(r["hi60"], 1960)
        self.assertEqual(r["lo60"], 1620)
        self.assertEqual(r["context_missing"], [])

    def test_indicators_fail_structure_ok(self):
        def bad(t, timeframe="1d", limit=60):
            raise RuntimeError("backend down")
        r = gather_structure("ADMR", market_structure_fn=_ok_structure_fn, indicators_fn=bad)
        self.assertEqual(r["structure"]["trend"], "uptrend")
        self.assertIsNone(r["atr"])
        self.assertTrue(any("indicators" in m for m in r["context_missing"]))

    def test_structure_fail_indicators_ok(self):
        def bad(t, days=30):
            raise RuntimeError("no data")
        r = gather_structure("ADMR", market_structure_fn=bad, indicators_fn=_ok_indicators_fn)
        self.assertEqual(r["structure"], {})
        self.assertEqual(r["atr"], 32)
        self.assertTrue(any("structure" in m for m in r["context_missing"]))

    def test_both_fail(self):
        def bad1(t, days=30): raise RuntimeError("x")
        def bad2(t, timeframe="1d", limit=60): raise RuntimeError("y")
        r = gather_structure("ADMR", market_structure_fn=bad1, indicators_fn=bad2)
        self.assertEqual(len(r["context_missing"]), 2)

    def test_indicators_error_payload(self):
        def err_ind(t, timeframe="1d", limit=60):
            return {"error": "no price data"}
        r = gather_structure("ADMR", market_structure_fn=_ok_structure_fn, indicators_fn=err_ind)
        self.assertIsNone(r["atr"])
        self.assertTrue(any("no price data" in m for m in r["context_missing"]))

    def test_missing_swing_low(self):
        def ms_no_swing(t, days=30):
            return _MS(last_swing_low=None, last_swing_high=None)
        r = gather_structure("ADMR", market_structure_fn=ms_no_swing, indicators_fn=_ok_indicators_fn)
        self.assertIsNone(r["structure"]["last_swing_low"])


class GatherOrderbookTest(unittest.TestCase):
    def test_reads_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            src = FIX / "orderbook_ADMR_fresh.json"
            dst = Path(d) / "ADMR.json"
            dst.write_text(src.read_text())
            ob = gather_orderbook("ADMR", d)
        self.assertIsNotNone(ob)
        self.assertEqual(ob["best_offer"], 1875)
        self.assertEqual(ob["last_price"], 1875)

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(gather_orderbook("NONE", d))

    def test_corrupt_json_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "BAD.json").write_text("not json{")
            self.assertIsNone(gather_orderbook("BAD", d))


class GatherLastTapeNoteTest(unittest.TestCase):
    def test_returns_latest_for_ticker(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.jsonl"
            p.write_text(
                json.dumps({"ts": "1", "ticker": "ADMR", "label": "intact"}) + "\n" +
                json.dumps({"ts": "2", "ticker": "BUMI", "label": "weakening"}) + "\n" +
                json.dumps({"ts": "3", "ticker": "ADMR", "label": "strengthening"}) + "\n"
            )
            note = gather_last_tape_note("ADMR", str(p))
        self.assertEqual(note["label"], "strengthening")

    def test_no_match_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.jsonl"
            p.write_text(json.dumps({"ticker": "BUMI", "label": "x"}) + "\n")
            self.assertIsNone(gather_last_tape_note("ADMR", str(p)))

    def test_missing_file_returns_none(self):
        self.assertIsNone(gather_last_tape_note("ADMR", "/nonexistent/path/notes.jsonl"))

    def test_skips_corrupt_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "notes.jsonl"
            p.write_text(
                "not json\n" +
                json.dumps({"ticker": "ADMR", "label": "ok"}) + "\n"
            )
            note = gather_last_tape_note("ADMR", str(p))
        self.assertEqual(note["label"], "ok")


if __name__ == "__main__":
    unittest.main()
