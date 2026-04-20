# /trade:portfolio — L0 Portfolio Analysis

Run the L0 layer: read Carina balance/positions/orders, compute pnl rollup, synthesize aggressiveness + per-holding thesis drift notes with Opus, write `trader_status.{balance, pnl, holdings, aggressiveness}` via `current_trade.save()`, append daily note, alert Telegram on redflags.

Load playbook and follow it exactly:

**Playbook:** `playbooks/trader/layer-0-portfolio.md`

**Spec:** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`

Guardrails (see playbook §Guardrails): no order writes, no regime/list writes, keep previous state on error.
