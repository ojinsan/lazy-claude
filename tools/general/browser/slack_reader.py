#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import quote_plus

from browser_base import BrowserBase

BASE = "https://app.slack.com/client"


async def _session(headed: bool = False):
    return await BrowserBase.launch(headless=not headed, use_profile=True)


async def channels(headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(4000)
        items = await session.page.evaluate(
            """
            () => Array.from(document.querySelectorAll('a[href*="/client/"]')).map(a => ({text: (a.innerText || '').trim(), href: a.href})).filter(x => x.text)
            """
        )
        return {"ok": True, "cmd": "channels", "items": items[:100]}
    finally:
        await session.close()


async def read_channel(channel: str, limit: int, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(3000)
        await BrowserBase.scroll_and_load(session.page, scrolls=2)
        text = await BrowserBase.extract_text(session.page, max_chars=25000)
        return {"ok": True, "cmd": "read", "channel": channel, "text": text[: max(2000, limit * 800)]}
    finally:
        await session.close()


async def search(query: str, limit: int, headed: bool) -> dict:
    session = await _session(headed)
    try:
        url = BASE + f"/search/search-{quote_plus(query)}"
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(3500)
        text = await BrowserBase.extract_text(session.page, max_chars=20000)
        links = await BrowserBase.extract_links(session.page, max_links=limit)
        return {"ok": True, "cmd": "search", "query": query, "text": text, "links": links}
    finally:
        await session.close()


async def thread(url: str, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(3000)
        text = await BrowserBase.extract_text(session.page, max_chars=22000)
        return {"ok": True, "cmd": "thread", "url": session.page.url, "text": text}
    finally:
        await session.close()


async def dm(user: str, limit: int, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(3000)
        text = await BrowserBase.extract_text(session.page, max_chars=max(10000, limit * 900))
        return {"ok": True, "cmd": "dm", "user": user, "text": text}
    finally:
        await session.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Slack workspace reader (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("channels")
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("read")
    x.add_argument("--channel", required=True)
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("thread")
    x.add_argument("--url", required=True)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("dm")
    x.add_argument("--user", required=True)
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--headed", action="store_true")

    return p


async def run(args: argparse.Namespace) -> dict:
    if args.cmd == "channels":
        return await channels(args.headed)
    if args.cmd == "read":
        return await read_channel(args.channel, args.limit, args.headed)
    if args.cmd == "search":
        return await search(args.query, args.limit, args.headed)
    if args.cmd == "thread":
        return await thread(args.url, args.headed)
    return await dm(args.user, args.limit, args.headed)


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
