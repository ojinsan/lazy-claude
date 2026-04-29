#!/usr/bin/env python3
"""
TikTok Safety Keyword Explorer
Trust & Safety research tool — identifies explosive/fireworks-making content,
extracts new risk keywords for follow-up loops.

Usage:
    python tiktok_safety_scraper.py [--keywords CSV] [--output DIR] [--limit N]
                                    [--headed] [--loop] [--max-loops N]
"""

import argparse
import asyncio
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PwTimeout

# ---------------------------------------------------------------------------
# Dangerous-content classifiers (Indonesian + English)
# ---------------------------------------------------------------------------

# Terms strongly indicating explosive/pyrotechnic construction instructions
EXPLOSIVE_TERMS = [
    # Fireworks / firecrackers
    r'\bmercon\b', r'\bpetasan\b', r'\bkuluwung\b',
    r'\bbom karbit\b', r'\bkarbit\b',
    # Explosive action verbs
    r'\bledak\b', r'\bmeledak\b', r'\bmeledakkan\b', r'\bpeledak\b',
    # Chemical precursors used in IED/fireworks
    r'\bbelerang\b', r'\bblerang\b', r'\bsulfur\b', r'\bsulpur\b',
    r'\bkalium nitrat\b', r'\bkno3\b', r'\bpotassium nitrate\b',
    r'\bamonium nitrat\b', r'\bnh4no3\b',
    r'\barang aktif\b', r'\bcharcoal powder\b',
    r'\bflash powder\b', r'\bblack powder\b',
    r'\bspirtus\b',   # denatured alcohol used as fuel
    r'\bbusi\b',       # spark plug — used as igniter
    # Brands/slang for compounds
    r'\bsuper ses\b', r'\bses\b', r'\bmadas sp\b', r'\bbooster kelengkeng\b',
    r'\bboster kelengkeng\b', r'\bbooster klengkeng\b', r'\bboster klengkeng\b',
    # Action phrases
    r'\bracikan\b', r'\badonan\b', r'\bformula\b',
    r'\bcara buat\b', r'\bcara membuat\b', r'\btutorial buat\b',
    r'\bbikin bom\b', r'\bbuat bom\b',
    # English
    r'\bexplosive\b', r'\bfirecracker\b', r'\bgunpowder\b',
    r'\bpipe bomb\b', r'\bimprovised explosive\b', r'\bied\b',
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in EXPLOSIVE_TERMS]

HASHTAG_RE = re.compile(r'#(\w+)', re.UNICODE)
MENTION_RE = re.compile(r'@(\w+)', re.UNICODE)

# ---------------------------------------------------------------------------

def classify(text: str) -> tuple[bool, list[str]]:
    """Return (is_dangerous, matched_terms)."""
    matched = []
    for pat in COMPILED:
        m = pat.search(text)
        if m:
            matched.append(m.group(0).lower())
    return bool(matched), list(set(matched))


def extract_hashtags(text: str) -> list[str]:
    return [t.lower() for t in HASHTAG_RE.findall(text)]


def extract_new_keywords(text: str, existing: set[str]) -> list[str]:
    """Pull hashtags + compound noun phrases that may be new risk keywords."""
    tags = extract_hashtags(text)
    # Filter: keep only tags that contain known risk stems
    risk_stems = [
        'mercon', 'petasan', 'ledak', 'bom', 'sulfur', 'belerang',
        'peledak', 'karbit', 'kuluwung', 'racik', 'adonan', 'busi',
        'spirtus', 'gulungan', 'kertas', 'bambu', 'kelengkeng', 'klengkeng',
        'booster', 'boster', 'ses', 'madas', 'blerang', 'sulpur',
        'diy', 'tutorial', 'cara', 'membuat', 'buat',
    ]
    new = []
    for tag in tags:
        if any(stem in tag for stem in risk_stems):
            candidate = tag.replace('_', ' ').strip()
            if candidate and candidate not in existing:
                new.append(candidate)
    return new


# ---------------------------------------------------------------------------
# TikTok scraper
# ---------------------------------------------------------------------------

