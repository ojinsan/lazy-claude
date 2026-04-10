#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

WORKSPACE = Path("/home/lazywork/.openclaw/workspace")
_RUNTIME_ROOT = WORKSPACE / "scarlett"  # openclaw runtime dir (name is on-disk, not renamed)
RUNTIME = _RUNTIME_ROOT / "runtime"
SCREENSHOT_DIR = RUNTIME / "screenshots"
PROFILE_ROOT = _RUNTIME_ROOT / "tools" / "general" / "browser" / "profiles"
DEFAULT_PROFILE = PROFILE_ROOT / "default"
LEGACY_THREADS_PROFILE = _RUNTIME_ROOT / "tools" / "general" / "playwright" / ".firefox-profile-threads"
ENV_PATH = WORKSPACE / ".env.local"

for p in [SCREENSHOT_DIR, PROFILE_ROOT]:
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class BrowserSession:
    playwright: Any
    browser: Optional[Any]
    context: Any
    page: Any
    use_profile: bool

    async def close(self) -> None:
        try:
            await self.context.close()
        finally:
            if self.browser is not None:
                await self.browser.close()
            if self.playwright is not None:
                await self.playwright.stop()


class BrowserBase:
    @staticmethod
    def load_env() -> dict[str, str]:
        env: dict[str, str] = {}
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k] = v
                os.environ.setdefault(k, v)
        return env

    @staticmethod
    async def launch(
        *,
        headless: bool = True,
        use_profile: bool = False,
        profile_dir: Optional[str | Path] = None,
        viewport: tuple[int, int] = (1440, 1024),
    ) -> BrowserSession:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = None

        if use_profile:
            if profile_dir:
                target = Path(profile_dir)
            elif LEGACY_THREADS_PROFILE.exists():
                target = LEGACY_THREADS_PROFILE
            else:
                target = DEFAULT_PROFILE
            target.mkdir(parents=True, exist_ok=True)
            context = await playwright.firefox.launch_persistent_context(
                str(target),
                headless=headless,
                viewport={"width": viewport[0], "height": viewport[1]},
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await playwright.firefox.launch(headless=headless)
            context = await browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
            page = await context.new_page()

        return BrowserSession(playwright=playwright, browser=browser, context=context, page=page, use_profile=use_profile)

    @staticmethod
    async def screenshot(page, name: Optional[str] = None, full_page: bool = True) -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = name or f"shot-{stamp}"
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in safe)[:80]
        out = SCREENSHOT_DIR / f"{safe}-{stamp}.png"
        await page.screenshot(path=str(out), full_page=full_page)
        return str(out)

    @staticmethod
    async def ocr_screenshot(page, name: Optional[str] = None) -> dict[str, Any]:
        path = await BrowserBase.screenshot(page, name=name, full_page=True)
        return {
            "ok": True,
            "image": path,
            "ocr_status": "pending_external_vision",
            "hint": "Pass this image path to an image/vision model for OCR.",
        }

    @staticmethod
    async def extract_text(page, max_chars: int = 20000) -> str:
        text = await page.evaluate(
            r"""
            () => {
              const blacklist = new Set(['SCRIPT','STYLE','NOSCRIPT']);
              const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
              const out = [];
              while (walker.nextNode()) {
                const node = walker.currentNode;
                const parent = node.parentElement;
                if (!parent || blacklist.has(parent.tagName)) continue;
                const t = (node.textContent || '').replace(/\s+/g, ' ').trim();
                if (t) out.push(t);
              }
              return out.join('\n');
            }
            """
        )
        return text[:max_chars]

    @staticmethod
    async def extract_links(page, max_links: int = 200) -> list[dict[str, str]]:
        links = await page.evaluate(
            r"""
            () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
              text: (a.innerText || a.textContent || '').replace(/\s+/g, ' ').trim(),
              href: a.href || ''
            }))
            """
        )
        cleaned = []
        seen = set()
        for item in links:
            href = (item.get("href") or "").strip()
            key = (href, (item.get("text") or "").strip())
            if not href or key in seen:
                continue
            seen.add(key)
            cleaned.append({"text": (item.get("text") or "").strip(), "href": href})
            if len(cleaned) >= max_links:
                break
        return cleaned

    @staticmethod
    async def scroll_and_load(page, scrolls: int = 3, delay_ms: int = 1500) -> None:
        for _ in range(scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(delay_ms)

    @staticmethod
    async def wait_for(page, selector: str, timeout: int = 10000) -> bool:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    async def safe_click(page, selector: str, timeout: int = 5000) -> bool:
        try:
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)
            return True
        except Exception:
            return False

    @staticmethod
    async def save_cookies(context, path: str | Path) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        state = await context.storage_state()
        target.write_text(json.dumps(state, indent=2))
        return str(target)

    @staticmethod
    async def load_cookies(context, path: str | Path) -> bool:
        target = Path(path)
        if not target.exists():
            return False
        state = json.loads(target.read_text())
        cookies = state.get("cookies", [])
        if cookies:
            await context.add_cookies(cookies)
        return True


def _main() -> None:
    print(json.dumps({
        "ok": True,
        "module": "browser_base",
        "default_profile": str(DEFAULT_PROFILE),
        "legacy_threads_profile": str(LEGACY_THREADS_PROFILE),
        "legacy_threads_exists": LEGACY_THREADS_PROFILE.exists(),
        "screenshot_dir": str(SCREENSHOT_DIR),
    }, indent=2))


if __name__ == "__main__":
    _main()
