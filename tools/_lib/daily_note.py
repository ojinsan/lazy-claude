"""Shared daily-note append helper. Used by L0 now, L1/L3/L5 later.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md §3.2.
"""
from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
VAULT_DAILY_DIR = str(WORKSPACE / "vault" / "daily")


def append_section(date_str: str, section_heading: str, body: str) -> str:
    """Append a `### {section_heading}` block under `## Auto-Appended` in
    vault/daily/{date_str}.md. Create file with header if missing.

    Returns absolute path to the file.
    """
    path = os.path.join(VAULT_DAILY_DIR, f"{date_str}.md")
    os.makedirs(VAULT_DAILY_DIR, exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {date_str}\n\n## Auto-Appended\n\n")

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"### {section_heading}\n{body}\n\n")

    return path
