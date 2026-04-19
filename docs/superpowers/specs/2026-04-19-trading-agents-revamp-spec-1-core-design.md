# Trading Agents Revamp — Spec #1: Core + Archive/Scaffold

**Date:** 2026-04-19
**Status:** Draft — pending user approval
**PRD:** `vault/developer_notes/REVAMP PLAN.md` (source of truth)

---

## 1. Context

Current trader implementation is messy: inconsistent sources, hidden bugs (e.g. ticker limitation), skills that drifted from principles, shallow docs. We are rebuilding from scratch as MECE, scalable, autonomous layered agents (L0–L5), each connected through a single JSON object (`current_trade`). Old code is archived (not deleted) so the new build can reference it during resurrection.

This spec is the **first of several**. It delivers only the ground truth that every later layer spec will depend on:

1. The `current_trade` JSON data contract.
2. Shared infra: schema module, rate limiter, Opus↔openclaude model wrapper.
3. Archive of old trader wiring (skills, playbooks, slash commands, cron).
4. Scaffold: empty dirs + stub slash commands + stub CLAUDE.md files.
5. Progress-tracking document for `tools/trader/*` (kept live due to MCP dependency).

Out of scope: any L0–L5 layer logic; L1-A (telegram listener) / L1-B (threads listener); Go backend backup; MCP server changes; refactor of `tools/trader/*` internals.

---

## 2. Decisions (from brainstorm)

| Topic | Decision |
|-------|----------|
| Persistence | JSON file primary. Go backend backup planned later (not this spec). |
| File layout | Live `runtime/current_trade.json` + per-run snapshots `runtime/history/YYYY-MM-DD/LN-HHMM.json`. |
| Archive scope | Everything trader-related **except** `tools/trader/*`. Preserves MCP deps. Tools status tracked separately in progress doc. |
| Schema | PRD base + `layer_runs`, `version`, `schema_version`. |
| Invocation pattern | Mixed. Some layers = pure python cron (L1-A, L1-B, L3 realtime, L3 10m, L5). Others = `claude -p "/trade:<layer>"` (L0, L1, L2, L3 30m, L4). |
| Per-ticker parallelism | **Serial** (reduce conflict risk) + rate limiter. |
| Model tier | Opus for decisions (L0, L1, L2 merge, L4). openclaude for cheap per-ticker (L2 per-ticker, L3 30m review). Bidirectional fallback on error/rate-limit. |
| Archive layout | Mirrored — `archive/skills/trader/`, `archive/playbooks/trader/`, `archive/.claude/commands/trade/`, `archive/runtime/cron/`. |
| Progress doc | Single file `docs/revamp-progress.md` with tool | used-by-layer | status | notes table. |

---

## 3. `current_trade` Schema

### 3.1 File location

- Live: `runtime/current_trade.json` (gitignored)
- Snapshots: `runtime/history/YYYY-MM-DD/<layer>-HHMM.json` (gitignored)

### 3.2 Shape

```json
{
  "schema_version": "1.0.0",
  "version": 42,
  "updated_at": "2026-04-19T05:30:12+07:00",

  "lists": {
    "filtered":  [{"ticker": "BBCA", "confidence": 60, "current_plan": null, "details": "..."}],
    "watchlist": [{"ticker": "BMRI", "confidence": 75, "current_plan": null, "details": "..."}],
    "superlist": [{"ticker": "ADRO", "confidence": 85,
                   "current_plan": {"mode": "buy_at_price", "price": 2500},
                   "details": "..."}],
    "exitlist":  [{"ticker": "BREN", "confidence": 20,
                   "current_plan": {"mode": "sell_at_price", "price": 6500},
                   "details": "..."}]
  },

  "trader_status": {
    "regime": "risk-on",
    "aggressiveness": "medium",
    "sectors": ["banking", "coal"],
    "narratives": [{"ticker": "ADRO", "content": "...", "source": "threads", "confidence": 80}],
    "balance": {"cash": 12000000, "buying_power": 24000000},
    "pnl": {"realized": 500000, "unrealized": -120000, "mtd": 300000, "ytd": 2100000},
    "holdings": [{"ticker": "BBRI", "lot": 10, "avg_price": 4200,
                  "current_price": 4350, "pnl_pct": 3.57}]
  },

  "layer_runs": {
    "l0": {"last_run": "2026-04-19T03:00:05+07:00", "status": "ok", "note": "..."},
    "l1": {"last_run": "2026-04-19T04:00:30+07:00", "status": "ok", "note": "..."},
    "l2": {"last_run": "2026-04-19T05:35:00+07:00", "status": "ok", "note": "..."},
    "l3": {"last_run": null, "status": "pending", "note": null},
    "l4": {"last_run": null, "status": "pending", "note": null},
    "l5": {"last_run": null, "status": "pending", "note": null}
  }
}
```

