# tools/ — Guide

Business logic scripts and service connectors. Called by playbooks/, skills/, or the MCP server.

## How to pick a tool

1. **Check the active skill first.** `skills/<role>/CLAUDE.md` names the specific file to use for each scenario. This is the primary source.
2. **If unsure which file to use**, consult `tools/INDEX.md` — full per-script descriptions with layer tags.
3. **Before calling any service**, read `tools/manual/<service>.md` — each manual lists what cases it covers and a minimal how-to.

## Skill doc convention

- If tool needs auth, env vars, browser profile, external side effects, or multi-step workflow: skill should point to the manual first, then the exact script/tool path.
- If tool is a short local helper with obvious inputs/outputs: skill can point directly to the script/tool path.
- Skill docs should always keep the exact script/tool path visible even when a manual is primary.
- Keep long operational setup in `tools/manual/*.md`; keep task-specific usage in the skill MD.

## Trader Utility Scripts (M1.3 / M1.5 additions)

| Script | Purpose | Output |
|--------|---------|--------|
| `trader/universe_scan.py` | Daily universe scan — liquid IDX tickers | `vault/data/universe-YYYY-MM-DD.json` |
| `trader/catalyst_calendar.py` | Upcoming corporate events for active holds | `vault/data/catalyst-YYYY-MM-DD.json` |
| `trader/relative_strength.py` | RS vs IHSG rank within a sector | stdout table |
| `trader/overnight_macro.py` | Prefetch global market closes (03:00 WIB) | `vault/data/overnight-YYYY-MM-DD.json` |

## Fund Manager API Client (M2.5)

| Script | Purpose | Usage |
|--------|---------|-------|
| `fund_api.py` | Thin HTTP client for Go backend at 127.0.0.1:8787 | `from tools.fund_api import api; api.post_signal({...})` |
| `fund_backfill.py` | One-time backfill: vault/data/* → SQLite via API | `python tools/fund_backfill.py --source all` |

`fund_api` is imported by `portfolio_health.py`, `journal.py`, `tradeplan.py`, `runtime_monitoring.py` for dual-write.
On network error: logs warning, returns None — never raises.

## Connectors (service clients)

| Connector   | Type              | MCP | Manual |
|-------------|-------------------|-----|--------|
| stockbit    | REST API          | No  | `manual/stockbit.md`, `manual/stockbit-screener.md` |
| airtable    | REST API + MCP    | Yes | `manual/airtable.md` |
| notion      | Browser + MCP     | Yes | `manual/notion.md` |
| google      | OAuth REST        | Yes | `manual/google.md` |
| threads     | Playwright        | Yes | `manual/threads.md` |
| instagram   | Playwright        | No  | `manual/instagram.md` |
| facebook    | Playwright        | No  | `manual/facebook.md` |
| browser     | Playwright base   | No  | `manual/browser.md` |
| telegram    | Bot API           | No  | `manual/telegram.md` |

Rules: no business logic in connectors. Auth/secrets from `.env.local` only. Prefer MCP for Claude-native tasks; use scripts for scheduled/automated jobs.
