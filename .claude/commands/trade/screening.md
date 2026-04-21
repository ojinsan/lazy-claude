# /trade:screening — L2 Stock Screening

Run L2: healthcheck gate → dedup universe (watchlist ∪ holdings) → fetch yesterday broker-flow caches → per-ticker openclaude full-judge across 4 dims (price/wyckoff/spring/vp/RS, broker+SID+konglo, yesterday bid-offer, narrative) → deterministic promotion truth table → Opus final merge assigning `current_plan` → write `lists.superlist` + `lists.exitlist` via `current_trade.save()`, append daily note, always-send Telegram recap.

Load playbook and follow exactly:

**Playbook:** `playbooks/trader/layer-2-screening.md`

**Spec:** `docs/superpowers/specs/2026-04-21-trading-agents-revamp-spec-4-l2-screening.md`

CRON: Mon–Fri 05:00 WIB. Depends on L0 (04:45) + L1 (04:00) same day — stale L1 → hard abort.

Guardrails (see playbook §Guardrails): no order writes, no touch to L0 fields (balance/pnl/holdings/aggressiveness) or L1 fields (regime/sectors/narratives/watchlist) or `lists.filtered`, keep prior state on error.
