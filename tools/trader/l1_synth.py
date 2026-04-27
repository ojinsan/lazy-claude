"""L1 Insight synth — pure validators + pool union + recap formatter.

No I/O, no AI. Imported by `playbooks/trader/layer-1-insight.md` after
Opus returns its draft synthesis.
"""
from __future__ import annotations

from typing import Iterable

from tools._lib.current_trade import Holding, ListItem, Narrative

VALID_REGIMES = {"risk_on", "cautious", "risk_off"}


def valid_regime(s) -> bool:
    return s in VALID_REGIMES


def sectors_count_valid(sectors: list[str]) -> bool:
    if not (3 <= len(sectors) <= 5):
        return False
    for s in sectors:
        if not isinstance(s, str) or not s or s != s.lower():
            return False
    return True


def narratives_count_valid(narratives: list) -> bool:
    return 3 <= len(narratives) <= 5


def narrative_anchors_in_watchlist(narratives: list, watchlist: list) -> bool:
    wl_tickers = {_ticker_of(w).upper() for w in watchlist if _ticker_of(w)}
    for n in narratives:
        t = _ticker_of(n)
        if not t or t.upper() not in wl_tickers:
            return False
    return True


def _ticker_of(item) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if hasattr(item, "ticker"):
        return str(item.ticker)
    if isinstance(item, dict):
        return str(item.get("ticker") or "")
    return ""


def _extract_tickers(items: Iterable) -> list[str]:
    out = []
    for it in items or []:
        t = _ticker_of(it)
        if t:
            out.append(t.upper())
    return out


def union_candidate_pool(rag_top, broker_flow_hapcu, broker_flow_retail_avoider,
                         lark_seed, holdings) -> list[str]:
    """Deduped union preserving first-seen order. Holdings always included."""
    if isinstance(broker_flow_retail_avoider, dict):
        ra_items = broker_flow_retail_avoider.get("tickers") or []
    else:
        ra_items = broker_flow_retail_avoider or []
    pools = [rag_top, broker_flow_hapcu, ra_items, lark_seed, holdings]
    seen: set[str] = set()
    out: list[str] = []
    for pool in pools:
        for t in _extract_tickers(pool):
            if t not in seen:
                seen.add(t)
                out.append(t)
    return out


def format_telegram_recap(
    regime: str,
    sectors: list[str],
    narratives: list,
    watchlist: list,
    prev_regime: str,
    l1a_fresh_minutes: int,
    rag_empty: bool,
    now_hhmm: str = "04:00",
) -> str:
    lines: list[str] = []
    if rag_empty:
        lines.append("⚠️ <b>RAG empty</b>")
    if prev_regime and regime and prev_regime != regime:
        lines.append(f"⚠️ <b>regime flipped:</b> {prev_regime} → {regime}")
    lines.append(f"🌍 <b>L1 Insight — {now_hhmm}</b>")
    lines.append("")
    lines.append(f"<b>Regime:</b> {regime.upper()}")
    if sectors:
        lines.append("<b>Sectors:</b> " + ", ".join(sectors))
    lines.append("")
    if narratives:
        lines.append(f"<b>Themes ({len(narratives)}):</b>")
        for n in narratives:
            content = getattr(n, "content", None) or (n.get("content") if isinstance(n, dict) else "")
            lines.append(f"• {content}")
    wl_tickers = [_ticker_of(w).upper() for w in watchlist if _ticker_of(w)]
    n = len(wl_tickers)
    wl_str = ", ".join(wl_tickers[:3]) + (" …" if n > 3 else "")
    lines.append("")
    lines.append(f"<b>Watchlist:</b> {n} ({wl_str})")
    lines.append("")
    lines.append(f"<i>Scarlett · L1 · fresh {l1a_fresh_minutes}min</i>")
    return "\n".join(lines)
