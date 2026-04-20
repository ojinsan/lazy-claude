import os
import tempfile
import unittest
from unittest.mock import patch

from tools._lib import daily_note as dn


class AppendCreatesFileIfMissingTest(unittest.TestCase):
    def test_creates_file_with_header_then_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dn, "VAULT_DAILY_DIR", tmp):
                dn.append_section(
                    date_str="2026-04-20",
                    section_heading="L0 — 03:00",
                    body="Balance Rp 19.6M. Aggressiveness: defensive.",
                )
                path = os.path.join(tmp, "2026-04-20.md")
                self.assertTrue(os.path.exists(path))
                with open(path) as f:
                    content = f.read()
        self.assertIn("# 2026-04-20", content)
        self.assertIn("## Auto-Appended", content)
        self.assertIn("### L0 — 03:00", content)
        self.assertIn("Balance Rp 19.6M. Aggressiveness: defensive.", content)


class AppendPreservesExistingContentTest(unittest.TestCase):
    def test_existing_sections_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dn, "VAULT_DAILY_DIR", tmp):
                existing = "# 2026-04-20\n\n## Auto-Appended\n\n### L0 — 03:00\nold body\n"
                path = os.path.join(tmp, "2026-04-20.md")
                with open(path, "w") as f:
                    f.write(existing)
                dn.append_section(
                    date_str="2026-04-20",
                    section_heading="L1 — 04:00",
                    body="Regime: cautious.",
                )
                with open(path) as f:
                    content = f.read()
        self.assertIn("### L0 — 03:00\nold body", content)
        self.assertIn("### L1 — 04:00\nRegime: cautious.", content)
        # L0 section appears before L1 section (chronological)
        self.assertLess(content.index("### L0 — 03:00"), content.index("### L1 — 04:00"))
