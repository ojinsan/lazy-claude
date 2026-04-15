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
| Threads | `tools/general/playwright/threads-scraper.js` — uses Firefox profile at `~/.claude/tools/general/playwright/.firefox-profile-threads`. **First run:** copy logged-in profile from `~/.mozilla/firefox/6btoqrgn.default-release/` |
| Web browse | Claude native WebFetch/WebSearch for global market news |
| Stockbit proxies | `tools/trader/api.py` → `get_market_context()` |
| Runtime script | `tools/trader/runtime_layer1_context.py` |

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
curl -s -X POST "https://api.telegram.org/bot8781123769:AAHceKJY0FepJIqBCnHqd9DP3_BHro01Cgc/sendMessage" \
  -d "chat_id=1139649438" \
  --data-urlencode "text=L1 $(date +%Y-%m-%d) | Regime: {risk-on/cautious/risk-off} | Posture: {N}/5
Sectors: {active themes, comma-separated}
Key risk: {one sentence if any, else 'none'}"
```

**Anti-spam:** Do not send more than once per L1 session. Do not re-send for L3/L4 re-runs.

## Skills To Load

- `skills/trader/macro-context.md`
- `skills/trader/market-sentiment.md`
- `skills/trader/insight-crawling.md`
- `skills/trader/airtable-trading.md`
