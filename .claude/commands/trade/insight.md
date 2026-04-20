# /trade:insight — L1 Insight & Context Synthesis

Run the L1 layer: L1-A freshness gate → parallel fetch (RAG + HAPCU + retail-avoider + macro + catalyst + Lark) → Opus synthesizes regime + sectors + narratives + watchlist → validate + single-shot retry → write `trader_status.{regime, sectors, narratives}` + `lists.watchlist` via `current_trade.save()`, append daily note, always-send Telegram recap.

Load playbook and follow it exactly:

**Playbook:** `playbooks/trader/layer-1-insight.md`

**Spec:** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-3-l1-insight.md`

CRON: Mon–Fri 04:00 WIB. Depends on telegram-scraper (L1-A) systemd unit being live — stale → hard abort.

Guardrails (see playbook §Guardrails): no order writes, no touch to L0 fields (balance/pnl/holdings/aggressiveness) or L2 lists (filtered/superlist/exitlist), keep previous state on error.
