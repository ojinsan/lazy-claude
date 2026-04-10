#!/usr/bin/env node
const { firefox } = require('playwright');
const fs = require('fs');

function arg(name, fallback = '') {
  const idx = process.argv.indexOf(name);
  return idx >= 0 ? (process.argv[idx + 1] || fallback) : fallback;
}

(async() => {
  const sheetUrl = arg('--url');
  const tabName = arg('--tab-name', 'Car Comparison');
  const jsonFile = arg('--json-file');
  if (!sheetUrl || !jsonFile) {
    console.error('Usage: google-sheet-writer.js --url <sheet-url> --tab-name <name> --json-file <data.json>');
    process.exit(1);
  }
  const rows = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));
  const browser = await firefox.launch({ headless: false });
  const page = await browser.newPage();
  await page.goto(sheetUrl, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(10000);
  await page.keyboard.press('Escape').catch(()=>{});

  // Google Sheets bottom bar actual add-sheet button
  const addBtn = page.locator('#t-formula-bar + div, .docs-sheet-addsheetbutton, [aria-label="Tambahkan sheet"], [aria-label="Add sheet"]').first();
  await addBtn.click({ timeout: 10000 });
  await page.waitForTimeout(2000);

  // Find actual sheet tab buttons from bottom bar text.
  const tabs = page.locator('.docs-sheet-tab, [id^="sheet-button-"]');
  const tabCount = await tabs.count();
  const lastTab = tabs.nth(Math.max(0, tabCount - 1));
  await lastTab.dblclick({ timeout: 8000 });
  await page.waitForTimeout(1000);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A').catch(()=>{});
  await page.keyboard.type(tabName);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(2000);

  // Verify actual tab exists.
  const verify = page.locator(`.docs-sheet-tab:has-text("${tabName}"), [id^="sheet-button-"]:has-text("${tabName}")`).first();
  if (!(await verify.count())) {
    console.error(JSON.stringify({ ok: false, error: 'tab-not-found-after-rename', tabName }, null, 2));
    await browser.close();
    process.exit(2);
  }
  await verify.click({ timeout: 5000 }).catch(()=>{});
  await page.waitForTimeout(1000);

  const headers = Object.keys(rows[0] || {});
  const table = [headers].concat(rows.map(r => headers.map(h => String(r[h] ?? ''))));
  const tsv = table.map(r => r.join('\t')).join('\n');

  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+g' : 'Control+g').catch(()=>{});
  await page.waitForTimeout(500);
  await page.keyboard.type('A1');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(800);
  await page.keyboard.insertText(tsv);
  await page.waitForTimeout(3000);

  console.log(JSON.stringify({ ok: true, tabName, rows: rows.length, headers }, null, 2));
  await browser.close();
})();
