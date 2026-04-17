# Fund Manager Plan — Master Index

**Author:** Opus 4.7, for Boss O.
**Date:** 2026-04-16.
**Audience:** a cheaper model (Sonnet/Haiku) executing this plan end-to-end.

This directory has two missions. Do Mission 1 first — it reshapes how Claude operates. Mission 2 depends on the outputs of Mission 1.

---

## Missions

| # | File | Goal | Estimate |
|---|------|------|----------|
| 1 | `mission-1-integration-audit.md` | Make L0–L5 talk to each other. Close gaps in journaling, scheduling, universe exploration. | ~2–3 sessions |
| 2 | `mission-2-system-build.md` | Build a Go backend + Next.js dashboard + SQLite + Redis. Wire the workspace to it via a thin Python client. | ~4–6 sessions |
| 3 | `mission-3-strategy-depth.md` | Add konglo mode, volume-price, spring, imposter, tape reading, confluence scoring, auto-trigger. 7 prefixed tool families + matching skills. | ~3–5 sessions |

**Order of execution:** M1 → M3 → M2 is allowed (M3 can begin as soon as M1 lands; M2 scaffolding and schema should be done after M3 defines the new tables to avoid reworking migrations). Recommended fastest path: M1, then M3 through M3.7, then M2.1–M2.7, then M3.8 last (adds migrations on top of M2's schema).

---

## Ground Rules (READ EVERY SESSION)

1. **One phase per commit.** Prefix commit message with `[M1.Phase N]` or `[M2.Phase N]`. Push after Boss O ack on first push.
2. **Never delete; archive.** If you replace a file, move the old one to the sibling `archive/` folder.
3. **No silent scope creep.** If a phase grows beyond what's written, stop and ask Boss O.
4. **Keep token budget tight.** `grep`/`glob` before `read`. Read only the file + line-range you need. Do NOT bulk-read `docs/`, `skills/`, or `tools/`.
5. **Paths are absolute.** Working directory is `/home/lazywork/workspace`. Every file path in this plan is absolute.
6. **Update the three CLAUDE.md files whenever you create/rename/move a file:**
   - New script → `tools/CLAUDE.md`
   - New skill → `skills/trader/CLAUDE.md` skills index
   - New playbook → `playbooks/trader/CLAUDE.md`
7. **Test before declaring done.** Every phase ends with a "Verify" block — run each check. If any fails, fix before commit.
8. **Ask Boss O for destructive decisions only.** File moves, archive promotion, schema migrations that drop data, and the first `git push` all need explicit OK.

---

## Directory Map After Both Missions

```
workspace/
├── docs/fund-manager-plan/          # this plan (do not edit during execution)
├── playbooks/trader/                # layer playbooks — edited in M1
├── skills/trader/                   # skills — edited in M1
├── tools/trader/                    # scripts — edited in M1 + M2
├── vault/                           # Obsidian MD — still the human record
│   └── data/                        # JSON source of truth for the dashboard
├── code/
│   └── fund-manager/                # M2 deliverable
│       ├── backend/                 # Go service
│       ├── frontend/                # Next.js app
│       ├── data/                    # fund.db SQLite + migrations
│       └── README.md
└── runtime/cron/                    # cron dispatcher edits in M1
```

---

## Stack Decisions (already made — do not re-argue)

### Backend

- **Language**: Go 1.22+.
- **Router**: `github.com/go-chi/chi/v5` (light, idiomatic, no magic).
- **SQLite**: `modernc.org/sqlite` (pure-Go, no cgo — deploys clean).
- **Redis**: `github.com/redis/go-redis/v9`.
- **Migrations**: plain `.sql` files under `backend/migrations/` run by the app on boot. No migration framework.
- **Config**: read from `../.env.local` at repo root (already holds `REDIS_*`, `AIRTABLE_*`, etc.).
- **No auth**. Bind to `127.0.0.1:8787` only.

### Frontend

- **Framework**: Next.js 15 (App Router).
- **Styling**: Tailwind CSS.
- **Components**: `shadcn/ui` — copy-paste primitives, no runtime dependency.
- **Data fetching**: `fetch()` inside server components for reads; `fetch()` + mutate hook for writes.
- **Charts**: `recharts`.
- **No auth**. Dev server on `127.0.0.1:3000`.

### Integration

- **From Python to Go**: `tools/fund_api.py` — thin `requests` wrapper around the Go API. Every workspace script that today writes to `vault/data/*.json` will additionally (or instead) POST to the Go API.
- **Vault stays**. Obsidian MD files are the human record; SQLite is the machine record for the dashboard. Dual-write from `journal.py` and `portfolio_health.py`.

---

## Execution Order

### Mission 1 (M1)

| Phase | Deliverable |
|-------|-------------|
| M1.1 | Layer integration audit report (`docs/fund-manager-plan/output/m1-audit.md`) |
| M1.2 | Close inter-layer gaps — edit playbooks + skills |
| M1.3 | Expand universe exploration — screener wired into L2, catalyst calendar |
| M1.4 | Upgrade journaling — attribution, calibration feedback, stale thesis enforcement |
| M1.5 | Upgrade scheduling — weekly/monthly review cron, overnight scrape, kill switch |
| M1.6 | Integration smoke test — simulate one trading day on paper, commit `vault/journal/simulated-YYYY-MM-DD.md` |

### Mission 2 (M2)

| Phase | Deliverable |
|-------|-------------|
| M2.1 | Scaffold repo structure + health endpoint |
| M2.2 | SQLite schema + migrations + seed from `vault/data/` |
| M2.3 | API surface — CRUD for every entity (portfolio, holdings, tradeplan, signal, thesis, lesson, watchlist, theme, transaction, layer_output, evaluation, performance_daily) |
| M2.4 | Redis integration — hot price/orderbook cache, signal queue |
| M2.5 | Python client `tools/fund_api.py` + dual-write in `journal.py`, `portfolio_health.py`, `runtime_*.py` |
| M2.6 | Next.js dashboard pages — overview, portfolio, watchlist, tradeplans, signals, journal, thesis, themes, performance, evaluation, ticker-drill |
| M2.7 | End-to-end test — run L0 via cron, verify data lands in dashboard, verify Python client returns same |

### Mission 3 (M3)

| Phase | Deliverable |
|-------|-------------|
| M3.1 | Konglo mode — loader + flow + skill + L1/L2/L4 wiring |
| M3.2 | Volume-price state classifier + 4-quadrant skill + L2/L3 wiring |
| M3.3 | Spring detector + skill + L2/L3/L4 integration |
| M3.4 | Imposter detector + skill + L3 wiring |
| M3.5 | Tape reading — 9 case modules + `tape_runner` + skill + L3 wiring |
| M3.6 | Confluence score 0–100 + skill + L2–L5 gating |
| M3.7 | Auto-trigger with dedup + daily budget + telegram-first |
| M3.8 | Dashboard + DB extensions (migrations 0006+, `/tape`, `/konglo`, `/confluence` pages) |

---

## Acceptance Criteria (all three missions done)

- [ ] Every layer playbook cites inputs from at least one upstream layer AND a downstream layer that reads its output.
- [ ] Running the cron for one full trading day produces: daily note, L0 state, L1 regime, L2 shortlist, L3 monitoring log per ticker, L4 tradeplans, L5 orders log, EOD review — all visible in the dashboard.
- [ ] `journal.py` writes to both `vault/data/` AND the Go API. Data in one matches the other.
- [ ] Dashboard shows equity curve, current portfolio, open tradeplans, last 48h signals, current themes, today's daily note. All load in <1s on localhost.
- [ ] Python can query the dashboard: `fund_api.get_holdings()`, `fund_api.get_tradeplans(date)`, etc. Returns typed dicts.
- [ ] A human (Boss O) can read the dashboard top-to-bottom and know: what the portfolio looks like, what plans exist, what signals fired today, what the thesis is for each hold, and what lessons are active.
- [ ] Every L3 monitoring cycle writes a `tape_state` row and a `confluence_score` row per tracked ticker.
- [ ] Konglo group view loads; each hold surfaces group peers and rotation state.
- [ ] Auto-trigger fires only when all gates pass (confluence 80+, tape high confidence, DD<5%, posture≥2, kill-switch off, not deduped, under daily budget). Log of triggers is visible in the dashboard.

---

## If You Get Stuck

1. Re-read the relevant section in this plan. The answer is usually in the phase's own "Verify" block.
2. Grep the codebase for prior art: `Grep "func .*<capability>"` under `tools/trader/`.
3. If still stuck, write a one-paragraph summary of the blocker into `docs/fund-manager-plan/output/blockers.md` and ask Boss O.
4. Never invent a solution that touches files outside the phase's declared scope.
