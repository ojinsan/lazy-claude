# /trade:monitor — L3 Intraday Monitoring

10m cron 09:00–15:30 WIB. Per-ticker openclaude tape judge over superlist ∪ exitlist ∪ holdings. BUY-NOW gate → Opus confirm → async /trade:tradeplan invocation.

**Playbook:** `playbooks/trader/layer-3-monitoring.md`.

**Spec:** `docs/superpowers/specs/2026-04-22-trading-agents-revamp-spec-5-l3-monitoring.md`.

**CRON:** Mon–Fri, every 10 min 09:00–15:30 WIB.

**Guardrails:** writes per-ticker `current_plan` + `details`, `intraday_notch`, `layer_runs['l3']`. No writes to watchlist / regime / sectors / narratives / holdings / balance / aggressiveness.
