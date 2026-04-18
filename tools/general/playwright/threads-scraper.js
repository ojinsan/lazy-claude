#!/usr/bin/node
const { firefox } = require('playwright');
const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const out = { query: '', username: '', limit: 10, output: '', headless: true, comments: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--query') out.query = argv[++i] || '';
    else if (a === '--username') out.username = (argv[++i] || '').replace(/^@/, '');
    else if (a === '--limit') out.limit = Number(argv[++i] || '10');
    else if (a === '--output') out.output = argv[++i] || '';
    else if (a === '--headed') out.headless = false;
    else if (a === '--comments') out.comments = true;
  }
  return out;
}

async function scrapePost(page) {
  await page.waitForTimeout(3000);

  const postUrl = page.url();

  const postData = await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll('span[dir="auto"]'));
    const spanTexts = spans.map(e => e.innerText?.trim() || '').filter(Boolean);
    const text = spanTexts
      .filter(t => t.length > 30 || t.includes('\n'))
      .find(t => !t.match(/^\d+(\.\d+)?[KMB]?\s*(views|likes|replies)/i)) || '';
    const viewsSpan = spans.find(e => /views/i.test(e.innerText));
    const views = viewsSpan ? viewsSpan.innerText.replace(/views/i, '').trim() : '0';
    const author = spanTexts.find((value, index) => {
      const next = spanTexts[index + 1] || '';
      return /^[^\s].{0,80}$/.test(value) && /^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(next);
    }) || '';

    return {
      text: text.slice(0, 3000),
      views,
      author,
    };
  });

  return {
    url: postUrl,
    ...postData,
  };
}

async function scrapeComments(page) {
  for (let i = 0; i < 4; i++) {
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
    await page.waitForTimeout(1200);
  }

  return await page.evaluate(() => {
    const spans = Array.from(document.querySelectorAll('span[dir="auto"]'))
      .map(el => (el.innerText || '').trim())
      .filter(Boolean);

    const isDate = text => /^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(text);
    const isHeaderAt = index => (
      index + 1 < spans.length &&
      isDate(spans[index + 1]) &&
      /^[^\s].{0,80}$/.test(spans[index])
    );
    const cleanPart = text => text
      .replace(/^·\s*/gm, '')
      .replace(/^Author\s*$/gim, '')
      .replace(/^Translate\s*$/gim, '')
      .replace(/^Some additional replies aren't available\. Learn more\s*$/gim, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
    const noisePatterns = [
      /^(like|reply|repost|share|follow|following|translate|see translation)$/i,
      /^\d+(\.\d+)?[KMB]?$/,
      /^\d+(\.\d+)?[KMB]?\s+(like|likes|reply|replies|repost|reposts|view|views)$/i,
      /^threads$/i,
      /^view all replies$/i,
      /^some additional replies aren't available\. learn more$/i,
    ];
    const isNoise = text => noisePatterns.some(re => re.test(text)) || /^https?:\/\//i.test(text);
    const uniq = values => [...new Set(values.filter(Boolean))];

    const blocks = [];
    for (let i = 0; i < spans.length - 1; i++) {
      if (!isHeaderAt(i)) continue;

      const author = spans[i];
      const date = spans[i + 1];
      let j = i + 2;
      let byAuthor = false;

      if (spans[j] === 'Author' || /^·?\s*Author$/i.test(spans[j])) {
        byAuthor = true;
        j += 1;
      }

      const parts = [];
      for (; j < spans.length; j++) {
        const text = spans[j];
        if (isHeaderAt(j)) break;
        if (!text || text === author || isDate(text) || isNoise(text)) continue;
        if (/^·?\s*Author$/i.test(text)) {
          byAuthor = true;
          continue;
        }
        if (parts.length && /^liked by /i.test(text)) break;
        const cleaned = cleanPart(text.replace(/\s+\n/g, '\n'));
        if (!cleaned || isNoise(cleaned)) continue;
        parts.push(cleaned);
        if (parts.length >= 8) break;
      }

      const text = uniq(parts).join('\n').trim();
      if (text.length >= 20 && text.length <= 2000) {
        blocks.push({
          author,
          date,
          byAuthor,
          text: text.slice(0, 1000),
        });
      }

      i = Math.max(i, j - 1);
    }

    const starter = blocks[0]?.author || '';
    const seen = new Set();
    return blocks
      .slice(1)
      .filter(item => {
        const key = `${item.author}|${item.text}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((item, index) => ({
        ...item,
        isThreadStarter: !!starter && item.author === starter,
        priority: item.byAuthor ? 0 : item.author === starter ? 1 : 2,
        order: index,
      }))
      .sort((a, b) => a.priority - b.priority || a.order - b.order)
      .slice(0, 30)
      .map(({ priority, order, ...item }) => item);
  });
}

async function getProfilePostLinks(page, username, limit) {
  const profileUrl = `https://www.threads.net/@${username}`;
  console.error(`[username] Navigating to profile: ${profileUrl}`);
  await page.goto(profileUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(4000);

  // Scroll to load more posts
  for (let i = 0; i < 3; i++) {
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
    await page.waitForTimeout(1500);
  }

  const links = await page.evaluate(() => {
    const seen = new Set();
    const out = [];
    document.querySelectorAll('a[href*="/post/"], a[href*="/t/"]').forEach(a => {
      const href = a.href;
      if (href && !seen.has(href)) { seen.add(href); out.push(href); }
    });
    return out;
  });

  console.error(`[username] Found ${links.length} post links on @${username}`);
  return links.slice(0, limit);
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.query && !args.username) {
    console.error('Usage: threads-scraper.js --query "..." [--limit 10] [--output file.json] [--headed] [--comments]');
    console.error('       threads-scraper.js --username handle [--limit 10] [--output file.json] [--headed]');
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

  let postLinks = [];
  let sourceLabel = '';

  if (args.username) {
    // Username mode: scrape profile page directly
    postLinks = await getProfilePostLinks(page, args.username, args.limit);
    sourceLabel = `@${args.username}`;
  } else {
    // Search mode (original behaviour)
    const searchUrl = `https://www.threads.net/search?q=${encodeURIComponent(args.query)}`;
    console.error(`Searching for: ${args.query}`);
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);

    postLinks = await page.evaluate(() => {
      const links = [];
      const articles = Array.from(document.querySelectorAll('article, a[href*="/post/"], a[href*="/t/"]'));
      for (const article of articles) {
        const linkEl = article.querySelector('a[href*="/post/"], a[href*="/t/"]') ||
                       (article.tagName === 'A' ? article : null);
        if (linkEl) {
          const href = linkEl.href;
          if (href && (href.includes('/post/') || href.includes('/t/')) && !links.includes(href))
            links.push(href);
        }
      }
      return links;
    });
    sourceLabel = args.query;
  }

  console.error(`Found ${postLinks.length} post links`);

  const results = [];
  const limit = Math.min(args.limit, postLinks.length);

  for (let i = 0; i < limit; i++) {
    const link = postLinks[i];
    console.error(`Scraping post ${i + 1}/${limit}: ${link}`);

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
    query: args.username ? `@${args.username}` : args.query,
    username: args.username || null,
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
