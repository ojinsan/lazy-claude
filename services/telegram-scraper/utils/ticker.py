"""Ticker extraction utilities."""
from __future__ import annotations

import csv
import re
from pathlib import Path


def load_stocklist(path: Path | None = None) -> set[str]:
    """Load valid stock codes from stocklist.csv."""
    if path is None:
        path = Path(__file__).parent.parent / "stocklist.csv"

    if not path.exists():
        return set()

    codes = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("code", "").strip().upper()
            if code and len(code) == 4:
                codes.add(code)

    return codes


class TickerExtractor:
    """Extract valid stock tickers from text."""

    # Pattern for potential ticker codes (2-6 uppercase letters)
    TICKER_PATTERN = re.compile(r"\b([A-Z]{2,6})\b")

    def __init__(self, valid_codes: set[str] | None = None):
        self.valid_codes = valid_codes or load_stocklist()

    def extract(self, text: str) -> list[str]:
        """Extract valid tickers from text."""
        if not text:
            return []

        # Find all potential matches
        matches = self.TICKER_PATTERN.findall(text.upper())

        # Filter to valid codes
        found = []
        seen = set()
        for match in matches:
            if match in self.valid_codes and match not in seen:
                found.append(match)
                seen.add(match)

        return found

    def extract_unique(self, texts: list[str]) -> list[str]:
        """Extract unique tickers from multiple texts."""
        seen = set()
        result = []
        for text in texts:
            for ticker in self.extract(text):
                if ticker not in seen:
                    result.append(ticker)
                    seen.add(ticker)
        return result