### 3.3 Enums

- `current_plan.mode`: `"buy_at_price" | "sell_at_price" | "wait_bid_offer" | null`
- `layer_runs[lN].status`: `"ok" | "error" | "pending" | "skipped"`

### 3.4 Invariants

- `version` monotonic; bumped on every `save()`.
- `updated_at` ISO-8601 with timezone (WIB `+07:00`).
- `schema_version` semver string; migration required on bump.

---

## 4. Components

### 4.1 Directory layout after this spec

```
tools/_lib/
├── current_trade.py    # schema (Pydantic) + load/save/snapshot
├── ratelimit.py        # token bucket for stockbit + claude
└── claude_model.py     # Opus↔openclaude wrapper with fallback

runtime/
├── current_trade.json       # live state (gitignored)
└── history/YYYY-MM-DD/      # per-run snapshots (gitignored)

archive/                     # new top-level, mirrors old paths
├── skills/trader/
├── playbooks/trader/
├── .claude/commands/trade/
└── runtime/
    ├── cron/                # trader_*.sh
    └── crontab-*.txt

skills/trader/CLAUDE.md      # stub — rebuilt per-layer in later specs
playbooks/trader/CLAUDE.md   # stub — rebuilt per-layer in later specs
.claude/commands/trade/
├── portfolio.md   # stub — body "TBD L0"
├── insight.md     # stub — L1
├── screening.md   # stub — L2
├── monitor.md     # stub — L3
├── tradeplan.md   # stub — L4
└── execute.md     # stub — L5

docs/revamp-progress.md      # tool status tracker
```

### 4.2 `tools/_lib/current_trade.py`

Pydantic models for every nested object. Public API:

```python
from tools._lib.current_trade import load, save, snapshot, CurrentTrade

ct: CurrentTrade = load()
ct.lists.superlist.append(...)
save(ct, layer="l2", status="ok", note="...")
```

- `load()` — read live file, Pydantic-validate. Missing file → return empty skeleton with `schema_version="1.0.0"`, `version=0`, empty lists, empty trader_status, all `layer_runs` `"pending"`.
- `save(ct, layer, status, note)` — bump `version`, set `updated_at`, update `layer_runs[layer]`, atomic-write live file, also write snapshot to `runtime/history/YYYY-MM-DD/<layer>-HHMM.json`.
- `snapshot(ct, label)` — manual snapshot (debug).

### 4.3 `tools/_lib/ratelimit.py`

Token-bucket rate limiter. Module exports two named buckets:

```python
from tools._lib.ratelimit import stockbit, claude_api

stockbit.acquire()
resp = requests.get(...)

claude_api.acquire()
call_claude(...)
```

- Defaults: stockbit 5 req/s, claude 10 req/min. Configurable via env (`RATELIMIT_STOCKBIT_RPS`, `RATELIMIT_CLAUDE_RPM`).
- `claude_api` bucket guards **both** Opus SDK calls and openclaude subprocess calls (same Anthropic backend quota).
- Single-process safe (threading.Lock).
- Cross-process coordination not required — CRON schedule is spaced and layers run serially.

### 4.4 `tools/_lib/claude_model.py`

```python
from tools._lib.claude_model import run

text = run(prompt, model="opus", fallback="openclaude")
```

- `model="opus"` path: Anthropic SDK direct call (reads `ANTHROPIC_API_KEY`).
- `model="openclaude"` path: subprocess `claude --settings .claude/settings.openclaude.json -p "<prompt>"`.
- Fallback trigger: HTTP 429, 5xx, timeout, `RateLimitError`.
- On both-fail → raise `ModelError`.

---

## 5. Data Flow

```
CRON (03:00)  ──►  claude -p "/trade:portfolio"
                       │
                       ▼
               skill/playbook read
                       │
                       ▼
    tools/_lib/current_trade.py :: load()
                       │
                       ▼
    python tools/trader/<helpers>  (stockbit/etc, via ratelimit.stockbit)
                       │
                       ▼
    claude_model.run(prompt, "opus", fallback="openclaude")
                       │
                       ▼
    mutate ct.trader_status / ct.lists / ...
                       │
                       ▼
    save(ct, layer="l0", status="ok")
         │                │
         ▼                ▼
  current_trade.json   runtime/history/2026-04-19/l0-0300.json
```

