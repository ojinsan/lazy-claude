#!/usr/bin/env python3
"""
Deprecated compatibility wrapper for Threads search.

This script preserves the old entrypoint name (`threads_search.py`) but now
standardizes on the same Firefox persistent profile used by
`threads-scraper.js`.

Preferred tool:
    node threads-scraper.js --query "search term" --limit 10

Compatibility usage:
    python threads_search.py --query "search term" [--limit 10] [--headed]
    python threads_search.py --query "search term" [--limit 10] [--profile /custom/profile]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

WORKSPACE = Path("/home/lazywork/.openclaw/workspace")
DEFAULT_PROFILE = WORKSPACE / "scarlett" / "tools" / "general" / "playwright" / ".firefox-profile-threads"  # openclaw runtime path
LEGACY_PROFILE = Path.home() / ".config" / "playwright" / "firefox_profiles" / "cloned_profile"


async def search_threads(query: str, limit: int = 10, profile: str | None = None, headless: bool = True):
    """Search Threads and return JSON-compatible results."""
    results: list[dict] = []
    profile_path = Path(profile).expanduser() if profile else DEFAULT_PROFILE
    fallback_used = False

    if not profile_path.exists() and LEGACY_PROFILE.exists():
        profile_path = LEGACY_PROFILE
        fallback_used = True

    profile_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.firefox.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=headless,
            viewport={"width": 1440, "height": 900},
        )
        page = context.pages[0] if context.pages else await context.new_page()

        try:
            search_url = f"https://www.threads.net/search?q={query}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)

            post_links = await page.evaluate(
                """
                () => {
                  const links = [];
                  const nodes = Array.from(document.querySelectorAll('article, a[href*="/post/"], a[href*="/t/"]'));
                  for (const node of nodes) {
                    const linkEl = node.querySelector?.('a[href*="/post/"], a[href*="/t/"]') ||
                                   (node.tagName === 'A' ? node : null);
                    if (!linkEl) continue;
                    const href = linkEl.href;
                    if (href && (href.includes('/post/') || href.includes('/t/')) && !links.includes(href)) {
                      links.push(href);
                    }
                  }
                  return links;
                }
                """
            )

            for link in post_links[:limit]:
                try:
                    await page.goto(link, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000)

                    post = await page.evaluate(
                        """
                        () => {
                          const text = document.querySelector('article [data-pressable-module="PostBody"]')?.innerText ||
                                       document.querySelector('article [role="article"]')?.innerText ||
                                       document.querySelector('div[dir="auto"]')?.innerText ||
                                       document.querySelector('article')?.innerText || '';
                          const likes = document.querySelector('[data-pressable-module="like_fill"] span')?.innerText ||
                                        document.querySelector('[aria-label*="like"] span')?.innerText || '0';
                          const replies = document.querySelector('[data-pressable-module="reply_fill"] span')?.innerText ||
                                          document.querySelector('[aria-label*="reply"] span')?.innerText || '0';
                          return { text: text.slice(0, 3000), likes, replies };
                        }
                        """
                    )

                    results.append({
                        "url": page.url,
                        "text": post.get("text", ""),
                        "likes": post.get("likes", "0"),
                        "replies": post.get("replies", "0"),
                    })
                except Exception:
                    continue

            print(
                json.dumps(
                    {
                        "success": True,
                        "deprecated": True,
                        "preferred_tool": "threads-scraper.js",
                        "query": query,
                        "count": len(results),
                        "profile": str(profile_path),
                        "used_legacy_profile_fallback": fallback_used,
                        "results": results,
                    },
                    indent=2,
                )
            )
        except Exception as e:
            print(
                json.dumps(
                    {
                        "success": False,
                        "deprecated": True,
                        "preferred_tool": "threads-scraper.js",
                        "error": str(e),
                        "profile": str(profile_path),
                        "used_legacy_profile_fallback": fallback_used,
                    }
                )
            )
            sys.exit(1)
        finally:
            await context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Number of results")
    parser.add_argument("--profile", default=None, help="Optional Firefox profile path")
    parser.add_argument("--headed", action="store_true", help="Run Firefox with UI")

    args = parser.parse_args()

    asyncio.run(search_threads(args.query, args.limit, args.profile, not args.headed))
