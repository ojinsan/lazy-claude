# Trader Skills — Master Index

## Philosophy

Follow the operator (bandar/smart money). Trade with strong hands, not the crowd.
Never confuse price movement with structure. Never confuse retail excitement with accumulation.

**Core principle**: Confluence of narrative + technical structure + smart money flow + SID alignment.
All four should point the same direction before committing. Fewer signals = smaller size or no trade.

---

## Strategy Style

| Style | When | Duration |
|-------|------|----------|
| Swing breakout | After base formation, volume surge, operator confirmed | Days–weeks |
| Pullback to support | Uptrend intact, operator holding, no SID deterioration | Days |
| Catalyst play | Strong narrative + technical alignment | 1–3 days |
| Avoid | SID rising, operator distributing to retail, extended run | — |

**Goal**: Beat IHSG, 50%+ annual. Only take setups with asymmetric risk/reward.

---

## SID Rules (CRITICAL — Read This First)

SID (Shareholders Identity Data) = number of unique shareholders.

| SID direction | Meaning | Signal |
|---------------|---------|--------|
| **Decreasing** | Shares concentrating into fewer hands → accumulation | **BULLISH** |
| **Stable** | No meaningful change in holder base | Neutral |
| **Increasing** | Shares spreading to more retail holders → distribution | **BEARISH** |

**Rate of change matters more than absolute level.**

- SID -10%+ = strong accumulation, someone draining float hard
- SID -3% to -10% = moderate consolidation, shares into stronger hands
- SID +3% to +15% = early distribution, retail starting to receive shares
- SID +15%+ = heavy distribution, retail FOMO phase → danger zone

**Cross-check rule**: SID decrease + smart money buying broker flow = strongest bullish signal.
SID increase + retail broker dominating = distribution trap → avoid or cut.

