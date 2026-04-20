import unittest
from unittest.mock import patch
import datetime as dt

from tools.trader import l1a_healthcheck as hc


class L1AHealthcheckTest(unittest.TestCase):
    def test_fresh_when_under_threshold(self):
        fresh_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)).isoformat()
        with patch.object(hc, "_fetch_last_insight_ts", return_value=fresh_ts):
            r = hc.check()
        self.assertTrue(r["fresh"])
        self.assertLess(r["last_seen_minutes_ago"], 120)
        self.assertEqual(r["threshold_minutes"], 120)

    def test_stale_when_over_threshold(self):
        stale_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=180)).isoformat()
        with patch.object(hc, "_fetch_last_insight_ts", return_value=stale_ts):
            r = hc.check()
        self.assertFalse(r["fresh"])
        self.assertGreater(r["last_seen_minutes_ago"], 120)

    def test_backend_unreachable_returns_fresh_false(self):
        with patch.object(hc, "_fetch_last_insight_ts", side_effect=ConnectionError):
            r = hc.check()
        self.assertFalse(r["fresh"])
        self.assertIsNone(r["last_seen_minutes_ago"])

    def test_empty_ts_returns_fresh_false(self):
        with patch.object(hc, "_fetch_last_insight_ts", return_value=""):
            r = hc.check()
        self.assertFalse(r["fresh"])
        self.assertIsNone(r["last_seen_minutes_ago"])

    def test_z_suffix_iso_parsed(self):
        fresh_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)).replace(microsecond=0)
        z = fresh_ts.isoformat().replace("+00:00", "Z")
        with patch.object(hc, "_fetch_last_insight_ts", return_value=z):
            r = hc.check()
        self.assertTrue(r["fresh"])
        self.assertLess(r["last_seen_minutes_ago"], 120)


if __name__ == "__main__":
    unittest.main()
