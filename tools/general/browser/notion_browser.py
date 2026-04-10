#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from urllib.parse import quote_plus

from browser_base import BrowserBase


async def _session(headed: bool = False, use_profile: bool = False):
    return await BrowserBase.launch(headless=not headed, use_profile=use_profile)


async def open_page(url: str, extract: str, screenshot: bool, headed: bool, use_profile: bool) -> dict:
    session = await _session(headed, use_profile)
    try:
        page = session.page
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2500)
        text = await BrowserBase.extract_text(page, max_chars=20000) if extract in {"text", "all"} else ""
        links = await BrowserBase.extract_links(page, max_links=100) if extract in {"links", "all"} else []
        shot = await BrowserBase.screenshot(page, name="notion-page") if screenshot else None
        return {"ok": True, "cmd": "open", "url": page.url, "title": await page.title(), "text": text, "links": links, "screenshot": shot}
    finally:
        await session.close()


async def search_in_page(url: str, query: str, headed: bool, use_profile: bool) -> dict:
    result = await open_page(url, "text", False, headed, use_profile)
    text = result.get("text", "")
    lines = [line.strip() for line in text.splitlines() if query.lower() in line.lower()]
    return {"ok": True, "cmd": "search", "url": url, "query": query, "matches": lines[:50], "count": len(lines)}


async def append_text(url: str, text: str, headed: bool, use_profile: bool) -> dict:
    session = await _session(headed, use_profile)
    try:
        page = session.page
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)

        page_text = await BrowserBase.extract_text(page, max_chars=6000)
        if "Sign up or login to edit" in page_text or "log in to edit" in page_text.lower():
            return {
                "ok": False,
                "cmd": "append",
                "url": page.url,
                "reason": "login_required_for_edit",
                "message": "This shared Notion page is readable publicly, but editing requires a Notion account login in the browser profile.",
            }

        selectors = [
            'div.notion-selectable.notion-text-block:last-of-type',
            'div.notion-page-content div.notion-selectable.notion-text-block:last-of-type',
            '[contenteditable="true"]',
            'div[role="textbox"]',
            'textarea',
        ]
        used = None
        for sel in selectors:
            try:
                await page.click(sel)
                await page.wait_for_timeout(300)
                await page.keyboard.press('End')
                await page.keyboard.press('Enter')
                await page.keyboard.type(text)
                used = sel
                break
            except Exception:
                continue

        await page.wait_for_timeout(1000)
        after_text = await BrowserBase.extract_text(page, max_chars=8000)
        success = used is not None and text.strip() in after_text
        return {
            "ok": success,
            "cmd": "append",
            "url": page.url,
            "selector_used": used,
            "appended_text": text,
            "reason": None if success else "append_not_confirmed",
        }
    finally:
        await session.close()


async def screenshot_page(url: str, headed: bool, use_profile: bool) -> dict:
    session = await _session(headed, use_profile)
    try:
        await session.page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await session.page.wait_for_timeout(2500)
        shot = await BrowserBase.screenshot(session.page, name="notion-page")
        ocr = await BrowserBase.ocr_screenshot(session.page, name="notion-ocr")
        return {"ok": True, "cmd": "screenshot", "url": session.page.url, "screenshot": shot, "ocr": ocr}
    finally:
        await session.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Notion browser tool for public/shared pages")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("open")
    x.add_argument("--url", required=True)
    x.add_argument("--extract", choices=["text", "links", "all"], default="text")
    x.add_argument("--screenshot", action="store_true")
    x.add_argument("--headed", action="store_true")
    x.add_argument("--use-profile", action="store_true")

    x = sub.add_parser("search")
    x.add_argument("--url", required=True)
    x.add_argument("--query", required=True)
    x.add_argument("--headed", action="store_true")
    x.add_argument("--use-profile", action="store_true")

    x = sub.add_parser("append")
    x.add_argument("--url", required=True)
    x.add_argument("--text", required=True)
    x.add_argument("--headed", action="store_true")
    x.add_argument("--use-profile", action="store_true")

    x = sub.add_parser("screenshot")
    x.add_argument("--url", required=True)
    x.add_argument("--headed", action="store_true")
    x.add_argument("--use-profile", action="store_true")

    return p


async def run(args: argparse.Namespace) -> dict:
    if args.cmd == "open":
        return await open_page(args.url, args.extract, args.screenshot, args.headed, args.use_profile)
    if args.cmd == "search":
        return await search_in_page(args.url, args.query, args.headed, args.use_profile)
    if args.cmd == "append":
        return await append_text(args.url, args.text, args.headed, args.use_profile)
    return await screenshot_page(args.url, args.headed, args.use_profile)


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(asyncio.run(run(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
