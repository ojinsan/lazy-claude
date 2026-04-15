#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from typing import Iterable

import requests

from config import load_env

API_TIMEOUT = 30
PARSE_MODE = "HTML"
BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
THREAD_ID_ENV = "TELEGRAM_MESSAGE_THREAD_ID"


def _escape(value: object) -> str:
    text = str(value or "—").strip()
    return html.escape(text or "—", quote=False)


def _compact(value: object, default: str = "none") -> str:
    text = str(value or "").strip()
    return text or default


def _number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = (
        text.replace("Rp", "")
        .replace("rp", "")
        .replace("%", "")
        .replace(",", "")
        .replace("_", "")
        .strip()
    )
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _format_idr(value: object) -> str:
    num = _number(value)
    if num is None:
        text = str(value or "—").strip()
        if not text:
            return "—"
        return text if text.lower().startswith("rp") else f"Rp {text}"
    if num.is_integer():
        return f"Rp {int(num):,}"
    return f"Rp {num:,.2f}"


def _format_percent(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "—"
    if text.endswith("%"):
        return text
    num = _number(text)
    if num is None:
        return text
    if num.is_integer():
        return f"{int(num)}%"
    return f"{num:.2f}%"


def _format_shares(value: object) -> str:
    num = _number(value)
    if num is None:
        return _compact(value, "—")
    if num.is_integer():
        return f"{int(num):,}"
    return f"{num:,.2f}"


def _format_pre(fields: Iterable[tuple[str, object]]) -> str:
    rows = [(label, str(value if value not in (None, "") else "—")) for label, value in fields]
    width = max(len(label) for label, _ in rows)
    body = "\n".join(f"{label.ljust(width)} : {value}" for label, value in rows)
    return f"<pre>{_escape(body)}</pre>"


def _render_message(emoji: str, title: str, takeaway: str, fields: Iterable[tuple[str, object]], footer: str | None = None) -> str:
    parts = [f"{emoji} <b>{_escape(title)}</b>"]
    takeaway_text = str(takeaway or "").strip()
    if takeaway_text:
        parts.extend(["", _escape(takeaway_text)])
    parts.extend(["", _format_pre(fields)])
    if footer:
        parts.extend(["", f"<i>{_escape(footer)}</i>"])
    return "\n".join(parts)


def _side(side: str | None) -> str:
    return str(side or "").strip().upper()


def build_layer1(args: argparse.Namespace) -> str:
    return _render_message(
        "🌍",
        f"L1 Global Context — {args.date}",
        f"{args.regime} posture. Stay selective and trade the tape, not the hope.",
        [
            ("Regime", args.regime),
            ("Posture", args.posture),
            ("Sectors", args.sectors),
            ("Key risk", _compact(args.key_risk)),
        ],
        footer="Scarlett trader · L1",
    )


def build_layer2(args: argparse.Namespace) -> str:
    return _render_message(
        "🧭",
        f"L2 Screening — {args.date}",
        f"Shortlist is ready. Focus first on {args.top_pick} unless the tape invalidates it.",
        [
            ("Shortlist", args.shortlist),
            ("Top pick", args.top_pick),
            ("Reason", args.top_reason),
            ("Watch", _compact(args.watch)),
        ],
        footer="Scarlett trader · L2",
    )


def build_layer3(args: argparse.Namespace) -> str:
    return _render_message(
        "🚨",
        f"L3 Signal — {args.ticker}",
        args.note,
        [
            ("Time", args.timestamp),
            ("Signal", args.signal),
            ("Action", args.action),
            ("Ticker", args.ticker),
        ],
        footer="Scarlett trader · L3",
    )


def build_layer4(args: argparse.Namespace) -> str:
    urgency = "Immediate action. Watch entry quality first." if args.urgent else "Trade plan finalized. Wait for confirmation at the trigger."
    return _render_message(
        "🎯",
        f"L4 Trade Plan — {args.ticker} · {args.date}",
        f"{args.thesis} {urgency}",
        [
            ("Entry", f"{_format_idr(args.entry_low)}–{_format_idr(args.entry_high)}"),
            ("SL", f"{_format_idr(args.stop)} ({_format_percent(args.stop_pct)})"),
            ("T1", f"{_format_idr(args.target1)} ({_format_percent(args.target1_pct)})"),
            ("Size", f"{_format_idr(args.size_amount)} ({_format_percent(args.size_pct)} cap)"),
            ("Risk", _format_percent(args.risk)),
            ("Trigger", args.trigger),
        ],
        footer="Scarlett trader · L4",
    )


def build_order_placing(args: argparse.Namespace) -> str:
    side = _side(args.side)
    emoji = "🟢" if side == "BUY" else "🔴"
    reason = args.reason or ("Entry conditions aligned" if side == "BUY" else "Exit trigger confirmed")
    return _render_message(
        emoji,
        f"Placing {side} — {args.ticker}",
        f"Pre-flight checks passed. Sending the {side.lower()} order now.",
        [
            ("Ticker", args.ticker),
            ("Shares", _format_shares(args.shares)),
            ("Price", _format_idr(args.price)),
            ("SL", _format_idr(args.stop) if args.stop else "—"),
            ("Risk", _format_percent(args.risk) if args.risk else "—"),
            ("Reason", reason),
        ],
        footer="Scarlett trader · execution",
    )


def build_order_confirmed(args: argparse.Namespace) -> str:
    side = _side(args.side)
    emoji = "✅" if side == "BUY" else "☑️"
    return _render_message(
        emoji,
        f"Order Placed — {side} {args.ticker}",
        "Broker accepted the order.",
        [
            ("Order ID", args.order_id),
            ("Ticker", args.ticker),
            ("Side", side),
            ("Shares", _format_shares(args.shares)),
            ("Price", _format_idr(args.price)),
        ],
        footer="Scarlett trader · execution",
    )


def build_order_failed(args: argparse.Namespace) -> str:
    side = _side(args.side) if args.side else "UNKNOWN"
    return _render_message(
        "❌",
        f"Order Failed — {args.ticker}",
        "Broker rejected the order or the request failed. Manual review needed.",
        [
            ("Ticker", args.ticker),
            ("Side", side),
            ("Error", args.error),
        ],
        footer="Scarlett trader · execution",
    )


def build_layer0(args: argparse.Namespace) -> str:
    dd = _number(args.dd)
    dd_flag = " ⚠️ DD>5%" if (dd is not None and dd >= 5) else ""
    return _render_message(
        "🏦",
        f"L0 Portfolio — {args.date}",
        f"Portfolio health check complete.{dd_flag} Action: {_compact(args.action)}.",
        [
            ("Equity",       _format_idr(args.equity)),
            ("MTD return",   _format_percent(args.mtd_return)),
            ("Drawdown",     _format_percent(args.dd)),
            ("Open risk",    _format_percent(args.open_risk)),
            ("Top exposure", _compact(args.top_exposure)),
            ("Action",       _compact(args.action)),
        ],
        footer="Scarlett trader · L0",
    )


def build_execution_summary(args: argparse.Namespace) -> str:
    return _render_message(
        "📦",
        f"Execution Summary — {args.timestamp}",
        "Session check complete.",
        [
            ("Exits", _compact(args.exits)),
            ("Entries", _compact(args.entries)),
            ("Holds", args.holds),
            ("Cash", _format_idr(args.cash)),
        ],
        footer="Scarlett trader · execution",
    )


def _telegram_config() -> tuple[str, str, str | None]:
    load_env()
    token = os.environ.get(BOT_TOKEN_ENV, "").strip()
    chat_id = os.environ.get(CHAT_ID_ENV, "").strip()
    thread_id = os.environ.get(THREAD_ID_ENV, "").strip() or None
    if not token:
        raise SystemExit(f"Missing required env var: {BOT_TOKEN_ENV}")
    if not chat_id:
        raise SystemExit(f"Missing required env var: {CHAT_ID_ENV}")
    return token, chat_id, thread_id


def send_message(text: str) -> dict:
    token, chat_id, thread_id = _telegram_config()
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": PARSE_MODE,
        "disable_web_page_preview": "true",
    }
    if thread_id:
        payload["message_thread_id"] = thread_id
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        timeout=API_TIMEOUT,
    )
    if not response.ok:
        raise requests.HTTPError(response.text, response=response)
    return response.json()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trader Telegram sender")
    parser.add_argument("--dry-run", action="store_true", help="Render message locally without sending")
    sub = parser.add_subparsers(dest="command", required=True)

    layer1 = sub.add_parser("layer1")
    layer1.add_argument("--date", required=True)
    layer1.add_argument("--regime", required=True)
    layer1.add_argument("--posture", required=True)
    layer1.add_argument("--sectors", required=True)
    layer1.add_argument("--key-risk", default="none")
    layer1.set_defaults(builder=build_layer1)

    layer2 = sub.add_parser("layer2")
    layer2.add_argument("--date", required=True)
    layer2.add_argument("--shortlist", required=True)
    layer2.add_argument("--top-pick", required=True)
    layer2.add_argument("--top-reason", required=True)
    layer2.add_argument("--watch", default="none")
    layer2.set_defaults(builder=build_layer2)

    layer3 = sub.add_parser("layer3")
    layer3.add_argument("--timestamp", required=True)
    layer3.add_argument("--ticker", required=True)
    layer3.add_argument("--signal", required=True)
    layer3.add_argument("--note", required=True)
    layer3.add_argument("--action", required=True)
    layer3.set_defaults(builder=build_layer3)

    layer4 = sub.add_parser("layer4")
    layer4.add_argument("--date", required=True)
    layer4.add_argument("--ticker", required=True)
    layer4.add_argument("--thesis", required=True)
    layer4.add_argument("--entry-low", required=True)
    layer4.add_argument("--entry-high", required=True)
    layer4.add_argument("--stop", required=True)
    layer4.add_argument("--stop-pct", required=True)
    layer4.add_argument("--target1", required=True)
    layer4.add_argument("--target1-pct", required=True)
    layer4.add_argument("--size-amount", required=True)
    layer4.add_argument("--size-pct", required=True)
    layer4.add_argument("--risk", required=True)
    layer4.add_argument("--trigger", required=True)
    layer4.add_argument("--urgent", action="store_true")
    layer4.set_defaults(builder=build_layer4)

    layer0 = sub.add_parser("layer0")
    layer0.add_argument("--date", required=True)
    layer0.add_argument("--equity", required=True)
    layer0.add_argument("--mtd-return", required=True)
    layer0.add_argument("--dd", required=True)
    layer0.add_argument("--open-risk", required=True)
    layer0.add_argument("--top-exposure", required=True)
    layer0.add_argument("--action", required=True)
    layer0.set_defaults(builder=build_layer0)

    placing = sub.add_parser("order-placing")
    placing.add_argument("--side", choices=["BUY", "SELL"], required=True)
    placing.add_argument("--ticker", required=True)
    placing.add_argument("--shares", required=True)
    placing.add_argument("--price", required=True)
    placing.add_argument("--stop")
    placing.add_argument("--risk")
    placing.add_argument("--reason")
    placing.set_defaults(builder=build_order_placing)

    confirmed = sub.add_parser("order-confirmed")
    confirmed.add_argument("--order-id", required=True)
    confirmed.add_argument("--side", choices=["BUY", "SELL"], required=True)
    confirmed.add_argument("--ticker", required=True)
    confirmed.add_argument("--shares", required=True)
    confirmed.add_argument("--price", required=True)
    confirmed.set_defaults(builder=build_order_confirmed)

    failed = sub.add_parser("order-failed")
    failed.add_argument("--ticker", required=True)
    failed.add_argument("--side", choices=["BUY", "SELL"])
    failed.add_argument("--error", required=True)
    failed.set_defaults(builder=build_order_failed)

    summary = sub.add_parser("execution-summary")
    summary.add_argument("--timestamp", required=True)
    summary.add_argument("--exits", default="none")
    summary.add_argument("--entries", default="none")
    summary.add_argument("--holds", required=True)
    summary.add_argument("--cash", required=True)
    summary.set_defaults(builder=build_execution_summary)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    text = args.builder(args)

    if args.dry_run:
        print(text)
        return 0

    result = send_message(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
