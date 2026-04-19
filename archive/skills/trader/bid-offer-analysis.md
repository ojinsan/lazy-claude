# Bid-Offer Analysis

## Purpose

Classify orderbook walls and judge authenticity. Translate book shape into one of: break likely, bounce likely, wait, exit. Owns wall taxonomy + authenticity + pressure imbalance metrics. Does NOT own absorption pattern reading (see `whale-retail-analysis.md`) or stack quality dynamics (see `orderbook-reading.md`).

## Wall Size Classification (Indonesian terms)

| Term | Depth | Default strength |
|------|-------|------------------|
| `satu papan` | wall at best bid/offer (1 level) | weakest — easily faked, often retail blocker |
| `dua papan` | wall spans 2 price levels | medium — real defense, still flippable |
| `keseluruhan` | wall across 3+ price levels | strong — real resistance/support OR coordinated whale distribution/accumulation |

Strength is a default. Authenticity overrides it.

## Authenticity (Fake vs Real Wall)

A wall is likely **fake** when ANY of:
- Appears immediately before a price level and disappears within 30 s without trades hitting it
- Size is large but `order_count` is 1 (single broker placeholder, not real liquidity)
- Wall position chases the tape: moves up as price rises, down as price falls
- Wall reappears at similar size after being eaten — same broker re-listing

A wall is likely **real** when ALL of:
- Persists ≥ 2 minutes with consistent size
- Multiple broker IDs contributing to the level (use `api.get_orderbook(ticker)` → broker breakdown)
- Absorbs trades — offer count drops tick-by-tick as buys hit it, price grinds through over time

Unclear → label `unclear`, do not act.

## Absorption Patterns (Bandar Eating Retail)

### Near Resistance — Break Likely

Signature:
- Thick offer wall above (classify via Wall Size section)
- Whale bids underneath, refreshing as retail sells hit them
- Offer wall slowly thins — hidden buy orders eating through it
- Running trade: sell-side lots are small (retail < 100 lots), buy-side lots are large (≥ 500 lots) hitting at the bid

Read: smart money accumulating through the resistance wall. The wall is theirs — meant to scare retail, not block themselves.
Action hint: `break likely`. Pre-place entry limit just inside or at the wall.

### Near Support — Bounce Likely

Signature:
- Thick bid wall below price
- Wall holds despite panic retail sells hitting it
- Offer side thinning — sellers exhausting
- Running trade: small lot sellers + large lot buyers = absorption, not distribution

Read: bandar holding the floor. Retail selling INTO smart money's accumulation.
Action hint: `bounce likely`. Do not sell into this wall.

### Critical Distinction — Absorption vs Distribution

When a thick bid wall sits below a rising price, it can be EITHER:

| Running trade signature | Verdict |
|-------------------------|---------|
| Large lot SELLER + small lot BUYER at bid | **Distribution** — whale unloading into retail FOMO. Exit or skip. |
| Small lot SELLER + large lot BUYER at bid | **Accumulation** — whale absorbing retail panic. Ride or enter. |

Never decide from wall shape alone. The lot-size breakdown from `running_trade_poller.py` is mandatory before calling absorption.

## Pressure Imbalance Metrics

Compute from a single snapshot (`api.get_stockbit_orderbook(ticker)`):

| Metric | Formula | Read |
|--------|---------|------|
| Bid/Ask ratio (top 5 lv) | `sum(bid_qty[0:5]) / sum(ask_qty[0:5])` | **Unreliable alone** — big players post fake thick bids to lure retail. Use as secondary only. |
| HAKA/HAKI ratio | `buy_vol / sell_vol` from running trades | > 1.5 = real buying pressure (buyers actively hitting offer); < 0.7 = selling pressure |
| Absorption signal | Thick OFFER wall + steady price + HAKA > HAKI | Price holds despite wall = smart money silently absorbing retail sells → Case 3 |
| Depth asymmetry | `bid_depth_5lv / ask_depth_5lv` | same threshold; tracks shape over time |
| Wall persistence | seconds wall survives before being pulled | < 30 s = fake; > 120 s = real |

For continuous tracking, poll with `tools/trader/orderbook_poller.py --ticker X --interval 5` and diff snapshots.

## Tool Resolution

| Use case | Tool |
|----------|------|
| Single snapshot | `api.get_stockbit_orderbook(ticker)` |
| Continuous poll | `tools/trader/orderbook_poller.py --ticker X --interval 5` |
| Live WebSocket stream | `tools/trader/orderbook_ws.py` |
| Wall detection (large threshold scan) | `tools/trader/tick_walls.py` |
| Snapshot-to-snapshot delta | `api.get_orderbook_delta(ticker)` |

## Decision Output

Every bid-offer read produces:
1. **Wall classification** — `satu papan` / `dua papan` / `keseluruhan`
2. **Authenticity** — `fake` / `real` / `unclear`
3. **Pressure read** — bid pressure / sell pressure / balanced (with bid/ask ratio number)
4. **Action hint** — `break likely` / `bounce likely` / `wait` / `exit`

## Examples

> Price 1,250. Offer wall at 1,260, `satu papan`, 500k lot, 1 broker. Running trade: 10k lot buys hitting bid continuously.

Read: likely fake wall (size + 1 broker), buyer pressure underneath. If wall persists < 2 min with shrinking size → break likely. Action: pre-place limit at 1,255–1,258.

> Price 2,400. Bid wall at 2,380, `keseluruhan`, 4 brokers, holding 8 minutes. Offer side thinning.

Read: real wall (depth + multiple brokers + persistence). Bid/ask ratio likely > 1.5. Action: bounce likely from 2,380.

## Example Prompts

> "Price 1,250. Thick offer at 1,260 (`satu papan`, 500k lot, 1 broker). Running trade shows 10k-lot buys hitting the bid continuously."
>
> Read: likely fake wall (1 broker, large single order). Buyer pressure underneath. If wall persists < 2 min with shrinking size → `break likely`. Pre-place limit at 1,255–1,258.

---

> "Price 2,400. Bid wall at 2,380 (`keseluruhan`, 4 brokers, holding 8 minutes). Offer side thinning. Running trade: 5k-lot retail sellers, 200k-lot buyer refreshing at 2,380."
>
> Read: real wall (depth + multi-broker + persistence). Large lot buyer = whale defending. `bounce likely` from 2,380.

---

> "Price 850. Thick bid wall at 820. Price rising. Running trade: 500k-lot seller + 10k-lot buyers."
>
> Read: Distribution disguised as support. Whale unloading into retail bids. `exit` if holding. `skip` if considering entry.

## Hard Rules

- A thick wall is not a conclusion. The conclusion is in how the wall behaves over time.
- Never act on `unclear`. Wait for the next snapshot or skip.
- Wall taxonomy alone is not enough — combine with absorption read (see `whale-retail-analysis.md`) before sizing up.
