# Whale–Retail Analysis

## Purpose

Read broker flow, SID, and tape participation to judge who is doing what. Owns: broker code taxonomy, absorption/distribution patterns, lot-size signals, trap detection. Does NOT own wall taxonomy (see `bid-offer-analysis.md`) or stack dynamics (see `orderbook-reading.md`).

## Broker Code Taxonomy

```
Smart money (domestic + foreign):
  AK, ZP, BK, YU, HP, RX, AI, ES, HD, MS, CS, DB, MG, SS, RF, BP

Foreign desks:
  BK, MS, CS, DB, MG, RX, YU, CG, ML

Retail flow:
  XL, XC, YP, CC, KK, PD, SQ, NI, AZ, CP
```

A broker code carries weight only with consistency. A single day from a smart-money code means nothing.

## SID Direction (Hard Rule)

```
SID DECREASING = accumulation = bullish
SID INCREASING = distribution = bearish
```

Never read SID rising as "more interest." It means retail is absorbing supply someone else is feeding.

Source: `tools/trader/sid_tracker.py` and `api.get_stockbit_sid_count(ticker)`.

## Broker Consistency Check

Pull from `api.get_broker_distribution(ticker)`:

| Pattern | Verdict |
|---------|---------|
| `buy_days` high, `sell_days` low (smart money code) | Committed accumulator |
| `buy_days ≈ sell_days` | Tektok / market making — no directional read |
| `sell_days` high (smart money code) | Distribution in progress |
| Same smart-money code present across consecutive days | High-conviction sponsor |
| Smart money avg cost underwater + still buying | Maximum conviction — operator defending position |

Use `tools/trader/broker_profile.py` for a packaged read (intent + trap detection + P&L).

## Absorption Patterns (Bandar Eating Retail)

### Near Resistance (break likely)

Setup signature:
- Thick offer wall above (read via `bid-offer-analysis.md`)
- Whale bids beneath, refreshing as retail sells hit them
- Offer wall slowly thins as hidden buys eat it

Lot-size confirmation:
- Sells = small retail lots (< 100 lots)
- Buys = larger consistent lots (≥ 500 lots) at the bid

Verdict: smart money accumulating through the wall. Size up entry.

### Near Support (bounce likely)

Setup signature:
- Thick bid wall below
- Wall holds despite retail panic sells
- Offers above start thinning, sellers giving up

Verdict: bandar holding the floor. Bounce setup.

### Distinguish Absorption From Distribution

When a thick bid wall sits below a rising price, it can be either:

| Tape signature | Verdict |
|----------------|---------|
| Large lot SELLER, small lot BUYER | Distribution — whale unloading into retail FOMO |
| Small lot SELLER, large lot BUYER | Accumulation — whale absorbing retail panic |

Use `running_trade_poller.py` lot-size breakdown to make this call. Never decide from level shape alone.

## Trap Detection

A trap is: aggressive retail buying (XL, YP, CC high `buy_days`) while smart money has high `sell_days`. Price may still be rising — this is the smart money exit window. Entering = buying directly from the operator.

Hard refusal: do not enter when ALL of:
- Top retail brokers in top-5 buy by value
- Any smart-money broker in top-5 sell by value
- SID rising

## Late-Distribution Warning

Retail FOMO + smart money exit = late distribution. If currently holding:
- Cut at next bounce
- Do not "wait for one more leg up"

## Tool Resolution

| Use case | Tool |
|----------|------|
| Full player profile + trap | `tools/trader/broker_profile.py` |
| SID accumulation / distribution | `tools/trader/sid_tracker.py` |
| Live tape participation | `tools/trader/running_trade_poller.py` |
| Snapshot broker breakdown | `api.get_broker_distribution(ticker)` |
| SID raw | `api.get_stockbit_sid_count(ticker)` |

## Output

Every whale–retail read returns:
1. **Dominant player + intent** — name the code(s), state intent
2. **Smart money state** — accumulating / distributing / absent
3. **Retail state** — early / late-FOMO / capitulating / quiet
4. **Trap?** — yes/no + evidence (specific codes + days)
5. **Verdict** — `sponsored` / `distributed` / `unclear`

## Multi-Day Consistency Score

Single-day broker data is noisy. Score consistency over 5–10 trading days:

```
For each smart-money broker code found in top-10 buyers:
  consistency = buy_days / (buy_days + sell_days)
  score = "committed" if consistency >= 0.7
          "mixed"     if 0.4 <= consistency < 0.7
          "exiting"   if consistency < 0.4
```

| Combined score | Verdict |
|----------------|---------|
| ≥ 2 "committed" smart-money codes | Strong sponsor — size up |
| 1 "committed" + no "exiting" | Moderate sponsor — normal size |
| Only "mixed" codes | Unclear — wait or small size |
| Any "exiting" smart-money code | Distribution risk — reduce size or skip |

## Bandar Avg Cost vs Current Price

Use `broker_profile.py` to estimate smart-money average cost:
- **Smart money underwater + still buying**: highest-conviction accumulation signal. Operator will NOT exit at a loss — markup is coming.
- **Smart money at breakeven + buying accelerating**: sponsor consolidating position before markup.
- **Smart money comfortably above cost + sell_days rising**: primary distribution phase. Exit or skip.
- **Smart money at cost + neutral**: no edge either direction. Wait.

## Hard Rules

- "Smart money buying" requires consistent high `buy_days` from a known smart-money code. One day proves nothing.
- SID direction overrides individual lot reads when they conflict.
- No verdict without lot-size evidence — level shape alone is not enough.

## Retail Code Anomalies
If retail codes show lot sizes or timing patterns inconsistent with retail behavior, see `imposter-detection.md` (M3.4) before drawing conclusions from broker flow.
