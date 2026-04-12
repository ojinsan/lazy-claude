#!/usr/bin/node
/**
 * Facebook scraper — marketplace and general search.
 *
 * Usage:
 *   node facebook-scraper.js --query "mazda 2" [--mode marketplace|search] [--location jakarta]
 *                             [--limit 20] [--output file.json] [--detail] [--headed]
 *
 * Modes:
 *   marketplace  Scrape Facebook Marketplace search results (default)
 *   search       Scrape Facebook general post search
 */

const { firefox } = require('playwright');
const fs = require('fs');

function parseArgs(argv) {
  const out = {
    query: '',
    mode: 'marketplace',
    location: 'jakarta',
    limit: 20,
    output: '',
    detail: false,
    headless: true,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--query')    out.query    = argv[++i] || '';
    else if (a === '--mode')     out.mode     = argv[++i] || 'marketplace';
    else if (a === '--location') out.location = argv[++i] || 'jakarta';
    else if (a === '--limit')    out.limit    = Number(argv[++i] || '20');
    else if (a === '--output')   out.output   = argv[++i] || '';
    else if (a === '--detail')   out.detail   = true;
    else if (a === '--headed')   out.headless = false;
  }
  return out;
}

// ---------------------------------------------------------------------------
// Marketplace
// ---------------------------------------------------------------------------

