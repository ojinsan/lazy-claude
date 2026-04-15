# Layer 1 — Global Context

Build the top-down market map before touching any stock.

## What To Gather

### Global Markets
- US indices (S&P 500, Nasdaq, Dow) — risk-on or risk-off?
- Japan (Nikkei), China (HSI/Shanghai), commodities (oil, gold, coal)
- USD/IDR, DXY, US 10Y yield
- Any macro event: Fed rate, geopolitics, trade war, sanctions

### Indonesia
- IHSG level and trend, foreign net flow
- BI rate direction (key: property/banking sector signal when rate moves)
- Government policy, MSCI events, dividend season, rights issues

### Sector Rotation Logic
- Energy / coal: watch when global energy crisis or commodity spike
- Property / construction: watch when BI cuts rate or stimulus
- Banking: foreign flow, BI rate, credit growth
- Nickel / EV metals: China EV demand, global transition narrative
- Consumer: domestic spending, Lebaran, subsidy policy

## Tools

| Tool | How |
|------|-----|
| RAG v3 | `api.rag_search(query)` — telegram + news insight from backend |
| Threads | `tools/general/playwright/threads-scraper.js` — uses Firefox profile at `~/workspace/tools/general/playwright/.firefox-profile-threads`. **First run:** copy logged-in profile from `~/.mozilla/firefox/6btoqrgn.default-release/` |
| Web browse | Claude native WebFetch/WebSearch for global market news |
| Stockbit proxies | `tools/trader/api.py` → `get_market_context()` |
| Runtime script | `tools/trader/runtime_layer1_context.py` |

## Execution Trigger (Integrated)

**L1 does not execute.** Context-only layer. No orders, no intent messages. Proceed to Output.

## Output (Required)

1. **Market regime**: risk-on / cautious / risk-off + reason
2. **Sector view**: which sectors to focus, which to avoid, and why
3. **Narrative list**: 3–5 active themes driving flow now
4. **Aggression posture**: how aggressive to be today (1–5)
5. **Initial candidates**: tickers that fit the narrative
6. **Post to Airtable** `Insights` for any strong context insight

## Telegram Notify (Scarlett)

Send once per session after L1 output is complete. Skip if already sent for today's L1.

**Trigger conditions (any one):**
- Aggression posture ≤ 2 (cautious/risk-off)
- Regime changed vs yesterday (e.g., risk-on → risk-off)
- Critical macro event detected (Fed, BI rate, geopolitics)
- Always send when completing scheduled 05:00 L1 run

**Send via Bash:**
```bash
python3 tools/trader/telegram_client.py layer1 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --regime "{risk-on/cautious/risk-off}" \
  --posture "{N}/5" \
  --sectors "{active themes, comma-separated}" \
  --key-risk "{one sentence if any, else 'none'}"
```

**Format:** emoji header + bold title + short takeaway + structured `<pre>` block.

**Required env:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**Anti-spam:** Do not send more than once per L1 session. Do not re-send for L3/L4 re-runs.

## Skills To Load

- `skills/trader/macro-context.md`
- `skills/trader/market-sentiment.md`
- `skills/trader/insight-crawling.md`
- `skills/trader/airtable-trading.md`