async def search_tiktok(page, keyword: str, limit: int = 20) -> list[dict]:
    """Search TikTok and return list of video metadata dicts."""
    url = f"https://www.tiktok.com/search?q={keyword}"
    results = []

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        # Wait for video cards to appear
        await page.wait_for_selector('[data-e2e="search_video-item"]', timeout=15_000)
    except PwTimeout:
        # Fallback: try older selector
        try:
            await page.wait_for_selector('div[class*="DivItemContainerForSearch"]', timeout=10_000)
        except PwTimeout:
            print(f"  [WARN] No results loaded for: {keyword}", flush=True)
            return results

    # Scroll to load more
    for _ in range(max(1, limit // 8)):
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.2)

    # Extract video cards
    cards = await page.query_selector_all('[data-e2e="search_video-item"]')
    if not cards:
        cards = await page.query_selector_all('div[class*="DivItemContainerForSearch"]')

    for card in cards[:limit]:
        item = {}
        try:
            # Video URL / ID
            link_el = await card.query_selector('a[href*="/video/"]')
            if link_el:
                item['url'] = await link_el.get_attribute('href') or ''
                m = re.search(r'/video/(\d+)', item['url'])
                item['video_id'] = m.group(1) if m else ''
            else:
                item['url'] = ''
                item['video_id'] = ''

            # Description / title
            desc_el = await card.query_selector('[data-e2e="search-card-desc"]')
            if not desc_el:
                desc_el = await card.query_selector('span[class*="SpanText"]')
            item['description'] = (await desc_el.inner_text()).strip() if desc_el else ''

            # Author
            author_el = await card.query_selector('[data-e2e="search-card-user-unique-id"]')
            if not author_el:
                author_el = await card.query_selector('span[class*="SpanUniqueId"]')
            item['author'] = (await author_el.inner_text()).strip() if author_el else ''

            # Stats (views)
            stats_el = await card.query_selector('[data-e2e="video-views"]')
            item['views'] = (await stats_el.inner_text()).strip() if stats_el else ''

        except Exception as e:
            item.setdefault('url', '')
            item.setdefault('video_id', '')
            item.setdefault('description', '')
            item.setdefault('author', '')
            item.setdefault('views', '')

        if item.get('url') or item.get('description'):
            results.append(item)

    return results


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def run(args):
    keywords_path = Path(args.keywords)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    findings_path = output_dir / f"findings_{ts}.csv"
    new_kw_path   = output_dir / f"new_keywords_{ts}.csv"

    # Load initial keywords
    def load_keywords(path: Path) -> list[dict]:
        with open(path, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    keyword_rows = load_keywords(keywords_path)
    all_known_keywords: set[str] = {r['keyword'].lower() for r in keyword_rows}

    # Findings writer
    findings_file = open(findings_path, 'w', newline='', encoding='utf-8')
    findings_writer = csv.DictWriter(findings_file, fieldnames=[
        'loop', 'search_keyword', 'keyword_category', 'video_id', 'url',
        'author', 'views', 'description', 'is_dangerous', 'matched_terms',
        'hashtags', 'scraped_at',
    ])
    findings_writer.writeheader()

    # New keywords writer
    nkw_file = open(new_kw_path, 'w', newline='', encoding='utf-8')
    nkw_writer = csv.DictWriter(nkw_file, fieldnames=[
        'keyword', 'category', 'priority', 'source_video', 'found_in_loop',
    ])
    nkw_writer.writeheader()

    discovered_this_session: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=not args.headed)
        ctx = await browser.new_context(
            locale='id-ID',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) '
                'Gecko/20100101 Firefox/124.0'
            ),
        )
        page = await ctx.new_page()

        loop_num = 0
        queue = list(keyword_rows)

        while queue:
            loop_num += 1
            if args.max_loops and loop_num > args.max_loops:
                print(f"\n[STOP] Reached max loops ({args.max_loops})", flush=True)
                break

            print(f"\n{'='*60}", flush=True)
            print(f"LOOP {loop_num} — {len(queue)} keywords to process", flush=True)
            print('='*60, flush=True)

            next_loop_new: list[dict] = []

            for row in queue:
                kw       = row['keyword']
                category = row.get('category', 'unknown')
                priority = row.get('priority', 'medium')

                print(f"\n[{loop_num}] Searching: {kw!r}  ({category} / {priority})", flush=True)

                try:
                    videos = await search_tiktok(page, kw, limit=args.limit)
                except Exception as e:
                    print(f"  [ERROR] {e}", flush=True)
                    videos = []

                print(f"  Found {len(videos)} videos", flush=True)

                for v in videos:
                    text = v.get('description', '')
                    is_dangerous, matched = classify(text)
                    tags = extract_hashtags(text)
                    new_kws = extract_new_keywords(text, all_known_keywords)

                    if is_dangerous:
                        print(f"  [!] DANGEROUS — {v.get('video_id','')} | {v.get('author','')} | matched: {matched}", flush=True)

                    findings_writer.writerow({
                        'loop':             loop_num,
                        'search_keyword':   kw,
                        'keyword_category': category,
                        'video_id':         v.get('video_id', ''),
                        'url':              v.get('url', ''),
                        'author':           v.get('author', ''),
                        'views':            v.get('views', ''),
                        'description':      text,
                        'is_dangerous':     is_dangerous,
                        'matched_terms':    '|'.join(matched),
                        'hashtags':         '|'.join(tags),
                        'scraped_at':       datetime.now().isoformat(),
                    })
                    findings_file.flush()

                    for nk in new_kws:
                        if nk not in all_known_keywords:
                            all_known_keywords.add(nk)
                            entry = {
                                'keyword':       nk,
                                'category':      category,
                                'priority':      'high',
                                'source_video':  v.get('url', ''),
                                'found_in_loop': loop_num,
                            }
                            nkw_writer.writerow(entry)
                            nkw_file.flush()
                            next_loop_new.append({'keyword': nk, 'category': category, 'priority': 'high'})
                            discovered_this_session.append(entry)
                            print(f"    [+] New keyword discovered: {nk!r}", flush=True)

                # Polite delay between searches
                await asyncio.sleep(2.5)

            if not args.loop:
                break

            if next_loop_new:
                print(f"\n[LOOP {loop_num}] {len(next_loop_new)} new keywords queued for next loop", flush=True)
                queue = next_loop_new
            else:
                print(f"\n[DONE] No new keywords found. Stopping after loop {loop_num}.", flush=True)
                break

        await browser.close()

    findings_file.close()
    nkw_file.close()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}", flush=True)
    print("SUMMARY", flush=True)
    print('='*60, flush=True)
    print(f"Findings CSV:     {findings_path}", flush=True)
    print(f"New keywords CSV: {new_kw_path}", flush=True)
    print(f"Total loops run:  {loop_num}", flush=True)
    print(f"New keywords found: {len(discovered_this_session)}", flush=True)

    if discovered_this_session:
        print("\nNew keywords discovered this session:", flush=True)
        for e in discovered_this_session:
            print(f"  [{e['priority']}] {e['keyword']}  (loop {e['found_in_loop']})", flush=True)


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='TikTok T&S safety keyword explorer')
    parser.add_argument('--keywords', default='tools/general/tiktok_safety_keywords.csv',
                        help='Input keywords CSV (keyword,category,priority)')
    parser.add_argument('--output',   default='tools/general/tiktok_safety_output',
                        help='Output directory for findings + new keywords')
    parser.add_argument('--limit',    type=int, default=20,
                        help='Max videos per keyword (default 20)')
    parser.add_argument('--headed',   action='store_true',
                        help='Show browser window (useful for debugging / CAPTCHA)')
    parser.add_argument('--loop',     action='store_true',
                        help='Re-run with newly discovered keywords until no new ones found')
    parser.add_argument('--max-loops', type=int, default=0,
                        help='Cap number of loops (0 = unlimited, only applies with --loop)')
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == '__main__':
    main()
