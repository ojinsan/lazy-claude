"""L3 monitoring — pure helpers (prompt build, parse, gate, merge, telegram).

No I/O, no API calls. Unit-testable end-to-end. Imports only stdlib.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

LABELS = ("intact", "strengthening", "weakening", "broken")
Label = Literal["intact", "strengthening", "weakening", "broken"]
PriceMode = Literal["buy_at_price", "sell_at_price", "wait_bid_offer"]

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
PROXIMITY_PCT = 0.005  # 0.5%


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    m = _FENCE_RE.match(raw)
    return m.group(1).strip() if m else raw


def format_judge_prompt(ticker: str, dim: dict[str, Any], context: dict[str, Any]) -> str:
    return (
        f"You are an intraday tape judge for IDX ticker {ticker}.\n"
        f"Return STRICT JSON: {{\"label\": one of {list(LABELS)}, "
        f"\"buy_now\": bool, \"thesis_break\": bool, \"rationale\": short string}}.\n\n"
        f"Labels meaning:\n"
        f"- intact: plan still valid, no change\n"
        f"- strengthening: accumulation/spring building; set buy_now=true only when tape + thick-wall confirm entry NOW\n"
        f"- weakening: distribution building; wait\n"
        f"- broken: thesis violated; exit or drop (thesis_break=true)\n\n"
        f"Ticker: {ticker}\n"
        f"Tape dim: {json.dumps(dim, sort_keys=True)}\n"
        f"Context: is_holding={context.get('is_holding')} is_superlist={context.get('is_superlist')} "
        f"is_exitlist={context.get('is_exitlist')} regime={context.get('regime')} "
        f"sectors={context.get('sectors')} intraday_notch={context.get('intraday_notch')}\n"
        f"Prior plan: {json.dumps(context.get('prior_plan'))}\n"
        f"Respond with ONE JSON object only.\n"
    )


def parse_judge_response(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"not json: {e}") from e
    for key in ("label", "buy_now", "thesis_break", "rationale"):
        if key not in data:
            raise ValueError(f"missing key: {key}")
    if data["label"] not in LABELS:
        raise ValueError(f"unknown label: {data['label']!r}")
    if not isinstance(data["buy_now"], bool) or not isinstance(data["thesis_break"], bool):
        raise ValueError("buy_now / thesis_break must be bool")
    return data


def _price_near(price_now: float, plan: dict[str, Any]) -> bool:
    target = plan.get("price")
    if target is None or price_now <= 0:
        return False
    return abs(price_now - target) / target <= PROXIMITY_PCT


def buy_now_gate(
    judge: dict[str, Any],
    prior_plan: dict[str, Any] | None,
    price_now: float,
    intraday_notch: int,
    fired_set: set[str],
    dim: dict[str, Any],
    is_superlist: bool,
    ticker: str = "",
) -> bool:
    if not is_superlist:
        return False
    if not judge.get("buy_now"):
        return False
    if ticker and ticker in fired_set:
        return False
    if intraday_notch < 0:
        return False
    if not prior_plan or prior_plan.get("mode") not in ("buy_at_price", "wait_bid_offer"):
        return False
    if not _price_near(price_now, prior_plan):
        return False
    setup_hit = (
        dim.get("thick_wall_buy_strong") is True
        or (dim.get("spring_confirmed") and dim.get("spring_confidence") in ("med", "high"))
        or (dim.get("tape_composite") in ("spring_ready", "ideal_markup") and dim.get("tape_confidence") in ("med", "high"))
    )
    return bool(setup_hit)


def merge_plan_update(
    ticker: str,
    label: Label,
    buy_now: bool,
    prior_plan: dict[str, Any] | None,
    is_holding: bool,
) -> dict[str, Any] | None:
    if label == "intact":
        return None
    if label == "broken" and is_holding:
        price = (prior_plan or {}).get("price")
        return {"current_plan": {"mode": "sell_at_price", "price": price}, "details": f"L3 broken: thesis violated on {ticker}"}
    if label == "broken":
        return {"current_plan": None, "details": f"L3 broken: drop from superlist {ticker}"}
    if label == "weakening":
        price = (prior_plan or {}).get("price")
        return {"current_plan": {"mode": "wait_bid_offer", "price": price}, "details": f"L3 weakening: wait re-test {ticker}"}
    mode = (prior_plan or {}).get("mode", "buy_at_price")
    price = (prior_plan or {}).get("price")
    return {"current_plan": {"mode": mode, "price": price}, "details": f"L3 strengthening{' BUY-NOW' if buy_now else ''} {ticker}"}


def format_intraday_notch_alert(ihsg_pct: float, foreign_delta: float) -> str:
    return (
        f"L3 intraday notch -1 — IHSG {ihsg_pct:+.1f}%, foreign net flow Δ{foreign_delta:+.0f}. "
        f"Size review on holdings + superlist."
    )


def format_telegram_events(events: list[dict[str, Any]]) -> str | None:
    if not events:
        return None
    lines = []
    for e in events:
        k = e.get("kind")
        if k == "buy_now":
            lines.append(f"🟢 L3 BUY-NOW: {e['ticker']} @ {e['price']} — {e['rationale']}. L4 invoked.")
        elif k == "thesis_break":
            lines.append(f"🔴 L3 THESIS BREAK: {e['ticker']} — {e['rationale']}")
        elif k == "notch":
            lines.append(e["message"])
        else:
            lines.append(f"L3: {k} — {e}")
    return "\n".join(lines)


def format_opus_confirm_prompt(
    ticker: str, dim: dict[str, Any], judge: dict[str, Any], prior_plan: dict[str, Any] | None, price_now: float,
) -> str:
    return (
        f"Confirm BUY-NOW for {ticker}. Full intraday 4-dim context below.\n"
        f"Tape dim: {json.dumps(dim, sort_keys=True)}\n"
        f"openclaude judge: {json.dumps(judge, sort_keys=True)}\n"
        f"Prior plan: {json.dumps(prior_plan)}\n"
        f"Price now: {price_now}\n\n"
        f"Return STRICT JSON: {{\"approve\": bool, \"size_hint\": string or null, \"rationale\": short string}}.\n"
        f"Reject (approve=false) if tape thin, regime rolling over, or size unwise. Approve only on high-conviction setup.\n"
    )


def parse_opus_confirm_response(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as e:
        raise ValueError(f"not json: {e}") from e
    for key in ("approve", "size_hint", "rationale"):
        if key not in data:
            raise ValueError(f"missing key: {key}")
    if not isinstance(data["approve"], bool):
        raise ValueError("approve must be bool")
    return data


def format_daily_note_events(events: list[dict[str, Any]], hhmm: str) -> str | None:
    if not events:
        return None
    lines = [f"L3 {hhmm}:"]
    for e in events:
        k = e.get("kind")
        if k == "buy_now":
            lines.append(f"- BUY-NOW {e['ticker']} @ {e.get('price')} — {e.get('rationale')}")
        elif k == "thesis_break":
            lines.append(f"- THESIS BREAK {e['ticker']} — {e.get('rationale')}")
        elif k == "notch":
            lines.append(f"- NOTCH: {e.get('message')}")
        else:
            lines.append(f"- {k}: {e}")
    return "\n".join(lines)
