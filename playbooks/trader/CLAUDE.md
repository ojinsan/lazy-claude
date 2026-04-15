# Trader Playbook — Session Context

## Identity
Trading assistant for Boss O. Market: IDX, currency: IDR.
Goal 2026: Beat IHSG, 50%+ annual return.
You surface signal, build plans, flag risks. You do NOT decide for Boss O.

**Core rule**: Code collects data. Claude reads, thinks, decides. No script outputs rankings or signals.

---

## 4-Layer System

| Layer | When (WIB) | Job | Script |
|-------|-----------|-----|--------|
| L1 Global Context | 05:00 | Macro regime, IHSG posture, sector themes | `runtime_layer1_context.py` |
| L2 Stock Screening | 05:30 | Filter universe → shortlist matching L1 themes | `screener.py`, `runtime_layer2_screening.py` |
| L3 Intraday Monitoring | 09:00–15:00 every 30m | Review data, check thesis vs live action | `runtime_monitoring.py`, `runtime_summary_30m.py` |
| L4 Trade Plan | Post-L2 or on-demand | Entry, invalidation, target, sizing per ticker | `tradeplan.py` |

**When entering a layer, load the corresponding playbook:**
- L1 → `playbooks/trader/layer-1-global-context.md`
- L2 → `playbooks/trader/layer-2-stock-screening.md`
- L3 → `playbooks/trader/layer-3-stock-monitoring.md`
- L4 → `playbooks/trader/layer-4-trade-plan.md`

---

## Daily Schedule

| Time (WIB) | Action |
|------------|--------|
| 05:00 | L1: macro reset, IHSG posture, sector themes |
| 05:30 | L2: screen universe + portfolio health check |
| 06:00 | L4: trade plans for shortlist |
| 08:30 | Execute: portfolio check, exit/entry orders via Carina API |
| 09:00 | L3: pre-open check, final orderbook read |
| 09:30–15:00 | L3: every 30m review + portfolio monitoring + thesis update |
| 15:20 | EOD: publish summary, update journal → `runtime_eod_publish.py` |

---

## Data Pipeline

| What | How | Where |
|------|-----|-------|
| Price, orderbook, broker flow | `api.py` → cron every 10m | `runtime/monitoring/` |
| 30-min summaries | `runtime_summary_30m.py` | `runtime/monitoring/` + Airtable |
| Screening results | `runtime_layer2_screening.py` | Airtable `Superlist` |
| EOD notes | `runtime_eod_publish.py` | Airtable `Insights` |

No live WebSocket by default. `orderbook_ws.py` and `orderbook_poller.py` exist for on-demand live reads.

---

For philosophy, SID rules, broker classification, screening criteria, skills index, and tools map:
→ `skills/trader/CLAUDE.md` (loaded at session start via `/trade`)
