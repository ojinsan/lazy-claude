# Trading Agents Revamp — Spec #0: Master Design

**Date:** 2026-04-19
**Status:** Draft — pending user approval
**PRD (source of truth):** `vault/developer_notes/REVAMP PLAN.md`

This is the high-level orientation for the whole revamp. Every detail spec (#1, #2, ...) drills into one area of this document.

---

## 1. Vision & Principles

- **MECE layers.** Trading process split into L0–L5, each with one clear job, no overlap, nothing missing.
- **Single passable JSON.** `current_trade.json` = shared state. Every layer reads it, enriches it, saves it. No hidden side-channels.
- **Autonomous.** Each layer triggers by CRON or by prior-layer signal. Claude reads, thinks, decides. Python collects and executes.
- **AI where judgment matters, code where precision matters.** Per-ticker screening, insight synthesis, tradeplan = Claude. Realtime signal detection, order placement, snapshot math = Python.
- **Clean start.** Archive old implementation. Resurrect with confirmation, not copy-paste.
- **Dual model tier.** Opus for decisions. openclaude (API via settings file) for cheap per-ticker. Bidirectional fallback on rate-limit/error.

---

## 2. System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                        current_trade.json (shared state)              │
└────────────────▲──────────▲───────▲───────▲───────▲───────▲──────────┘
                 │          │       │       │       │       │
          ┌──────┴────┐  ┌──┴──┐  ┌─┴─┐  ┌──┴──┐  ┌─┴──┐  ┌─┴──┐
          │    L0     │  │ L1  │  │L2 │  │ L3  │  │ L4 │  │ L5 │
          │ Portfolio │  │Insi.│  │Scr│  │Mon. │  │Plan│  │Exec│
          └───────────┘  └──┬──┘  └───┘  └──┬──┘  └────┘  └────┘
                            │               │
                      ┌─────┴────┐    ┌─────┴────┐
                      │ L1-A TG  │    │ realtime │
                      │ L1-B Thr │    │ WS+poll  │
                      └──────────┘    └──────────┘
```

**Lists in `current_trade`**: filtered → watchlist → superlist → exitlist. Each layer moves tickers across lists per its own rules.

---

## 3. Per-Layer High-Level

Each table row = one layer. Detail specs cover logic.

### L0 — Portfolio Analysis
- **Trigger:** CRON 03:00 WIB
- **Model:** Opus
- **Reads:** Carina balance/positions, yesterday PnL, yesterday orders, thesis state.
- **Writes:** `trader_status` (balance, PnL, holdings, aggressiveness).
- **Logic:**
  - Pull broker positions + cash.
  - Compute realized/unrealized PnL, MtD, YtD.
  - Check thesis drift for each holding.
  - Set aggressiveness posture (defensive/neutral/aggressive).
  - Flag 2+ redflag holdings for exit consideration.
- **Detail spec:** #2.

### L1 — Insight & Context Synthesis
- **Trigger:** CRON 04:00 WIB
- **Model:** Opus
- **Reads:** L1-A telegram RAG DB, L1-B threads RAG DB, macro/catalyst data, broker flow screener.
- **Writes:** `trader_status.regime`, `trader_status.sectors`, `trader_status.narratives`, `lists.watchlist`.
- **Logic:**
  - Query RAG: top-confidence tickers, sector themes.
  - Connect-dots: news + broker flow + retail-avoidance screener.
  - Set regime (risk-on/off, cautious).
  - Promote tickers into watchlist with confidence + narrative.
  - Telegram recap: sectors, ticker count, top narratives.
- **Detail spec:** #3.

### L1-A — Telegram Listener (helper)
- **Trigger:** CRON every 30 min
- **Model:** none (pure Python)
- **Reads:** Telegram channels.
- **Writes:** Insight DB chunks. Not `current_trade`.
- **Logic:** Scrape → chunk → embed → store. Expose RAG query API for L1.
- **Detail spec:** #3 (bundled with L1).

### L1-B — Threads Listener (helper)
- **Trigger:** CRON every 6 hours
- **Model:** none (pure Python)
- **Reads:** Threads (logged-in Playwright scraper).
- **Writes:** Insight DB chunks. Not `current_trade`.
- **Logic:** Scrape → chunk → embed → store. Expose RAG query API for L1.
- **Detail spec:** #3 (bundled with L1).

### L2 — Screening
- **Trigger:** CRON 05:00 WIB
- **Model:** openclaude per-ticker (serial), Opus for final merge
- **Reads:** watchlist + holdings, Stockbit EOD bars, broker flow, SID, narratives (L1), yesterday bid-offer.
- **Writes:** `lists.superlist` (and `exitlist` if holding degrades).
- **Logic (per ticker):**
  - 4-dim analysis: price/volume/wyckoff, broker+SID, yesterday tx/bid-offer, narrative.
  - Each dim scored: `redflag | weak | strong | superstrong`.
  - Promotion rules (PRD): 1 superstrong OR 3 strong OR 2 strong + 0 redflag → superlist.
  - Holdings MUST be included; 2 redflags → exitlist.
- **Merge step (Opus):** promote winners, assign `current_plan: buy_at_price | sell_at_price | wait_bid_offer`.
- **Telegram:** superlist recap.
- **Detail spec:** #4.

### L3 — Monitoring
- **Trigger:** multiple
  - Realtime WebSocket (Stockbit) — Python, continuous during market
  - CRON every 10 min (market hours 09:00–15:00) — Python, backup snapshot
  - CRON every 30 min (market hours) — Claude, AI review
- **Model:** openclaude (30m review). Python for realtime/10m.
- **Reads:** superlist entries with `wait_bid_offer`, live orderbook, transactions, bid-offer book, broker activity.
- **Writes:** entry signals → trigger L4. Updates `current_plan` when signal fires.
- **Logic:**
  - Python realtime: thick-wall detection, withdrawn-wall detection, support-break-buy, breakout-with-buying. High-confidence → immediate L4+L5 fire. Medium/low → stash for 30m AI review.
  - 30m AI: digest last 30m tape, judge if signal valid, trigger L4 if so.
- **Detail spec:** #5.

### L4 — Trade Plan
- **Trigger:** signal from L2 (`buy_at_price`/`sell_at_price`) or L3 (entry signal).
- **Model:** Opus
- **Reads:** target ticker context from `current_trade` (holdings, balance, aggressiveness, narrative, superlist entry).
- **Writes:** full trade plan (bid, offer, cutloss, TP, trailing stop) into the ticker's superlist entry `details`.
- **Logic:**
  - Size per aggressiveness + remaining buying power.
  - Entry at given price or microstructure-optimized bid.
  - Invalidation = cutloss price. TP ladder. Trailing stop trigger.
- **Detail spec:** #6.

### L5 — Execute
- **Trigger:** new L4 plan OR CRON every 30 min (success check).
- **Model:** none (pure Python)
- **Reads:** superlist entries with a finalized plan, Stockbit/Carina order API.
- **Writes:** order IDs into superlist entry, Telegram notify, holdings refresh on fill.
- **Logic:**
  - Place buy/sell with plan params. Set cutloss + TP + trailing stop where supported.
  - Validate lot size, tick rules.
  - 30m check: reconcile open orders vs plan, escalate failure to Telegram.
- **Detail spec:** #7.

---

## 4. CRON Schedule (Full)

| Time (WIB)  | Days | Kind | What |
|-------------|------|------|------|
| 03:00       | Mon–Fri | claude | `/trade:portfolio` (L0) |
| 04:00       | Mon–Fri | claude | `/trade:insight` (L1) |
| 05:00       | Mon–Fri | claude | `/trade:screening` (L2) |
| every 30m   | always  | python | L1-A telegram listener |
| every 6h    | always  | python | L1-B threads listener |
| 08:30       | Mon–Fri | python | Pre-open L5 sweep (cancel stale, place planned entries) |
| 09:00–15:00 | Mon–Fri | python | L3 realtime WS + 10m snapshot |
| every 30m 09:00–15:00 | Mon–Fri | claude | `/trade:monitor` (L3 AI review) |
| every 30m 09:00–15:00 | Mon–Fri | python | L5 order success check |
| on signal   | Mon–Fri | claude | `/trade:tradeplan` (L4) triggered by L2/L3 |
| 15:20       | Mon–Fri | claude/python | EOD publish (summary + journal) |

Weekend: listeners only.

---

## 5. Shared Infra

All layers depend on these. Built in spec #1.

- **`tools/_lib/current_trade.py`** — Pydantic schema, `load()`, `save(ct, layer, status, note)`, snapshots.
- **`tools/_lib/ratelimit.py`** — token buckets: `stockbit` (req/s), `claude_api` (req/min, covers Opus SDK + openclaude subprocess).
- **`tools/_lib/claude_model.py`** — `run(prompt, model, fallback)` with bidirectional Opus↔openclaude fallback on 429/5xx/timeout.

---

## 6. Archive & Scaffold (spec #1 scope)

- Archive `skills/trader/`, `playbooks/trader/`, `.claude/commands/trade*`, `runtime/cron/trader_*.sh`, `runtime/crontab-*.txt` → `archive/...` (mirrored paths).
- Keep `tools/trader/*` live (MCP deps).
- Create stub slash commands + empty trader skill/playbook CLAUDE.md.
- Bootstrap `docs/revamp-progress.md` (tool × layer × status table).

---

## 7. Roadmap (Order of Detail Specs)

| Spec | Scope | Blocks | Status |
|------|-------|--------|--------|
| #0 | Master (this doc) | — | **draft** |
| #1 | Core + Archive/Scaffold | #2–#7 | **draft** |
| #2 | L0 Portfolio | #4 (holdings input), #6 (sizing input) | not started |
| #3 | L1 + L1-A + L1-B | #4 (narratives input) | not started |
| #4 | L2 Screening | #6 (plan trigger) | not started |
| #5 | L3 Monitoring | #6 (plan trigger) | not started |
| #6 | L4 Trade Plan | #7 (order input) | not started |
| #7 | L5 Execute | — | not started |
| #8 | Orchestration / CRON wiring | — | not started |

Build order: #1 → #2 → #3 → #4 → #5 → #6 → #7 → #8.
Each detail spec = own brainstorm → design → plan → implement cycle.

---

## 8. Out of Scope (for whole revamp)

- Go backend `current_trade` backup — separate project after JSON stable.
- `tools/trader/*` internal refactor — per-layer audit during each detail spec.
- MCP server changes — not touched.
- UI/dashboard — not in this revamp.
