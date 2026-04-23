import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from tools.trader import l3_dim_gather

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "l3")


def _mk_tape_obj():
    """Build object with attrs matching tape_runner.TapeState so asdict works."""
    data = json.load(open(os.path.join(FIX, "tape_snapshot_ADMR.json")))
    # return as plain dict — code tolerates dict or dataclass
    return data


class TestGatherTape(unittest.TestCase):

    def _setup_dirs(self, tmpdir):
        ob_dir = os.path.join(tmpdir, "orderbook_state")
        rt_dir = os.path.join(tmpdir, "realtime")
        prior_dir = os.path.join(tmpdir, "prior")
        os.makedirs(ob_dir)
        os.makedirs(rt_dir)
        os.makedirs(prior_dir)
        shutil.copy(os.path.join(FIX, "orderbook_state_ADMR_now.json"), os.path.join(ob_dir, "ADMR.json"))
        shutil.copy(os.path.join(FIX, "orderbook_state_ADMR_prior.json"), os.path.join(prior_dir, "ADMR.json"))
        # bump running trade timestamps to be within last 10min of "now"
        now_ts = int(time.time())
        rt_out = os.path.join(rt_dir, "ADMR-run.jsonl")
        with open(os.path.join(FIX, "running_trade_ADMR.jsonl")) as fin, open(rt_out, "w") as fout:
            for i, line in enumerate(fin):
                row = json.loads(line)
                row["ts"] = now_ts - (9 - i) * 60  # spread over last ~9 min
                fout.write(json.dumps(row) + "\n")
        return ob_dir, rt_dir, prior_dir

    @patch("tools.trader.l3_dim_gather.tape_runner")
    @patch("tools.trader.l3_dim_gather.spring_detector")
    @patch("tools.trader.l3_dim_gather.api")
    def test_happy_path_full_dict(self, mock_api, mock_spring, mock_tape):
        mock_tape.snapshot.return_value = _mk_tape_obj()
        mock_spring.detect.return_value = json.load(open(os.path.join(FIX, "spring_detect_ADMR.json")))
        mock_api.get_price.return_value = 1860.0

        with tempfile.TemporaryDirectory() as d:
            ob_dir, rt_dir, prior_dir = self._setup_dirs(d)
            out = l3_dim_gather.gather_tape(
                "ADMR",
                orderbook_state_dir=ob_dir,
                running_trade_dir=rt_dir,
                prior_orderbook_path=os.path.join(prior_dir, "ADMR.json"),
            )
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["ticker"], "ADMR")
        self.assertEqual(out["tape_composite"], "healthy_markup")
        self.assertTrue(out["spring_confirmed"])
        self.assertIn(out["pattern"], ("spike", "gradient", "normal"))
        self.assertIsInstance(out["thick_wall_buy"], bool)
        self.assertIsInstance(out["thick_wall_buy_strong"], bool)
        self.assertEqual(out["price_now"], 1860.0)
        self.assertEqual(out["running_trade_count_10m"], 10)
        self.assertIsNotNone(out["running_trade_buy_ratio"])
        self.assertGreater(out["running_trade_buy_ratio"], 0.5)
        # wall_withdrawn: prior 1880 had 1.5M, now 350k → withdrawn by >5k
        self.assertTrue(out["wall_withdrawn"])

    @patch("tools.trader.l3_dim_gather.tape_runner")
    @patch("tools.trader.l3_dim_gather.spring_detector")
    @patch("tools.trader.l3_dim_gather.api")
    def test_missing_orderbook_unavailable(self, mock_api, mock_spring, mock_tape):
        mock_tape.snapshot.side_effect = FileNotFoundError("no orderbook")
        mock_spring.detect.return_value = {"is_spring": False}
        mock_api.get_price.return_value = 1860.0
        with tempfile.TemporaryDirectory() as d:
            out = l3_dim_gather.gather_tape(
                "ZZZZ",
                orderbook_state_dir=d,
                running_trade_dir=d,
                prior_orderbook_path=None,
            )
        self.assertEqual(out["status"], "unavailable")
        self.assertIn("unavailable", out["reason"].lower())

    @patch("tools.trader.l3_dim_gather.tape_runner")
    @patch("tools.trader.l3_dim_gather.spring_detector")
    @patch("tools.trader.l3_dim_gather.api")
    def test_missing_prior_no_wall_withdrawn(self, mock_api, mock_spring, mock_tape):
        mock_tape.snapshot.return_value = _mk_tape_obj()
        mock_spring.detect.return_value = json.load(open(os.path.join(FIX, "spring_detect_ADMR.json")))
        mock_api.get_price.return_value = 1860.0
        with tempfile.TemporaryDirectory() as d:
            ob_dir = os.path.join(d, "ob")
            os.makedirs(ob_dir)
            shutil.copy(os.path.join(FIX, "orderbook_state_ADMR_now.json"), os.path.join(ob_dir, "ADMR.json"))
            out = l3_dim_gather.gather_tape(
                "ADMR",
                orderbook_state_dir=ob_dir,
                running_trade_dir=d,
                prior_orderbook_path=None,
            )
        self.assertFalse(out["wall_withdrawn"])
        self.assertFalse(out["thick_wall_buy_strong"])


if __name__ == "__main__":
    unittest.main()
