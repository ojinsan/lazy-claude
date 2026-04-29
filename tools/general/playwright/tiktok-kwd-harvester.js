#!/usr/bin/node
/**
 * TikTok Keyword Harvester
 * T&S tool — expands a seed blocklist by discovering + verifying new risk keywords.
 *
 * Flow per keyword:
 *   1. Search TikTok (up to --verify N videos)
 *   2. If ≥1 dangerous video found → keyword is VERIFIED, add to blocklist
 *   3. Extract hashtags from dangerous video captions → candidate keywords
 *   4. Call TikTok suggestions API → more candidates
 *   5. Verify each candidate the same way (steps 1-2)
 *   6. Loop until no new verified keywords found (or --max-loops hit)
 *
 * Usage:
 *   node tiktok-kwd-harvester.js [--seeds CSV] [--output DIR] [--verify N]
 *                                 [--headed] [--max-loops N]
 *
 * Output:
 *   blocklist_TIMESTAMP.csv   — verified keywords safe to block
 *   rejected_TIMESTAMP.csv    — candidates that returned no dangerous content
 */

'use strict';

const { firefox }   = require('playwright');
const { spawnSync } = require('child_process');
const fs   = require('fs');
const path = require('path');

const PROFILE          = path.resolve(__dirname, '.firefox-profile-tiktok');
const CLAUDE_BIN       = '/home/lazywork/.local/bin/claude';
const CLAUDE_SETTINGS  = path.resolve(__dirname, '../../../.claude/settings.openclaude.json');

// ---------------------------------------------------------------------------
// Args
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = {
    seeds:     path.resolve(__dirname, '../tiktok_safety_keywords.csv'),
    output:    path.resolve(__dirname, '../tiktok_safety_output'),
    verify:    7,       // videos to check per keyword
    headed:    false,
    maxLoops:  5,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if      (a === '--seeds')      opts.seeds     = argv[++i];
    else if (a === '--output')     opts.output    = argv[++i];
    else if (a === '--verify')     opts.verify    = Number(argv[++i]);
    else if (a === '--headed')     opts.headed    = true;
    else if (a === '--max-loops')  opts.maxLoops  = Number(argv[++i]);
  }
  return opts;
}

// ---------------------------------------------------------------------------
// CSV
// ---------------------------------------------------------------------------

function readCsv(filePath) {
  const lines = fs.readFileSync(filePath, 'utf8').trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const cols = line.split(',');
    const row  = {};
    headers.forEach((h, i) => { row[h] = (cols[i] || '').trim(); });
    return row;
  });
}

