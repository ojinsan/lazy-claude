#!/usr/bin/env node
const { MemoryClient } = require('mem0ai');

const apiKey = process.env.MEM0_API_KEY;
if (!apiKey) {
  console.error('MEM0_API_KEY is required');
  process.exit(1);
}

const client = new MemoryClient({ apiKey });

async function run() {
  const cmd = process.argv[2];
  const userId = process.env.MEM0_USER_ID || 'mr_o';

  if (cmd === 'add') {
    const text = process.argv.slice(3).join(' ');
    if (!text) throw new Error('Usage: mem0_helper.js add <text>');
    await client.add([
      { role: 'user', content: text },
      { role: 'assistant', content: 'Saved as critical memory.' }
    ], { user_id: userId, version: 'v2' });
    console.log('OK:add');
    return;
  }

  if (cmd === 'search') {
    const query = process.argv.slice(3).join(' ');
    if (!query) throw new Error('Usage: mem0_helper.js search <query>');
    const res = await client.search(query, { user_id: userId, version: 'v2' });
    console.log(JSON.stringify(res.slice(0, 5), null, 2));
    return;
  }

  if (cmd === 'seed-critical') {
    const critical = [
      '4-group watchlist mandatory: local tracked, api backend watchlist, rag v3 search, stocklist market-attractive.',
      'Morning brief must be sent via message() and include thought process per ticker.',
      'Unread alerts in queue must be sent immediately before other tasks.'
    ];
    for (const c of critical) {
      await client.add([{ role: 'user', content: c }], { user_id: userId, version: 'v2' });
    }
    console.log('OK:seed-critical');
    return;
  }

  throw new Error('Usage: mem0_helper.js <add|search|seed-critical> ...');
}

run().catch((e) => {
  console.error(e.message || String(e));
  process.exit(1);
});
