"""Pure helpers for L2 screening (spec #4).

No AI, no I/O. All functions deterministic so they unit-test without mocks.

- `promotion_decision`: PRD truth table (superlist / exitlist / drop).
- `format_judge_prompt` / `parse_judge_response`: openclaude per-ticker contract.
- `format_merge_prompt` / `parse_merge_response`: Opus final merge contract.
- `format_telegram_recap`: always-send recap template.
"""
from __future__ import annotations

import json
from typing import Literal

LABELS = {"superstrong", "strong", "weak", "redflag"}
PLANS = {"buy_at_price", "sell_at_price", "wait_bid_offer"}

Verdict = Literal["superlist", "exitlist", "drop"]


def promotion_decision(scores: dict[str, str], is_holding: bool) -> Verdict:
    """PRD truth table. Superlist wins over exitlist when both would trigger."""
    vals = list(scores.values())
    n_ss = vals.count("superstrong")
    n_s = vals.count("strong")
    n_r = vals.count("redflag")

    # Superlist rules (PRD §L2)
    if n_ss >= 1:
        return "superlist"
    if n_s >= 3:
        return "superlist"
    if n_s >= 2 and n_r == 0:
        return "superlist"

    # Exitlist (holdings only)
    if is_holding and n_r >= 2:
        return "exitlist"

    return "drop"


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
    return s


def parse_judge_response(raw: str) -> tuple[dict[str, str], str]:
    """Parse openclaude judge response. Returns (scores dict, rationale)."""
    s = _strip_fences(raw)
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"judge response not valid JSON: {e}") from e

    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("judge response missing 'scores' dict")

    required = {"price", "broker", "book", "narrative"}
    missing = required - set(scores)
    if missing:
        raise ValueError(f"judge response missing dims: {sorted(missing)}")

    for dim, label in scores.items():
        if label not in LABELS:
            raise ValueError(f"judge dim '{dim}' has invalid label '{label}' (must be in {sorted(LABELS)})")

    rationale = data.get("rationale", "")
    return {k: scores[k] for k in ("price", "broker", "book", "narrative")}, rationale


def format_judge_prompt(ticker: str, dims: dict, context: dict) -> str:
    """Per-ticker full-judge prompt for openclaude."""
    regime = context.get("regime", "")
    sectors = context.get("sectors", [])
    aggressiveness = context.get("aggressiveness", "")
    is_holding = bool(context.get("is_holding", False))

    return f"""You are the L2 per-ticker judge for an IDX equities portfolio.

# Context
- ticker: {ticker}
- regime: {regime}
- sectors (L1): {", ".join(sectors) if sectors else "<none>"}
- aggressiveness (L0): {aggressiveness}
- is_holding={is_holding}

# Rules
Score EACH of the 4 dims with EXACTLY one label from: superstrong | strong | weak | redflag
- price: 60-day price/volume/wyckoff/spring/vp-state/RS fact bundle
- broker: smart-money flow, SID direction, top-broker identity, konglo alignment
- book: yesterday's orderbook close snapshot (bid walls, offer walls, pressure side, 10m stance)
- narrative: thematic fit with today's regime + sector tilt

Guidance:
- spring_hit + confidence med/high → price dim minimum `strong`
- vp_state in {{weak_rally, distribution}} without spring → price dim redflag candidate
- is_holding: bias toward exit calls (redflag) if dims degrade; 2 redflags triggers exitlist
- konglo_in_l1_sectors → broker dim gets a boost

# Inputs
## Dim 1 — price / volume / wyckoff / spring / vp / RS
{json.dumps(dims.get(1, {}), ensure_ascii=False, default=str)}

## Dim 2 — broker + SID + konglo
{json.dumps(dims.get(2, {}), ensure_ascii=False, default=str)}

## Dim 3 — yesterday bid/offer
{json.dumps(dims.get(3, {}), ensure_ascii=False, default=str)}

## Dim 4 — narrative
{json.dumps(dims.get(4, {}), ensure_ascii=False, default=str)}

# Output (JSON only — no prose, no code fences)
{{"scores": {{"price": "...", "broker": "...", "book": "...", "narrative": "..."}}, "rationale": "<≤200 chars explaining the call>"}}
"""


def format_merge_prompt(promoted: list[dict], exits: list[dict], holdings: list[str], regime: str) -> str:
    """Opus merge prompt: assign current_plan per ticker + tidy details."""
    return f"""You are the L2 merge step. Assign a current_plan per ticker based on the judge scores.

# Plans
- buy_at_price: dim-3 shows whale bid at support + dim-1 accumulation; pilot buy
- sell_at_price: exit-list tickers OR dim-1 distribution + dim-2 smart-money out
- wait_bid_offer: clean above bid wall, whales parked below, or judge mixed — observe first

# Context
- regime: {regime}
- holdings: {", ".join(holdings) if holdings else "<none>"}

# Promoted (→ superlist)
{json.dumps(promoted, ensure_ascii=False, default=str)}

# Exits (→ exitlist)
{json.dumps(exits, ensure_ascii=False, default=str)}

# Output (JSON only — no prose, no code fences)
{{"TICKER": {{"current_plan": "buy_at_price|sell_at_price|wait_bid_offer", "details": "<≤120 chars>"}}, ...}}
"""


def parse_merge_response(raw: str) -> dict[str, dict]:
    """Parse Opus merge response. Validates current_plan enum."""
    s = _strip_fences(raw)
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"merge response not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("merge response must be a JSON object")

    for ticker, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"merge entry for {ticker} not an object")
        plan = entry.get("current_plan")
        if plan not in PLANS:
            raise ValueError(f"invalid current_plan for {ticker}: '{plan}' (must be in {sorted(PLANS)})")
    return data


def format_telegram_recap(
    superlist: list[dict],
    exitlist: list[dict],
    n_judged: int,
    regime: str,
    prev_superlist_count: int,
    now_hhmm: str,
) -> str:
    """Always-send recap. Empty superlist → short form. Otherwise top-3 per bucket."""
    if not superlist:
        return f"🧭 <b>L2 Screening — {now_hhmm}</b>\n\n0 promoted · {n_judged} judged · regime: {regime}\n\n<i>Scarlett · L2</i>"

    lines = [f"🧭 <b>L2 Screening — {now_hhmm}</b>"]
    delta = ""
    if prev_superlist_count != len(superlist):
        delta = f" (prev {prev_superlist_count})"
    lines.append(f"<b>{len(superlist)} promoted{delta}</b> · {len(exitlist)} exit · {n_judged} judged · regime: {regime}")
    lines.append("")
    lines.append("<b>Superlist:</b>")
    for item in superlist[:5]:
        lines.append(f"• <b>{item['ticker']}</b> [{item['current_plan']}] {item.get('details', '')}")
    if exitlist:
        lines.append("")
        lines.append("<b>Exit:</b>")
        for item in exitlist[:3]:
            lines.append(f"• <b>{item['ticker']}</b> [{item['current_plan']}] {item.get('details', '')}")
    lines.append("")
    lines.append("<i>Scarlett · L2</i>")
    return "\n".join(lines)
