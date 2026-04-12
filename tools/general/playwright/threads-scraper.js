#!/usr/bin/node
const { firefox } = require('playwright');
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const out = { query: '', limit: 10, output: '', headless: true, comments: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--query') out.query = argv[++i] || '';
    else if (a === '--limit') out.limit = Number(argv[++i] || '10');
    else if (a === '--output') out.output = argv[++i] || '';
    else if (a === '--headed') out.headless = false;
    else if (a === '--comments') out.comments = true;
  }
  return out;
}

async function scrapePost(page) {
  // Wait for the post to load
  await page.waitForTimeout(3000);

  // Get post URL
  const postUrl = page.url();

  // Scrape post text and engagement
  const postData = await page.evaluate(() => {
    // Threads renders post text in span[dir="auto"]
    // Pattern: views → username → post text → replies...
    // Pick the first span with substantial content (>30 chars or multiline)
    const spans = Array.from(document.querySelectorAll('span[dir="auto"]'));
    const text = spans
      .map(e => e.innerText?.trim() || '')
      .filter(t => t.length > 30 || t.includes('\n'))
      .find(t => !t.match(/^\d+(\.\d+)?[KMB]?\s*(views|likes|replies)/i)) || '';

    // Engagement: look for view/like/reply counts near spans containing those words
    const viewsSpan = spans.find(e => /views/i.test(e.innerText));
    const views = viewsSpan ? viewsSpan.innerText.replace(/views/i, '').trim() : '0';

    return {
      text: text.slice(0, 3000),
      views,
    };
  });

  return {
    url: postUrl,
    ...postData,
  };
}

async function scrapeComments(page) {
  // Try to scroll and load comments
  const comments = [];

  // Scroll down to load more comments
  for (let i = 0; i < 5; i++) {
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
    await page.waitForTimeout(1500);
  }

  const commentsData = await page.evaluate(() => {
    const commentEls = document.querySelectorAll('article');
    const comments = [];

    // Skip the main post (first article), get the rest as comments
    for (let i = 1; i < commentEls.length; i++) {
      const el = commentEls[i];
      const text = el.querySelector('[data-pressable-module="PostBody"]')?.innerText ||
                   el.querySelector('div[dir="auto"]')?.innerText ||
                   el.querySelector('span')?.innerText || '';

      if (text.length > 20 && text.length < 2000) {
        const likes = el.querySelector('[data-pressable-module="like_fill"] span')?.innerText ||
                      el.querySelector('[aria-label*="like"] span')?.innerText || '0';

        comments.push({
          text: text.slice(0, 1000),
          likes,
        });
      }

      if (comments.length >= 30) break;
    }

    return comments;
  });

  return commentsData;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.query) {
    console.error('Usage: threads-scraper.js --query "..." [--limit 10] [--output file.json] [--headed] [--comments]');
    process.exit(1);
  }

  // Primary: logged-in Threads profile (do NOT wipe or recreate on each run)
  // Fallback: .pw-firefox-threads (Playwright-run copy)
  const PRIMARY_PROFILE = '/home/lazywork/workspace/tools/general/playwright/.firefox-profile-threads';
  const FALLBACK_PROFILE = '/home/lazywork/workspace/tools/general/playwright/.pw-firefox-threads';
  const userDataDir = require('fs').existsSync(PRIMARY_PROFILE) ? PRIMARY_PROFILE : FALLBACK_PROFILE;

  const browser = await firefox.launchPersistentContext(userDataDir, {
    headless: args.headless,
    viewport: { width: 1440, height: 900 },
  });

  const page = browser.pages()[0] || await browser.newPage();
  const searchUrl = `https://www.threads.net/search?q=${encodeURIComponent(args.query)}`;
  console.log(`Searching for: ${args.query}`);
  await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);

  // First, collect post links from search results
  const postLinks = await page.evaluate(() => {
    const links = [];
    const articles = Array.from(document.querySelectorAll('article, a[href*="/post/"], a[href*="/t/"]'));

    for (const article of articles) {
      // Try to find a link within the article
      const linkEl = article.querySelector('a[href*="/post/"], a[href*="/t/"]') ||
                     (article.tagName === 'A' ? article : null);

      if (linkEl) {
        const href = linkEl.href;
        if (href && (href.includes('/post/') || href.includes('/t/')) && !links.includes(href)) {
          links.push(href);
        }
      }
    }

    return links;
  });

  console.log(`Found ${postLinks.length} post links`);

  const results = [];
  const limit = Math.min(args.limit, postLinks.length);

  for (let i = 0; i < limit; i++) {
    const link = postLinks[i];
    console.log(`Scraping post ${i + 1}/${limit}: ${link}`);

    try {
      await page.goto(link, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(3000);

      const postData = await scrapePost(page);

      if (args.comments) {
        postData.comments = await scrapeComments(page);
      }

      results.push(postData);
    } catch (e) {
      console.error(`Error scraping post ${link}: ${e.message}`);
    }
  }

  const payload = {
    query: args.query,
    fetchedAt: new Date().toISOString(),
    source: 'threads',
    results,
    count: results.length,
  };

  if (args.output) {
    fs.writeFileSync(args.output, JSON.stringify(payload, null, 2));
  }
  console.log(JSON.stringify(payload, null, 2));
  await browser.close();
}

main().catch(err => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
