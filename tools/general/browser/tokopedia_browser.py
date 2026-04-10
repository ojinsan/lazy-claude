#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import quote_plus

from browser_base import BrowserBase

BASE = "https://www.tokopedia.com"


async def _session(headed: bool = False):
    return await BrowserBase.launch(headless=not headed, use_profile=True)


async def search(query: str, sort: str, limit: int, headed: bool) -> dict:
    session = await _session(headed)
    try:
        url = f"{BASE}/search?st=product&q={quote_plus(query)}"
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        await BrowserBase.scroll_and_load(session.page, scrolls=2)
        links = await BrowserBase.extract_links(session.page, max_links=limit)
        return {"ok": True, "cmd": "search", "query": query, "sort": sort, "links": links}
    finally:
        await session.close()


async def product(url: str, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        text = await BrowserBase.extract_text(session.page, max_chars=15000)
        return {"ok": True, "cmd": "product", "url": session.page.url, "title": await session.page.title(), "text": text}
    finally:
        await session.close()


async def shop(url: str, limit: int, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        links = await BrowserBase.extract_links(session.page, max_links=limit)
        return {"ok": True, "cmd": "shop", "url": session.page.url, "links": links}
    finally:
        await session.close()


async def cart(headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(f"{BASE}/cart", wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        text = await BrowserBase.extract_text(session.page, max_chars=15000)
        return {"ok": True, "cmd": "cart", "text": text}
    finally:
        await session.close()


async def orders(status: str, headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(f"{BASE}/order-list", wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        text = await BrowserBase.extract_text(session.page, max_chars=15000)
        return {"ok": True, "cmd": "orders", "status": status, "text": text}
    finally:
        await session.close()


async def compare(urls: list[str], headed: bool) -> dict:
    items = []
    for url in urls:
        items.append(await product(url, headed))
    return {"ok": True, "cmd": "compare", "items": items}


async def wishlist(headed: bool) -> dict:
    session = await _session(headed)
    try:
        await session.page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        text = await BrowserBase.extract_text(session.page, max_chars=12000)
        return {"ok": True, "cmd": "wishlist", "text": text}
    finally:
        await session.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tokopedia browser (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--sort", default="relevance")
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("product")
    x.add_argument("--url", required=True)
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("shop")
    x.add_argument("--url", required=True)
    x.add_argument("--limit", type=int, default=20)
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("cart")
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("orders")
    x.add_argument("--status", default="all")
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("compare")
    x.add_argument("--urls", nargs='+', required=True)
    x.add_argument("--headed", action="store_true")
    x = sub.add_parser("wishlist")
    x.add_argument("--headed", action="store_true")
    return p


async def run(args: argparse.Namespace) -> dict:
    if args.cmd == "search":
        return await search(args.query, args.sort, args.limit, args.headed)
    if args.cmd == "product":
        return await product(args.url, args.headed)
    if args.cmd == "shop":
        return await shop(args.url, args.limit, args.headed)
    if args.cmd == "cart":
        return await cart(args.headed)
    if args.cmd == "orders":
        return await orders(args.status, args.headed)
    if args.cmd == "compare":
        return await compare(args.urls, args.headed)
    return await wishlist(args.headed)


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
