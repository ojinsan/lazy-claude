"""
Konglo (conglomerate) group loader. Read-only — never writes to the JSON source.
Composes nothing; is imported by konglo_flow.py and other M3 tools.
"""
import json
import sys
from pathlib import Path
from typing import Optional

_DATA_FILE = Path(__file__).parent / "data" / "konglo_list.json"
_INDEX: Optional[dict] = None


def _build_index() -> dict:
    raw = json.loads(_DATA_FILE.read_text())
    groups = raw["conglomerates"]
    by_id: dict[str, dict] = {}
    by_ticker: dict[str, list[dict]] = {}

    for g in groups:
        entry = {
            "id": g["id"],
            "name": g["name"],
            "owner": g.get("owner", ""),
            "market_power": g.get("market_power", ""),
            "sectors": g.get("sectors", []),
            "notes": g.get("description", ""),
            "tickers": [s["ticker"] for s in g.get("stocks", [])],
        }
        by_id[g["id"]] = entry
        for stock in g.get("stocks", []):
            by_ticker.setdefault(stock["ticker"], []).append(entry)

    return {"by_id": by_id, "by_ticker": by_ticker, "groups": groups}


def _idx() -> dict:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def load() -> dict:
    return _idx()


def group_for(ticker: str) -> Optional[dict]:
    """First group for ticker (most tickers belong to one group)."""
    hits = _idx()["by_ticker"].get(ticker.upper())
    return hits[0] if hits else None


def groups_for(ticker: str) -> list[dict]:
    """All groups containing ticker (some tickers span 2 groups, e.g. BREN)."""
    return _idx()["by_ticker"].get(ticker.upper(), [])


def tickers_for_group(group_id: str) -> list[str]:
    g = _idx()["by_id"].get(group_id)
    return g["tickers"] if g else []


def peer_tickers(ticker: str) -> list[str]:
    """Sibling tickers in same group(s), excluding self."""
    t = ticker.upper()
    seen: set[str] = set()
    for g in groups_for(t):
        for peer in g["tickers"]:
            if peer != t:
                seen.add(peer)
    return sorted(seen)


def groups_by_sector(sector: str) -> list[dict]:
    sl = sector.lower()
    return [
        g for g in _idx()["by_id"].values()
        if any(sl in s.lower() for s in g.get("sectors", []))
    ]


if __name__ == "__main__":
    import argparse, pprint
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["lookup", "peers", "group", "sector"])
    p.add_argument("arg")
    args = p.parse_args()

    if args.cmd == "lookup":
        result = groups_for(args.arg)
        pprint.pprint(result if result else {"error": f"{args.arg} not in any group"})
    elif args.cmd == "peers":
        pprint.pprint(peer_tickers(args.arg))
    elif args.cmd == "group":
        pprint.pprint(tickers_for_group(args.arg))
    elif args.cmd == "sector":
        pprint.pprint(groups_by_sector(args.arg))