function escapeCsv(v) {
  const s = String(v ?? '').replace(/"/g, '""');
  return (s.includes(',') || s.includes('"') || s.includes('\n')) ? `"${s}"` : s;
}

function csvWriter(filePath, fields) {
  const fd = fs.openSync(filePath, 'w');
  fs.writeSync(fd, fields.join(',') + '\n');
  return {
    write(values) {
      fs.writeSync(fd, fields.map(f => escapeCsv(values[f])).join(',') + '\n');
    },
    close() { fs.closeSync(fd); },
  };
}

// ---------------------------------------------------------------------------
// Danger classifier — Claude CLI proxy + regex fallback
// ---------------------------------------------------------------------------

const RISK_STEMS = [
  'mercon','petasan','ledak','bom','sulfur','belerang',
  'peledak','karbit','kuluwung','racik','adonan','busi',
  'spirtus','gulungan','kertas','bambu','kelengkeng','klengkeng',
  'booster','boster','ses','madas','blerang','sulpur',
  'diy mercon','cara buat','membuat mercon','bikin mercon',
];

// Fast regex pre-filter — obvious hits skip the API call
const PATTERNS = [
  /\bmercon\b/i, /\bpetasan\b/i, /\bkuluwung\b/i,
  /\bbom karbit\b/i, /\bkarbit\b/i,
  /\bledak\b/i, /\bmeledak\b/i, /\bpeledak\b/i,
  /\bbelerang\b/i, /\bblerang\b/i, /\bsulfur\b/i, /\bsulpur\b/i,
  /\bkalium nitrat\b/i, /\bkno3\b/i, /\bpotassium nitrate\b/i,
  /\bamonium nitrat\b/i, /\bnh4no3\b/i,
  /\barang aktif\b/i, /\bflash powder\b/i, /\bblack powder\b/i,
  /\bspirtus\b/i, /\bbusi\b/i,
  /\bsuper ses\b/i, /\bmadas sp\b/i,
  /\bbooster kelengkeng\b/i, /\bboster kelengkeng\b/i,
  /\bbooster klengkeng\b/i,  /\bboster klengkeng\b/i,
  /\bracikan\b/i, /\badonan\b/i,
  /\bcara buat\b/i, /\bcara membuat\b/i, /\btutorial buat\b/i,
  /\bbikin bom\b/i, /\bbuat bom\b/i,
  /\bexplosive\b/i, /\bfirecracker\b/i, /\bgunpowder\b/i,
  /\bpipe bomb\b/i, /\bimprovised explosive\b/i,
];

function regexMatch(text) {
  return PATTERNS.some(p => p.test(text));
}

/**
 * Classify a batch of video descriptions via Claude CLI proxy.
 * Returns 1-based indices of dangerous captions, or null on API failure.
 */
function classifyWithClaude(descriptions) {
  const numbered = descriptions
    .map((d, i) => `${i + 1}. ${d.replace(/\n/g, ' ').slice(0, 300)}`)
    .join('\n');

  const prompt =
    `You are a Trust & Safety classifier for TikTok content moderation (Indonesia).\n` +
    `Identify which captions describe tutorials, instructions, or demonstrations for making fireworks, firecrackers, or improvised explosives (mercon, petasan, bom, peledak, karbit, etc.).\n\n` +
    `Captions:\n${numbered}\n\n` +
    `Reply ONLY with a JSON array of the dangerous caption numbers (1-based index). Example: [1,3] or [] if none.`;

  const env = { ...process.env };
  delete env.CLAUDECODE;
  delete env.CLAUDE_CODE_ENTRYPOINT;
  delete env.CLAUDE_CODE_EXECPATH;

  const result = spawnSync(
    CLAUDE_BIN,
    ['--settings', CLAUDE_SETTINGS, '-p', prompt],
    { encoding: 'utf8', timeout: 60000, env },
  );

  if (result.status !== 0 || !result.stdout) {
    console.log(`  [WARN] Claude classify failed (exit ${result.status}) — regex fallback`);
    return null;
  }

  const m = result.stdout.match(/\[[\d,\s]*\]/);
  if (!m) {
    console.log(`  [WARN] Claude bad response — regex fallback`);
    return null;
  }
  return JSON.parse(m[0]);
}

function extractHashtags(text) {
  return (text.match(/#(\w+)/g) || []).map(t => t.slice(1).toLowerCase());
}

function isRiskCandidate(kw) {
  return RISK_STEMS.some(s => kw.includes(s));
}

// ---------------------------------------------------------------------------
// TikTok helpers
// ---------------------------------------------------------------------------

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function fetchSuggestions(page, keyword) {
  try {
    const url = `https://www.tiktok.com/api/search/general/preview/?keyword=${encodeURIComponent(keyword)}&from_page=search`;
    const raw = await page.evaluate(async (u) => {
      try {
        const r = await fetch(u, { credentials: 'include', headers: { Accept: 'application/json' } });
        return await r.text();
      } catch { return null; }
    }, url);
    if (!raw) return [];
    const data = JSON.parse(raw);
    return (data.sug_list || data.data || [])
      .map(i => (i.keyword || i.query || i.text || '').toLowerCase().trim())
      .filter(Boolean);
  } catch { return []; }
}

async function searchVideos(page, keyword, limit) {
  const url = `https://www.tiktok.com/search?lang=en&q=${encodeURIComponent(keyword)}`;
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  } catch { return []; }

  await sleep(3000);

  // Error page = rate limited
  const err = await page.evaluate(() => !!document.querySelector('[data-e2e="search-error-icon"]'));
  if (err) {
    console.log(`  [RATE-LIMIT] Waiting 30s...`);
    await sleep(30000);
    // retry once
    try { await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 }); }
    catch { return []; }
    await sleep(3000);
    const err2 = await page.evaluate(() => !!document.querySelector('[data-e2e="search-error-icon"]'));
    if (err2) return [];
  }

  try {
    await page.waitForSelector('[data-e2e="search-card-desc"]', { timeout: 10000 });
  } catch { return []; }

  // One scroll pass
  await page.evaluate(() => window.scrollBy(0, 1400));
  await sleep(1000);

  return await page.evaluate((lim) => {
    const descs = Array.from(document.querySelectorAll('[data-e2e="search-card-desc"]')).slice(0, lim);
    return descs.map(d => {
      let container = d.parentElement;
      for (let i = 0; i < 8; i++) {
        if (!container) break;
        if (container.querySelector('a[href*="/video/"]')) break;
        container = container.parentElement;
      }
      const linkEl = container ? container.querySelector('a[href*="/video/"]') : null;
      const url    = linkEl ? linkEl.href : '';
      const m      = url.match(/\/video\/(\d+)/);
      return {
        videoId:     m ? m[1] : '',
        url,
        description: d.innerText.trim(),
      };
    });
  }, limit);
}

// ---------------------------------------------------------------------------
// Core: verify a keyword
// Returns { verified: bool, dangerousCount: int, candidates: string[] }
// ---------------------------------------------------------------------------

