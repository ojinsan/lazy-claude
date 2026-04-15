#!/usr/bin/env node
/**
 * instagram-scraper.js
 *
 * Firefox-session-aware Instagram scraper for market research.
 * Requires a logged-in Firefox profile at .firefox-profile-instagram/
 *
 * Usage:
 *   node instagram-scraper.js profile --username <username>
 *   node instagram-scraper.js posts --username <username> [--limit 10]
 *   node instagram-scraper.js search --query <query>
 *
 * Status: placeholder — implement using the threads-scraper.js pattern.
 */

const { chromium, firefox } = require('playwright');
const path = require('path');

const PROFILE_DIR = path.join(__dirname, '.firefox-profile-instagram');

async function scrapeProfile(username) {
  const browser = await firefox.launchPersistentContext(PROFILE_DIR, {
    headless: true,
  });
  const page = await browser.newPage();
  await page.goto(`https://www.instagram.com/${username}/`, { waitUntil: 'networkidle' });
  const content = await page.content();
  await browser.close();
  return content;
}

const [,, command, ...args] = process.argv;

(async () => {
  if (command === 'profile') {
    const username = args[args.indexOf('--username') + 1];
    if (!username) { console.error('--username required'); process.exit(1); }
    const html = await scrapeProfile(username);
    console.log(html.substring(0, 2000));
  } else {
    console.error(`Unknown command: ${command}`);
    console.error('Usage: node instagram-scraper.js profile --username <username>');
    process.exit(1);
  }
})();