async function scrapeMarketplace(page, args) {
  const url = `https://www.facebook.com/marketplace/${args.location}/search?query=${encodeURIComponent(args.query)}`;
  console.error(`[marketplace] navigating to: ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  // Scroll to load more listings
  for (let i = 0; i < 5; i++) {
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
    await page.waitForTimeout(1500);
  }

  // Collect listing cards
  const cards = await page.evaluate(() => {
    const results = [];
    // Marketplace listing links
    const anchors = Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'));
    const seen = new Set();

    for (const a of anchors) {
      const href = a.href.split('?')[0]; // strip tracking params
      if (seen.has(href)) continue;
      seen.add(href);

      // Price — usually in a span with currency-like text
      const allText = a.innerText || '';
      const lines = allText.split('\n').map(s => s.trim()).filter(Boolean);

      // Heuristic: first line = price (contains Rp or digit), rest = title / location
      let price = '';
      let title = '';
      let location = '';

      for (const line of lines) {
        if (!price && /^(Rp|IDR|\$|€|£|\d)/.test(line)) {
          price = line;
        } else if (!title && line.length > 2) {
          title = line;
        } else if (!location && title && line.length > 2) {
          location = line;
        }
      }

      results.push({ url: href, price, title, location });
      if (results.length >= 60) break; // hard cap before detail fetch
    }
    return results;
  });

  console.error(`[marketplace] found ${cards.length} listing cards`);

  if (!args.detail) {
    return cards.slice(0, args.limit);
  }

  // Visit each listing for full details
  const results = [];
  const limit = Math.min(args.limit, cards.length);
  for (let i = 0; i < limit; i++) {
    const card = cards[i];
    console.error(`[marketplace] detail ${i + 1}/${limit}: ${card.url}`);
    try {
      await page.goto(card.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(3000);

      const detail = await page.evaluate(() => {
        // Title
        const titleEl = document.querySelector('h1, [data-testid="marketplace-pdp-title"], span[dir="auto"]');
        const title = titleEl?.innerText?.trim() || '';

        // Price
        const priceEls = Array.from(document.querySelectorAll('span, div')).filter(
          el => /^(Rp|IDR|\$)\s*[\d.,]+/.test(el.innerText?.trim() || '')
        );
        const price = priceEls[0]?.innerText?.trim() || '';

        // Description — look for the biggest text block
        const spans = Array.from(document.querySelectorAll('span[dir="auto"], div[dir="auto"]'));
        const desc = spans
          .map(el => el.innerText?.trim() || '')
          .filter(t => t.length > 50)
          .sort((a, b) => b.length - a.length)[0] || '';

        // Location
        const locEl = Array.from(document.querySelectorAll('span, div')).find(
          el => /\b(Jakarta|Bandung|Surabaya|Bali|Tangerang|Bekasi|Depok|Bogor|Semarang|Medan)\b/i.test(el.innerText || '')
        );
        const location = locEl?.innerText?.trim().slice(0, 80) || '';

        return { title, price, description: desc.slice(0, 1000), location };
      });

      results.push({
        url: card.url,
        title: detail.title || card.title,
        price: detail.price || card.price,
        location: detail.location || card.location,
        description: detail.description,
      });
    } catch (e) {
      console.error(`[marketplace] error on ${card.url}: ${e.message}`);
      results.push(card);
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// General search (posts)
// ---------------------------------------------------------------------------

async function scrapeSearch(page, args) {
  const url = `https://www.facebook.com/search/posts?q=${encodeURIComponent(args.query)}`;
  console.error(`[search] navigating to: ${url}`);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);

  // Scroll to load posts
  for (let i = 0; i < 5; i++) {
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
    await page.waitForTimeout(1500);
  }

  const posts = await page.evaluate((limit) => {
    const results = [];

    // Facebook renders feed items inside role="article" or feed-story divs
    const articles = Array.from(document.querySelectorAll('[role="article"]'));

    for (const article of articles) {
      if (results.length >= limit) break;

      // Post text — largest dir=auto block inside the article
      const textEls = Array.from(article.querySelectorAll('[dir="auto"]'));
      const text = textEls
        .map(el => el.innerText?.trim() || '')
        .filter(t => t.length > 20)
        .sort((a, b) => b.length - a.length)[0] || '';

      if (!text) continue;

      // Post link — look for timestamp-anchored links
      const linkEl = article.querySelector('a[href*="/posts/"], a[href*="/permalink/"], a[href*="?story_fbid="]');
      const postUrl = linkEl?.href || '';

      // Author name — usually the first strong/b or aria-label link
      const authorEl = article.querySelector('strong, b, a[role="link"][aria-label]');
      const author = authorEl?.innerText?.trim() || '';

      // Timestamp
      const tsEl = article.querySelector('abbr[data-utime], a[aria-label] abbr, time');
      const timestamp = tsEl?.getAttribute('data-utime')
        ? new Date(Number(tsEl.getAttribute('data-utime')) * 1000).toISOString()
        : (tsEl?.getAttribute('datetime') || tsEl?.innerText?.trim() || '');

      // Engagement counts
      const spans = Array.from(article.querySelectorAll('span'));
      const reactionEl = spans.find(s => /^\d[\d.,KMB]*\s*(likes?|reactions?)?$/i.test(s.innerText?.trim() || ''));
      const reactions = reactionEl?.innerText?.trim() || '';
      const commentEl = spans.find(s => /^\d[\d.,KMB]*\s*comments?$/i.test(s.innerText?.trim() || ''));
      const comments = commentEl?.innerText?.trim() || '';

      results.push({
        url: postUrl,
        author,
        timestamp,
        text: text.slice(0, 2000),
        reactions,
        comments,
      });
    }
    return results;
  }, args.limit);

  console.error(`[search] found ${posts.length} posts`);
  return posts;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);
  if (!args.query) {
    console.error('Usage: facebook-scraper.js --query "..." [--mode marketplace|search] [--location jakarta] [--limit 20] [--output file.json] [--detail] [--headed]');
    process.exit(1);
  }

  const PRIMARY_PROFILE  = '/home/lazywork/workspace/tools/general/playwright/.firefox-profile-facebook';
  const FALLBACK_PROFILE = '/home/lazywork/workspace/tools/general/playwright/.firefox-profile-facebook';
  const userDataDir = fs.existsSync(PRIMARY_PROFILE) ? PRIMARY_PROFILE : FALLBACK_PROFILE;

  // Ensure the profile dir exists
  if (!fs.existsSync(userDataDir)) {
    fs.mkdirSync(userDataDir, { recursive: true });
  }

  const browser = await firefox.launchPersistentContext(userDataDir, {
    headless: args.headless,
    viewport: { width: 1440, height: 900 },
  });

  const page = browser.pages()[0] || await browser.newPage();

  let results;
  try {
    if (args.mode === 'search') {
      results = await scrapeSearch(page, args);
    } else {
      results = await scrapeMarketplace(page, args);
    }
  } finally {
    await browser.close();
  }

  const payload = {
    query: args.query,
    mode: args.mode,
    ...(args.mode === 'marketplace' ? { location: args.location } : {}),
    fetchedAt: new Date().toISOString(),
    source: 'facebook',
    count: results.length,
    results,
  };

  if (args.output) {
    fs.writeFileSync(args.output, JSON.stringify(payload, null, 2));
    console.error(`[facebook-scraper] saved to ${args.output}`);
  }
  console.log(JSON.stringify(payload, null, 2));
}

main().catch(err => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
