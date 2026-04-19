# Realtime Monitoring

## Purpose

Run the L3 monitoring loop without drowning in noise. Owns: polling cadence, alert triage labels, escalation rules. Does NOT own orderbook reading (see `orderbook-reading.md`), wall classification (`bid-offer-analysis.md`), or whale/retail interpretation (`whale-retail-analysis.md`).

## Cadence

| Source | Interval | When to use |
|--------|----------|-------------|
| `runtime_monitoring.py` | every 10 m | Default L3 polling, writes `runtime/monitoring/intraday-10m.log` |
| `runtime_summary_30m.py` | every 30 m | Rolling 30-min summary, writes `summary-30m.log` |
| `realtime_listener.py --tickers X --interval 30` | 30 s | Active position or live signal hunt |
| `orderbook_poller.py --ticker X --interval 5` | 5 s | Pre-entry / pre-exit window only |
| `running_trade_poller.py` | continuous | Tape participation when verifying absorption/distribution |

Default loop: 10-minute baseline + 30-minute summary. Drop to 30 s / 5 s only inside an active entry/exit window.

## Alert Triage

Every incoming alert gets one label:

| Label | When | Action |
|-------|------|--------|
| `high` | Stop hit, target hit, thesis break, breakout confirmed with follow-through | Boss O alert immediately, send L3 telegram |
| `medium` | New `accumulation_setup` / `shakeout_trap` on tracked name; orderbook flips | Update monitoring log + Airtable Insights |
| `low` | Minor signal, drifting price, wall behavior change without conviction | Local log only |
| `noise` | Stale snapshot, single-tick blip, duplicate alert within session | Discard |

Same signal on same ticker twice in one session → downgrade duplicate to `noise`.

## Escalation Rules

Promote `medium` → `high` when ANY of:
- Tracked ticker is currently held AND signal contradicts thesis
- Two `medium` signals on the same ticker within 15 minutes
- Signal coincides with portfolio DD > 3% from HWM (be more reactive when bleeding)

Demote `high` → `medium` when:
- Source is a single snapshot without confirmation from tape
- Signal lifetime < 60 s before reverting

## Polling Discipline

- Never run two pollers on the same ticker from two scripts — duplicate cost, duplicate alerts.
- Always `kill` the poller after the entry/exit window closes (price moved out of zone, order filled, or 30 min elapsed).
- Pollers write to `runtime/monitoring/realtime/`. Read from there, don't rebuild from scratch.

## Output Per Cycle

For each tracked ticker, produce:
1. **Latest signal** — `accumulating | distributing | noisy | wait | exit`
2. **Triage label** — `high | medium | low | noise`
3. **Promotion / demotion** — move to L4, demote from watchlist, or no change
4. **Action queued for L5** — none / pre-place limit / cancel / cut

## Tool Resolution

| Use case | Tool |
|----------|------|
| Cron L3 loop | `tools/trader/runtime_monitoring.py` |
| 30-min summary | `tools/trader/runtime_summary_30m.py` |
| Live event stream | `tools/trader/realtime_listener.py` |
| Live orderbook | `tools/trader/orderbook_poller.py` |
| Live tape | `tools/trader/running_trade_poller.py` |
| Snapshot | `tools/trader/api.py` (`get_price`, `get_orderbook`, `get_running_trade`) |

## Pre-Open Protocol (08:30–09:00 WIB)

Before market opens, run a lightweight pre-open check on all tracked tickers (not the full 10-min loop):

1. `api.get_price(ticker)` → compare pre-open quote vs yesterday close. Gap > 2% up or down = flag.
2. Check opening auction queue direction if available. Large buy queue = early strength.
3. Read last overnight broker flow (from `broker_profile.py` on yesterday's session). Still accumulating?
4. Flag any position where overnight gap breached the invalidation level → pre-market exit decision to L5.

Output: per-ticker `pre-open status` = `gap-up-watch | gap-down-flag | flat | invalidated`. Feed into the first L3 cycle at 09:00.

## Active Queue Management

Never monitor all tickers at maximum intensity. Tier the queue dynamically:

| Tier | Who goes here | Tools running |
|------|--------------|---------------|
| **Active** (up to 3 tickers) | Current holds + any L4 plan in entry window | `realtime_listener.py` + `orderbook_poller.py` (5s) |
| **Watchlist** (up to 10 tickers) | Shortlisted names from L2 with developing signals | `runtime_monitoring.py` (10m) |
| **Background** (rest) | No current signal, thesis check only | 30-min summary only |

Promote to Active: when any watchlist ticker hits `medium` or `high` triage label.
Demote from Active: when entry window closes, order fills, or 45 min elapsed with no signal change.
Remove from queue entirely: when thesis is `broken` or `L3 demoted`.

## Hard Rules

- Monitoring surfaces changes; it does not replace judgment. Every `high` alert still passes through the relevant analysis skill before action.
- No telegram on every tick — only when triage label changes. Use `skills/trader/telegram-notify.md` (`layer3` subcommand) on label change.
- Poller leaks burn quota — verify nothing is running after each L3 session.