SID is a SLOW signal (doesn't change daily). Use it to confirm intent, not as entry timing.

---

## Broker Classification

```
Smart money:  AK, ZP, BK, YU, HP, RX, AI, ES, HD, MS, CS, DB, MG, SS, RF, BP
Foreign:      BK, MS, CS, DB, MG, RX, YU, CG, ML
Retail:       XL, XC, YP, CC, KK, PD, SQ, NI, AZ, CP
Prajogo grp:  DP, LG, NI
```

**Broker flow interpretation:**

| Pattern | Meaning |
|---------|---------|
| Smart money accumulating, retail absent | Early stage — best entry window |
| Smart money accumulating, retail joining late | Mid stage — still ok, smaller size |
| Retail buying, smart money exiting quietly | Distribution trap — **do not enter, exit if holding** |
| Smart money distributing, SID rising | Clear distribution — avoid |
| Tektok (same broker buying+selling) | Market making or scalping — not directional |
| Mixed smart money (some buy, some sell) | Unclear — wait for clarity |

**Bandar avg cost vs current price**: if smart money is underwater and still buying → high conviction accumulation.

---

## Screening Criteria (Apply In Order)

1. **Narrative fit** — does the stock match an active Layer 1 theme? No fit = skip.
2. **Technical structure** — base formation or pullback to support, not extended.
3. **Broker flow** — smart money accumulating? Retail dominant? Trap signal?
4. **SID trend** — decreasing (good) or increasing (bad)? Cross-check with broker flow.
5. **Orderbook quality** — real bid support, or fake walls? Bid/offer ratio and wall behavior.
6. **Volume confirmation** — vol ratio > 1x on breakout days, vol ratio < 0.8x on consolidation days.

All six should align. Fewer than 4 aligned = skip or low conviction only.

---

## Skills Index

Load only what the current layer or task needs. Unload after use.

### Layer 1 — Global Context
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `macro-context.md` | Top-down macro + rates + commodities | Always in L1 |
| `market-sentiment.md` | IHSG regime, foreign flow, tape tone | Always in L1 |
| `insight-crawling.md` | Web, RAG, Threads for catalyst intelligence | L1 context fetch |
| `fundamental-narrative-analysis.md` | Sector/catalyst story | L1 theme building |

### Layer 2 — Stock Screening
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `whale-retail-analysis.md` | Broker flow + SID + player intent | Always in L2 |
| `technical-analysis.md` | Structure, trend, support/resistance | Always in L2 |
| `wyckoff-lens.md` | Accumulation/distribution phase | L2 when structure unclear |
| `market-structure.md` | BOS/CHoCH, key levels, invalidation | L2 for each candidate |
| `narrative-building.md` | Why this stock now | L2 for shortlist candidates |

### Layer 3 — Monitoring
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `realtime-monitoring.md` | Alert triage, live changes | Always in L3 |
| `bid-offer-analysis.md` | Orderbook wall behavior | L3 when near key level |
| `thesis-evaluation.md` | Is the thesis still intact? | L3 each review cycle |
| `orderbook-reading.md` | Bid stack quality, absorption | L3 pre-entry check |

### Layer 4 — Trade Plan
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `trade-planning.md` | Entry, invalidation, target, sizing | Always in L4 |
| `risk-rules.md` | Risk discipline, position sizing | Always in L4 |
| `swing-trade-plan.md` | Basic swing plan template | L4 swing setups |
| `pro-orderbook-trade-plan.md` | Execution-sensitive plan with microstructure | L4 orderbook setups |

### Execution
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `execution.md` | Entry/exit rules, sizing formula, order protocol, safety gates | Always in execute layer |

### Support Skills (load on demand)
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `airtable-trading.md` | Insights + Superlist operations | Any layer posting to Airtable |
| `broker-flow.md` | Deep broker flow reading | L2/L3 ambiguous flow |
| `sid-tracker.md` | SID accumulation/distribution detail | L2 when SID signal is key |
| `insight-crawling.md` | Web/RAG/Threads intel | L1 context fetch |
| `journal-review.md` | Past lessons on similar setups | L4 before committing |
| `stockbit-access.md` | Token/auth handling | When auth issues arise |
| `watchlist-4group.md` | Universe management | L2 universe construction |

---

## Tools Map

### Core data (always available)
| Script | What it gives |
|--------|--------------|
| `api.py` | Price, candles, orderbook, broker distribution, SID, running trades, RAG, market context |
| `config.py` | Env, paths, token config |

### Order execution (Carina / Stockbit broker)
| Function | What it does |
|----------|-------------|
| `api.get_cash_info()` | Trade limit, buying power, available balance |
| `api.get_position_detail(ticker)` | Current qty, avg cost, unrealized P&L per stock |
| `api.get_orders(ticker)` | Open/today orders — check for duplicates before placing |
| `api.place_buy_order(symbol, price, shares)` | Place limit buy — **REAL order** |
| `api.place_sell_order(symbol, price, shares)` | Place limit sell — **REAL order** |
| `api.cancel_order(order_id)` | Cancel open order |
| `api.amend_orders([{order_id, price, shares}])` | Bulk amend open orders |

### Analysis scripts
| Script | What it gives | Use in |
|--------|--------------|--------|
| `broker_profile.py` | Player intent, smart money vs retail, trap detection, bandar P&L | L2, L3 |
| `sid_tracker.py` | SID accumulation/distribution signal, intent narrative | L2 |
| `market_structure.py` | Support/resistance, trend, BOS/CHoCH | L2, L4 |
| `indicators.py` | RSI, EMA, ATR, golden cross, cycle signal | L2, L4 |
| `wyckoff.py` | Wyckoff phase detection | L2 |
| `psychology.py` | Behavior at key price levels — WHO is doing WHAT at support/resistance (bandar absorbing vs retail fleeing) | L2, L3 |
| `tick_walls.py` | Orderbook wall analysis, large threshold | L3, L4 |
| `orderbook_poller.py` | Live orderbook polling loop | L3 live |
| `orderbook_ws.py` | WebSocket orderbook stream | L3 live |
| `running_trade_poller.py` | Live tape / running trades | L3 live |
| `realtime_listener.py` | Waterseven-style poll — running trade patterns + orderbook deltas, writes to `runtime/monitoring/realtime/` | L3 live |
| `tradeplan.py` | Trade plan generator | L4 |
| `screener.py` | Full screener pipeline | L2 bulk scan |
| `eval_pipeline.py` | Watchlist evaluation | L2 |
| `narrative.py` | Narrative generation helper | L1, L2 |
| `macro.py` | Macro context helper | L1 |
| `journal.py` | Trade journal read/write | L4, journal review |
| `airtable_client.py` | Airtable read/write for trader tables | Any layer |
| `watchlist_4group_scan.py` | 4-group universe scan | L2 universe |
| `think.py` | Reasoning helper | Any |

### Runtime scripts (scheduled/automated jobs)
| Script | Job |
|--------|-----|
| `runtime_layer1_context.py` | Automated L1 context collection |
| `runtime_layer2_screening.py` | Automated L2 screening pipeline |
| `runtime_monitoring.py` | Periodic monitoring loop |
| `runtime_summary_30m.py` | 30-min market summary |
| `runtime_eod_publish.py` | End-of-day Airtable publish |

### Connectors / MCP
| Tool | What it gives |
|------|--------------|
| Airtable MCP | Read/write Lazytrade base (Insights + Superlist) |
| WebSearch / WebFetch | Global market news, macro data |
| Threads scraper (`tools/general/playwright/threads-scraper.js`) | Social sentiment, operator hints |

---

## Quick Decision Rules

**Enter only when:**
- Narrative fits current Layer 1 theme ✓
- Technical: at or near support, not extended ✓
- Broker: smart money net accumulating ✓
- SID: flat or decreasing ✓
- Orderbook: real bid support present ✓

**Exit / avoid when:**
- SID rising fast + retail brokers dominating
- Smart money exiting while retail piling in
- Thesis narrative broken by tape
- Structure failed (price closed below invalidation)

**Size down when:**
- Only 3/5 signals align
- Regime is cautious (posture 2–3)
- Near distribution zone

**Never:**
- Chase a stock already +5% on the day without a pullback plan
- Enter based on narrative alone without structure
- Ignore SID increase as "fine because price is going up"
