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

## Hard Rules

- Book is not perfect truth. Always confirm with tape (running trade) before sizing.
- Spoof flag overrides any other read — wait it out.
- A single snapshot is never enough for refresh judgment. Need ≥ 3 polls.
