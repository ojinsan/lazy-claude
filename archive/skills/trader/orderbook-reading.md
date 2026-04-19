# Orderbook Reading

## Purpose

Read bid/offer stack quality, depth asymmetry, and refresh dynamics tick-by-tick. Owns the *dynamics* of the book — how levels behave, refresh, and step. Does NOT own wall classification (see `bid-offer-analysis.md`) or absorption pattern read (see `whale-retail-analysis.md`).

## Stack Quality

A stack is "good" when liquidity is genuine and stable. Check four things per snapshot:

| Dimension | Good signal | Bad signal |
|-----------|-------------|------------|
| Distribution | Tapered — biggest size at best, decreasing into back | Inverted (size jumps further back) → spoof setup |
| Broker count | ≥ 3 brokers per top-3 level | 1 broker dominating top-3 → thin disguise |
| Tick gap | Tight, no gaps in top 5 levels | Gapping levels → low real depth |
| Refresh cadence | Refreshes after fills, holds during quiet | Vanishes only when price approaches → reactive, fake |

## Depth Asymmetry (vs Time)

Single snapshot ratio is from `bid-offer-analysis.md`. Here we track the ratio *over time*:

- Compute `ratio = bid_depth_5lv / ask_depth_5lv` every poll
- Trend ratio over 5–10 polls
  - Rising ratio + rising price → real demand absorbing supply
  - Rising ratio + flat price → bidders building base, breakout pending
  - Falling ratio + flat price → silent distribution, exit caution
  - Falling ratio + falling price → confirmed sell pressure

## Refresh Dynamics

What happens at the best price after a trade:

| Pattern | Read |
|---------|------|
| Bid eaten → new bid steps up at higher price | Aggressive buyer chasing — bullish |
| Bid eaten → new bid same price, same size, same broker | Patient accumulator re-listing |
| Bid eaten → no refresh, gap appears | Demand exhausted at level |
| Offer eaten → next offer higher, smaller size | Supply thinning, breakout odds rise |
| Offer eaten → next offer same price, refreshes | Real overhead resistance |
| Offer eaten → wall reappears bigger | Distribution underway, do not chase |

## Crossing Behavior

Tape crosses at bid (sell) vs at offer (buy):
- Crosses dominantly at offer with size up = real demand (markup phase)
- Crosses dominantly at bid with size up = real supply (markdown phase)
- Crosses both sides with size up = churn (Wyckoff range, no edge)
- Crosses only on tiny lots = no participation, ignore the tape

Pull crossing data from `tools/trader/running_trade_poller.py` or `realtime_listener.py`.

## Spoofing Indicators

Mark book as suspect spoof when:
- Top-3 bid wall flips to top-3 offer wall within seconds (same broker reverses side)
- Large levels in mid-book (level 3–5) but top-1 stays thin
- Refresh cadence faster than 1 s per cancel/replace cycle

Do not interpret spoofed books as accumulation/distribution — flag and wait for genuine flow.

## Tool Resolution

| Use case | Tool |
|----------|------|
| Snapshot orderbook | `api.get_stockbit_orderbook(ticker)` |
| Continuous polling | `tools/trader/orderbook_poller.py` |
| Live stream | `tools/trader/orderbook_ws.py` |
| Tape (crossing side, lot size) | `tools/trader/running_trade_poller.py` |
| Combined live | `tools/trader/realtime_listener.py --tickers X --interval 30` |

## Output

Each orderbook read returns:
1. **Stack quality** — `genuine` / `thin` / `spoofed`
2. **Depth trend** — direction of ratio over recent polls + price reaction
3. **Refresh signal** — chasing / patient / exhausted / churn / spoof
4. **Confidence** — `clean read` / `partial` / `no read` (no read = abstain)
5. **Confirmation cue** — what next price action would validate the read

## Session Context

Book behavior is different by session phase. Adjust interpretation:

| Session phase | What to watch | What to ignore |
|---------------|--------------|----------------|
| Pre-open (08:30–09:00) | Opening auction queue size + side imbalance | Bid/ask ratio (no crossing yet) |
| First 30 min (09:00–09:30) | Aggressive crosses at offer (markup) or bid (markdown) | Any individual refresh in isolation |
| Midday (11:00–13:30) | Depth ratio trend over 10+ polls | Single-snapshot imbalance (lunch hour book is thin) |
| Power hour (14:00–15:00) | Refresh pattern at support/resistance | Noise crosses — lots < 10 are institutional algos not direction |
| Closing auction (15:45–16:00) | Final queue direction; large orders arrive here | Book during pre-close is illiquid and easily spoofed |

## Pre-Entry Checklist

Before calling a read "entry-ready" based on orderbook alone:

1. Stack quality is `genuine` (not `thin` or `spoofed`)
2. Depth ratio trending in favor of entry direction for ≥ 5 consecutive polls
3. Refresh shows `chasing` or `patient` (NOT `exhausted` or `spoof`)
4. Tape crossing confirms at entry side (offer crosses for buys, bid crosses for sells)
5. At least one of the above confirmed via `realtime_listener.py`, not just snapshot

If 3 of 5 → `partial read`. Still use, but reduce size by 50%.
If < 3 → no read. Abstain.

## Hard Rules

- Book is not perfect truth. Always confirm with tape (running trade) before sizing.
- Spoof flag overrides any other read — wait it out.
- A single snapshot is never enough for refresh judgment. Need ≥ 3 polls.
