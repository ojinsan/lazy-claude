import unittest
from unittest.mock import patch

from tools._lib import claude_model as cm


class FallbackTest(unittest.TestCase):
    def test_opus_success_returns_opus_result(self):
        with patch.object(cm, "_call_opus", return_value="opus-ok"):
            out = cm.run("hi", model="opus", fallback="openclaude")
        self.assertEqual(out, "opus-ok")

    def test_opus_429_fallback_to_openclaude(self):
        with patch.object(cm, "_call_opus", side_effect=cm.RateLimitError("429")), \
             patch.object(cm, "_call_openclaude", return_value="oc-ok"):
            out = cm.run("hi", model="opus", fallback="openclaude")
        self.assertEqual(out, "oc-ok")

    def test_both_fail_raises_model_error(self):
        with patch.object(cm, "_call_opus", side_effect=cm.RateLimitError("429")), \
             patch.object(cm, "_call_openclaude", side_effect=RuntimeError("boom")):
            with self.assertRaises(cm.ModelError):
                cm.run("hi", model="opus", fallback="openclaude")

    def test_openclaude_primary_fallback_to_opus(self):
        with patch.object(cm, "_call_openclaude", side_effect=cm.RateLimitError("429")), \
             patch.object(cm, "_call_opus", return_value="opus-ok"):
            out = cm.run("hi", model="openclaude", fallback="opus")
        self.assertEqual(out, "opus-ok")


if __name__ == "__main__":
    unittest.main()
