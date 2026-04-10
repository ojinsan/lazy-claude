#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import quote_plus

from browser_base import BrowserBase


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="General web browsing via Playwright Firefox")
    sub = p.add_subparsers(dest="cmd", required=True)

    open_p = sub.add_parser("open", help="Open a URL and extract content")
    open_p.add_argument("--url", required=True)
    open_p.add_argument("--extract", choices=["text", "links", "all"], default="text")
    open_p.add_argument("--screenshot", action="store_true")
    open_p.add_argument("--headed", action="store_true")

    search_p = sub.add_parser("search", help="Search using a browser-rendered engine")
    search_p.add_argument("--query", required=True)
    search_p.add_argument("--engine", choices=["google", "duckduckgo"], default="google")
    search_p.add_argument("--screenshot", action="store_true")
    search_p.add_argument("--headed", action="store_true")

    shot_p = sub.add_parser("screenshot", help="Take a screenshot of a URL")
    shot_p.add_argument("--url", required=True)
    shot_p.add_argument("--output")
    shot_p.add_argument("--headed", action="store_true")

    pdf_p = sub.add_parser("pdf", help="Save a URL as PDF")
    pdf_p.add_argument("--url", required=True)
    pdf_p.add_argument("--output", required=True)
    pdf_p.add_argument("--headed", action="store_true")

    return p


async def cmd_open(args: argparse.Namespace) -> dict:
    session = await BrowserBase.launch(headless=not args.headed, use_profile=False)
    try:
        await session.page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        await session.page.wait_for_timeout(1500)
        text = await BrowserBase.extract_text(session.page) if args.extract in {"text", "all"} else ""
        links = await BrowserBase.extract_links(session.page) if args.extract in {"links", "all"} else []
        shot = await BrowserBase.screenshot(session.page, name="web-open") if args.screenshot else None
        return {
            "ok": True,
            "cmd": "open",
            "url": session.page.url,
            "title": await session.page.title(),
            "text": text,
            "links": links,
            "screenshot": shot,
        }
    finally:
        await session.close()


async def cmd_search(args: argparse.Namespace) -> dict:
    session = await BrowserBase.launch(headless=not args.headed, use_profile=False)
    try:
        if args.engine == "google":
            url = f"https://www.google.com/search?q={quote_plus(args.query)}"
        else:
            url = f"https://duckduckgo.com/?q={quote_plus(args.query)}"
        await session.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await session.page.wait_for_timeout(2000)
        links = await BrowserBase.extract_links(session.page, max_links=20)
        shot = await BrowserBase.screenshot(session.page, name="web-search") if args.screenshot else None
        return {
            "ok": True,
            "cmd": "search",
            "engine": args.engine,
            "query": args.query,
            "url": session.page.url,
            "title": await session.page.title(),
            "links": links,
            "screenshot": shot,
        }
    finally:
        await session.close()


async def cmd_screenshot(args: argparse.Namespace) -> dict:
    session = await BrowserBase.launch(headless=not args.headed, use_profile=False)
    try:
        await session.page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        await session.page.wait_for_timeout(1500)
        path = await BrowserBase.screenshot(session.page, name=Path(args.output).stem if args.output else "web-shot")
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            Path(path).replace(out)
            path = str(out)
        return {"ok": True, "cmd": "screenshot", "url": session.page.url, "path": path}
    finally:
        await session.close()


async def cmd_pdf(args: argparse.Namespace) -> dict:
    session = await BrowserBase.launch(headless=not args.headed, use_profile=False)
    try:
        await session.page.goto(args.url, wait_until="networkidle", timeout=45000)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        await session.page.pdf(path=str(out), print_background=True)
        return {"ok": True, "cmd": "pdf", "url": session.page.url, "path": str(out)}
    finally:
        await session.close()


async def run(args: argparse.Namespace) -> dict:
    if args.cmd == "open":
        return await cmd_open(args)
    if args.cmd == "search":
        return await cmd_search(args)
    if args.cmd == "screenshot":
        return await cmd_screenshot(args)
    if args.cmd == "pdf":
        return await cmd_pdf(args)
    raise ValueError(f"Unknown command: {args.cmd}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = asyncio.run(run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