async function verifyKeyword(page, keyword, limit) {
  const videos = await searchVideos(page, keyword, limit);
  const candidates = new Set();

  // --- classify with Claude (proxy), regex fallback ---
  const descriptions = videos.map(v => v.description || '');
  let dangerousIndices; // 1-based
  if (descriptions.every(d => !d)) {
    dangerousIndices = [];
  } else {
    const apiResult = classifyWithClaude(descriptions);
    if (apiResult !== null) {
      dangerousIndices = apiResult;
    } else {
      // regex fallback
      dangerousIndices = descriptions
        .map((d, i) => (regexMatch(d) ? i + 1 : null))
        .filter(Boolean);
    }
  }

  for (const idx of dangerousIndices) {
    const v = videos[idx - 1];
    if (!v) continue;
    for (const tag of extractHashtags(v.description || '')) {
      const kw = tag.replace(/_/g, ' ').trim();
      if (isRiskCandidate(kw)) candidates.add(kw);
    }
  }

  // Also pull suggestions (shares page session)
  const sugs = await fetchSuggestions(page, keyword);
  for (const s of sugs) {
    if (isRiskCandidate(s)) candidates.add(s);
  }

  return {
    verified:      dangerousIndices.length > 0,
    dangerousCount: dangerousIndices.length,
    videosChecked: videos.length,
    candidates:    [...candidates],
  };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);
  fs.mkdirSync(args.output,  { recursive: true });
  fs.mkdirSync(PROFILE,      { recursive: true });

  const ts           = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const blocklistPath  = path.join(args.output, `blocklist_${ts}.csv`);
  const rejectedPath   = path.join(args.output, `rejected_${ts}.csv`);

  const blocklistCsv = csvWriter(blocklistPath, ['keyword','category','dangerous_videos','verified_loop','source']);
  const rejectedCsv  = csvWriter(rejectedPath,  ['keyword','videos_checked','reason','loop']);

  const seedRows    = readCsv(args.seeds);
  const verified    = new Set();   // confirmed blocklist
  const rejected    = new Set();   // checked, no dangerous content
  const seen        = new Set();   // all ever queued

  // Seed queue
  let queue = seedRows.map(r => ({ keyword: r.keyword.toLowerCase(), category: r.category || 'seed', source: 'seed' }));
  queue.forEach(r => seen.add(r.keyword));

  const browser = await firefox.launchPersistentContext(PROFILE, {
    headless: !args.headed,
    viewport: { width: 1440, height: 900 },
    locale:   'id-ID',
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
  });
  const page = browser.pages()[0] || await browser.newPage();

  let loopNum = 0;

  try {
    while (queue.length && loopNum < args.maxLoops) {
      loopNum++;
      console.log(`\n${'='.repeat(60)}`);
      console.log(`LOOP ${loopNum} — ${queue.length} keywords to verify`);
      console.log('='.repeat(60));

      const nextQueue = [];

      for (const item of queue) {
        const kw = item.keyword;
        process.stdout.write(`\n  Checking: "${kw}" ... `);

        const result = await verifyKeyword(page, kw, args.verify);

        if (result.verified) {
          console.log(`VERIFIED (${result.dangerousCount}/${result.videosChecked} dangerous)`);
          verified.add(kw);
          blocklistCsv.write({
            keyword:          kw,
            category:         item.category,
            dangerous_videos: result.dangerousCount,
            verified_loop:    loopNum,
            source:           item.source,
          });

          // Queue candidates not yet seen
          for (const c of result.candidates) {
            if (!seen.has(c)) {
              seen.add(c);
              nextQueue.push({ keyword: c, category: item.category, source: `loop${loopNum}:${kw}` });
              console.log(`    [candidate] "${c}"`);
            }
          }
        } else {
          console.log(`rejected (${result.videosChecked} videos, 0 dangerous)`);
          rejected.add(kw);
          rejectedCsv.write({ keyword: kw, videos_checked: result.videosChecked, reason: 'no_dangerous_content', loop: loopNum });
        }

        await sleep(2500);
      }

      if (nextQueue.length === 0) {
        console.log(`\n[DONE] No new candidates. Stopping after loop ${loopNum}.`);
        break;
      }

      queue = nextQueue;
    }
  } finally {
    await browser.close();
    blocklistCsv.close();
    rejectedCsv.close();
  }

  // Summary
  console.log(`\n${'='.repeat(60)}`);
  console.log('SUMMARY');
  console.log('='.repeat(60));
  console.log(`Blocklist (${verified.size}):   ${blocklistPath}`);
  console.log(`Rejected  (${rejected.size}):   ${rejectedPath}`);
  console.log(`Loops run: ${loopNum}`);
  console.log(`\nVERIFIED BLOCKLIST:`);
  for (const kw of [...verified].sort()) console.log(`  ${kw}`);
}

main().catch(e => { console.error(e); process.exit(1); });
