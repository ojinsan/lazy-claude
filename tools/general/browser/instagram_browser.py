#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import quote_plus

from browser_base import BrowserBase

BASE = "https://www.instagram.com"


async def _open_with_profile(path: str, headed: bool = False):
    session = await BrowserBase.launch(headless=not headed, use_profile=True)
    await session.page.goto(path, wait_until="domcontentloaded", timeout=45000)
    await session.page.wait_for_timeout(2500)
    return session


async def profile(username: str, headed: bool) -> dict:
    session = await _open_with_profile(f"{BASE}/{username}/", headed)
    try:
        text = await BrowserBase.extract_text(session.page, max_chars=12000)
        links = await BrowserBase.extract_links(session.page, max_links=40)
        return {"ok": True, "cmd": "profile", "username": username, "url": session.page.url, "title": await session.page.title(), "text": text, "links": links}
    finally:
        await session.close()


async def posts(username: str, limit: int, headed: bool) -> dict:
    session = await _open_with_profile(f"{BASE}/{username}/", headed)
    try:
        await BrowserBase.scroll_and_load(session.page, scrolls=2)
        items = await session.page.evaluate(
            """
            (limit) => Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'))
              .slice(0, limit)
              .map(a => ({href: a.href, text: (a.innerText || '').trim()}))
            """,
            limit,
        )
        return {"ok": True, "cmd": "posts", "username": username, "items": items}
    finally:
        await session.close()


async def post(url: str, screenshot: bool, headed: bool) -> dict:
    session = await _open_with_profile(url, headed)
    try:
        text = await BrowserBase.extract_text(session.page, max_chars=12000)
        shot = await BrowserBase.screenshot(session.page, name="instagram-post") if screenshot else None
        return {"ok": True, "cmd": "post", "url": session.page.url, "title": await session.page.title(), "text": text, "screenshot": shot}
    finally:
        await session.close()


async def stories(username: str, screenshot_all: bool, headed: bool) -> dict:
    session = await _open_with_profile(f"{BASE}/stories/{username}/", headed)
    try:
        shots = []
        if screenshot_all:
            shots.append(await BrowserBase.screenshot(session.page, name=f"stories-{username}"))
        ocr = await BrowserBase.ocr_screenshot(session.page, name=f"stories-ocr-{username}")
        text = await BrowserBase.extract_text(session.page, max_chars=8000)
        return {"ok": True, "cmd": "stories", "username": username, "url": session.page.url, "text": text, "screenshots": shots, "ocr": ocr}
    finally:
        await session.close()


async def search(query: str, headed: bool) -> dict:
    session = await _open_with_profile(f"{BASE}/explore/", headed)
    try:
        page = session.page
        selectors = [
            'input[placeholder*="Search"]',
            'input[aria-label*="Search"]',
            'input[name="queryBox"]',
        ]
        used = None
        for sel in selectors:
            try:
                await page.fill(sel, query)
                await page.press(sel, 'Enter')
                used = sel
                break
            except Exception:
                continue
        await page.wait_for_timeout(3500)
        text = await BrowserBase.extract_text(page, max_chars=12000)
        links = await BrowserBase.extract_links(page, max_links=50)
        return {
            "ok": True,
            "cmd": "search",
            "query": query,
            "url": page.url,
            "selector_used": used,
            "text": text,
            "links": links,
        }
    finally:
        await session.close()


async def feed(limit: int, screenshot: bool, headed: bool) -> dict:
    session = await _open_with_profile(BASE + "/", headed)
    try:
        await BrowserBase.scroll_and_load(session.page, scrolls=max(1, min(limit, 5)))
        text = await BrowserBase.extract_text(session.page, max_chars=15000)
        shot = await BrowserBase.screenshot(session.page, name="instagram-feed") if screenshot else None
        return {"ok": True, "cmd": "feed", "url": session.page.url, "text": text, "screenshot": shot}
    finally:
        await session.close()


async def reels(username: str, limit: int, headed: bool) -> dict:
    session = await _open_with_profile(f"{BASE}/{username}/reels/", headed)
    try:
        await BrowserBase.scroll_and_load(session.page, scrolls=2)
        items = await session.page.evaluate(
            """
            (limit) => Array.from(document.querySelectorAll('a[href*="/reel/"]')).slice(0, limit).map(a => ({href: a.href, text: (a.innerText || '').trim()}))
            """,
            limit,
        )
        return {"ok": True, "cmd": "reels", "username": username, "items": items}
    finally:
        await session.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Instagram browser (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("profile")
    x.add_argument("--username", required=True)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("posts")
    x.add_argument("--username", required=True)
    x.add_argument("--limit", type=int, default=12)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("post")
    x.add_argument("--url", required=True)
    x.add_argument("--screenshot", action="store_true")
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("stories")
    x.add_argument("--username", required=True)
    x.add_argument("--screenshot-all", action="store_true")
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("feed")
    x.add_argument("--limit", type=int, default=5)
    x.add_argument("--screenshot", action="store_true")
    x.add_argument("--headed", action="store_true")

    x = sub.add_parser("reels")
    x.add_argument("--username", required=True)
    x.add_argument("--limit", type=int, default=12)
    x.add_argument("--headed", action="store_true")

    return p


async def run(args: argparse.Namespace) -> dict:
    if args.cmd == "profile":
        return await profile(args.username, args.headed)
    if args.cmd == "posts":
        return await posts(args.username, args.limit, args.headed)
    if args.cmd == "post":
        return await post(args.url, args.screenshot, args.headed)
    if args.cmd == "stories":
        return await stories(args.username, args.screenshot_all, args.headed)
    if args.cmd == "search":
        return await search(args.query, args.headed)
    if args.cmd == "feed":
        return await feed(args.limit, args.screenshot, args.headed)
    return await reels(args.username, args.limit, args.headed)


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
