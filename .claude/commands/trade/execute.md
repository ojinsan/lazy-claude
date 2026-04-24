# /trade:execute — L5 Execute

Pure-Python order placement + reconcile. No AI judgment — reads `plan` set by L4.

**Playbook:** `playbooks/trader/layer-5-execute.md`

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md`

**Three paths:**

| Path | When | What |
|------|------|------|
| Pre-open sweep | 08:00–08:45 WIB | Place entry limit orders for all `plan≠None, execution=None` items |
| Reconcile | 09:00–15:15 WIB every 30m | Fetch orders → detect fills → place stop+TP; alert stale |
| Intraday fire | L4 Mode B via Popen | `python -m tools.trader.l5_run --ticker T` (does NOT use this slash) |

**To execute:** read and follow `playbooks/trader/layer-5-execute.md` step by step.

**CRON (spec #8):** Pre-open at 08:30 WIB. Reconcile every 30m 09:00–15:00 WIB Mon–Fri.

**Guardrails:**
- `aggressiveness=off` → abort (healthcheck)
- `execution≠None` → skip (idempotency)
- 5% price drift from plan → abort (circuit breaker)
- Sell without sufficient holdings → skip with telegram warn
- Insufficient cash → skip with telegram warn
- No auto-cancel: stale orders → telegram warn only, Boss decides