Invariants:

- Exactly one process writes `current_trade.json` at a time (CRON spacing guarantees no overlap at current schedule).
- Atomic write: write `.tmp` then `os.replace()` → live file never half-written.
- Snapshot pattern `<layer>-HHMM.json` identifies who wrote and when.

---

## 6. Archive & Scaffold Procedure

### 6.1 Files to archive (by source path)

| Source | Destination |
|--------|-------------|
| `skills/trader/*.md` (incl. existing `archive/` inside) | `archive/skills/trader/` |
| `playbooks/trader/*.md` (incl. existing `archive/` inside) | `archive/playbooks/trader/` |
| `.claude/commands/trade.md`, `.claude/commands/trade/*.md` | `archive/.claude/commands/trade/` |
| `runtime/cron/trader_*.sh` | `archive/runtime/cron/` |
| `runtime/crontab-clean.txt`, `runtime/crontab-updated.txt` | `archive/runtime/` |

`tools/trader/*` is **not archived**. Tracked in progress doc instead.

### 6.2 Scaffold after archive

- Create stub `skills/trader/CLAUDE.md` — one line: "Rebuilt per-layer via spec-N. See `docs/superpowers/specs/`."
- Create stub `playbooks/trader/CLAUDE.md` — same convention.
- Create six stub slash commands under `.claude/commands/trade/` — each with body `# /trade:<layer>` and a line `TBD — rebuilt in spec #<N>`.
- Ensure `runtime/current_trade.json` and `runtime/history/` paths are gitignored. Append to `.gitignore` if needed.

### 6.3 Progress doc bootstrap

Create `docs/revamp-progress.md` with initial table populated from current `tools/trader/` listing. Columns:

| tool | used-by-layer | status | notes |
|------|---------------|--------|-------|
| `api.py` | (TBD) | live | stockbit facade |
| ... | ... | ... | ... |

`status` values: `live` | `improved` | `unused` | `deprecate-candidate`.

At spec bootstrap time all tools start as `live, unassigned`. Each later layer spec updates the rows for tools it consumes.

---

## 7. Error Handling

| Condition | Behaviour |
|-----------|-----------|
| Live file missing | `load()` returns empty skeleton. No error. |
| Schema validation fail on load | Pydantic raises, process exits non-zero, CRON wrapper alerts via Telegram. No silent corruption. |
| Atomic write crash | `.tmp` written but not renamed → live file unchanged. Next run re-creates `.tmp`. |
| Opus 429/5xx/timeout | Fallback to openclaude via `claude_model.run`. |
| openclaude 429 | Fallback to Opus. |
| Both model paths fail | Raise `ModelError`; layer saves `status="error"` with note; CRON wrapper alerts Telegram. |
| Stockbit 429 | ratelimit bucket slows up front; on real 429 response, exponential backoff max 3 retries, then `save(status="error", note="stockbit down")`. |
| `schema_version` mismatch | Raise. Migration is an explicit dev action — not auto. |

---

## 8. Testing

- `tests/test_current_trade.py`
  - load empty → skeleton with correct defaults.
  - save bumps `version` by 1.
  - save writes live + snapshot at expected path.
  - atomic write: simulate crash between `.tmp` write and rename → live file unchanged.
  - `schema_version` mismatch → raises.
- `tests/test_ratelimit.py`
  - bucket fills and drains at configured rate.
  - `acquire()` blocks when empty, releases when token available.
- `tests/test_claude_model.py`
  - mock Opus 429 → fallback invokes openclaude subprocess path.
  - mock both paths fail → raises `ModelError`.
- No integration tests in this spec (no layer logic exists yet).

### Archive verification

Post-archive one-shot check: grep archived skills/playbooks for `tools/trader` references. List findings into `docs/revamp-progress.md` so each tool's historical consumer is recorded before resurrection starts.

---

## 9. Open Items (tracked, not resolved in this spec)

- Exact rate-limit numbers (`RATELIMIT_STOCKBIT_RPS`, `RATELIMIT_CLAUDE_RPM`) — tune during L2 build when real traffic pattern known.
- Go backend backup path — separate future spec.
- Schema migration policy beyond v1 — deferred until first migration needed.
- `tools/trader/*` audit and deprecation — happens per-layer as specs consume them.
