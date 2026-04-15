# Layer 3 — Stock Monitoring

Watch shortlisted names closely during market hours. Understand whale intent, not just price.

## Portfolio Monitoring (Run First, Every Cycle)

For each ticker in Airtable `Superlist` where Status = `Hold`:
```python
pos = api.get_position_detail(ticker)   # current qty, avg cost, P&L
```
Check against L4 plan:
- Price vs invalidation level → if breached, flag for exit
- Price vs Target 1 → if hit, flag for 50% reduce
- `distribution_setup` or `wick_shakeout` in latest 30m data → update thesis status
- Unrealized P&L: if ≤ -5% from avg cost AND thesis signal weakening → escalate to Boss O alert

Output per hold: `intact | reduce | exit | watch`

---

## What To Monitor

### Price & Volume
- Running trades: are real buyers/sellers stepping in?
- Volume surge vs price action — accumulation or distribution?
- Tape speed: slow grind up = controlled; spike with panic = retail-driven

### Orderbook (Bid/Offer Shape)
- Where is the nearest thick offer wall? Is it fake (retail blocker) or real resistance?
- Does the wall refresh, shrink, or disappear?
- Does bid step up per tick into the wall?
- Price acceptance above the wall after absorption = constructive

### Manipulation Signals
- `accumulation_setup`: thick offer wall + whale bids underneath → smart money accumulating while retail fears the wall
- `distribution_setup`: thick bid wall + whale offers behind it → whale distributing into retail attraction
- `shakeout_trap`: engineered price dip (wall appears, price drops) but whale bids hold → deliberate retail flush
- `wick_shakeout`: price dips >1.5% but whale bids remain → smart money held through the dip

### Wyckoff Phase
- Is the stock in accumulation, markup, distribution, or markdown?
- Any spring / test / sign of strength pattern?

## Tools

| Tool | How |
|------|-----|
| Orderbook + running trade | `tools/trader/runtime_monitoring.py` (cron every 10m → `intraday-10m.log`) |
| 30-min summary | `tools/trader/runtime_summary_30m.py` (cron every 30m → `summary-30m.log`) |
| Tick walls | `tools/trader/tick_walls.py` |
| Orderbook WS | `tools/trader/orderbook_ws.py` |
| Running trade | `tools/trader/running_trade_poller.py` |
| Wyckoff | `tools/trader/wyckoff.py` |
| Psychology at levels | `tools/trader/psychology.py` — use when price hits wall or key level, judge bandar intent |
| Realtime listener | `tools/trader/realtime_listener.py --tickers X Y --interval 30` — continuous crossing/flow events → `runtime/monitoring/realtime/` |

## Output (Required)

Apply three output levels to every ticker assessed:

| Level | When | Action |
|-------|------|--------|
| **local only** | Signal early, noisy, or developing | Write to monitoring log only |
| **Airtable Insights** | Worth preserving — clean early accumulation, manipulation edge | Post to `Insights` |
| **Boss O alert** | Materially actionable NOW — entry open, thesis break, stop trigger | Flag explicitly |

Default to `local only`. Promote only when genuinely warranted. Do not stay silent on a name worth preserving just because it is not yet L4-ready.

Per ticker:
1. **Signal update**: accumulating / distributing / noisy / wait
2. **Manipulation flag**: note any `accumulation_setup` or `shakeout_trap` explicitly
3. **Promotion**: move to Layer 4 if golden setup appears
4. **Demotion**: remove from watchlist if thesis breaks

## Telegram Notify (Scarlett)

Send only on new signal detection. Do NOT send on every 30-min tick — only when something changes.

**Trigger conditions (any one):**
- New `accumulation_setup` or `shakeout_trap` detected for any shortlisted ticker
- `wick_shakeout` with whale bids holding — high-priority alert
- Thesis break: any tracked name invalidated → demotion
- Name promoted to Layer 4 (golden setup)

**Send via Bash:**
```bash
python3 tools/trader/telegram_client.py layer3 \
  --timestamp "$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M WIB')" \
  --ticker "{TICKER}" \
  --signal "{signal_type}" \
  --note "{one-line description of what was detected}" \
  --action "{watch/promote to L4/demote}"
```

**Format:** emoji header + bold title + short takeaway + structured `<pre>` block.

**Required env:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**Anti-spam:** One message per new signal per ticker per session. Same signal on same ticker = no repeat. Batch multiple signals in one message if detected together.

## Skills To Load

- `skills/trader/orderbook-reading.md`
- `skills/trader/bid-offer-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/realtime-monitoring.md`
- `skills/trader/airtable-trading.md`
