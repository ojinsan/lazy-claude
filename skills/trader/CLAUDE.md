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

### Layer 0 — Portfolio (Hedge-Fund View)
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `portfolio-management.md` | Position sizing, concentration limits, drawdown thresholds | Always in L0 |
| `sector-exposure.md` | Sector bucket mapping, max exposure rules, rotation triggers | Always in L0 |
| `probability-measurement.md` | Win rate, expectancy, Kelly fraction for sizing decisions | L0 calibration step |
| `money-flow-analysis.md` | Aggregate foreign flow, smart-money direction across holds | L0 portfolio flow check |
| `portfolio-self-review.md` | Daily self-review protocol, lesson logging template | L0 self-evaluation step |
| `thesis-drift-check.md` | Re-check thesis validity for each hold | L0 per-hold thesis review |

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
| `volume-price-rules.md` | 4-quadrant VP state, sizing caps | L2 criterion 2.5 — see Scoring section for full detail |
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
| `telegram-notify.md` | Single source of truth for every telegram subcommand + trigger rule | Any layer sending Telegram |
| `broker-flow.md` | Deep broker flow reading | L2/L3 ambiguous flow |
| `sid-tracker.md` | SID accumulation/distribution detail | L2 when SID signal is key |
| `insight-crawling.md` | Web/RAG/Threads intel | L1 context fetch |
| `journal-review.md` | Lesson protocol, kill-switch, hit_rate_by, thesis actions, intraday posture, calibration | L0 Step 0+6, L4 pre-plan, L5 sizing, EOD sync |
| `stockbit-access.md` | Token/auth handling | When auth issues arise |
| `watchlist-4group.md` | Universe management | L2 universe construction |

### Tape & Microstructure (M3.3+ — load when relevant)
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `spring-setup.md` | Wyckoff Phase C spring conditions, entry/stop rules, failure mode | L2 spring override, L3 wick_shakeout, L4 Mode B spring path |
| `imposter-detection.md` | Smart money hiding in retail codes — lot size + timing anomalies | L3 every cycle when broker flow ambiguous |
| `tape-reading.md` | 9-case tape reading reference — walls, markup, spam, crossing, spring | L3 every cycle for all monitored names |

### Scoring (M3.2/M3.6 — load when evaluating setups)
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `volume-price-rules.md` | 4-quadrant VP state, thresholds, sizing caps | L2 criterion 2.5, L3 every cycle |
| `confluence-scoring.md` | 0–100 composite score, buckets, anti-game rules | L2 final gate, L3 cycle output, L4 plan, L5 entry gate |
| `auto-trigger.md` | Auto-invoke Claude on high-conviction signals — gates, dedup, budget | Loaded by monitoring runtime only |

### Ownership & Flow (M3.1 — load when checking konglo)
| Skill | Purpose | Load when |
|-------|---------|-----------|
| `konglo-ownership.md` | Conglomerate group mapping, leader-laggard rotation, size cap rules | L1 group rotation scan, L2 criterion 6, L4 plan |

### New Capabilities (M1 additions — load when relevant)
| Function | Where | When |
|----------|-------|------|
| `journal.kill_switch_state()` | L0 Step 0, L5 pre-entry | Before any new entry — abort if active |
| `journal.set_thesis_action(ticker, action)` | L0 Step 4 | After each hold drift-check |
| `journal.get_thesis_actions()` | L2 input, L4 input | Filter exit-candidates from promotion |
| `journal.set_intraday_posture(posture, reason)` | L3 11:30 / 14:00 | Mid-day regime flip |
| `journal.hit_rate_by(dim, days)` | L4 pre-plan | Cap risk if pattern win-rate < 40% |
| `journal.load_previous_orders()` | L0 Step 1.5 | Review yesterday's execution |
| `universe_scan.py` | L2 Universe Prep | Daily at 04:00 WIB via cron |
| `catalyst_calendar.py` | L1 Indonesia, L4 inputs | Daily at 04:00 WIB via cron |
| `relative_strength.py` | L2 criterion 3.5 | Per-sector RS ranking |
| `overnight_macro.py` | L1 Global Markets | Daily at 03:00 WIB via cron |

---

## Tools

For the full script index, connectors, and manuals → `tools/CLAUDE.md`

Trader skill doc rule:
- Stockbit, Airtable, Telegram, browser/profile-based tools, and other service-heavy tools should point to `tools/manual/*.md` first, then the exact script.
- Local analysis helpers like `market_structure.py`, `indicators.py`, `wyckoff.py`, `tradeplan.py`, `broker_profile.py`, and similar trader-local scripts can stay direct in the skill MD.
- Keep exact script paths visible in every skill even when manual is primary.

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
- Enter based on narrative alone without structure
- Ignore SID increase as "fine because price is going up"
