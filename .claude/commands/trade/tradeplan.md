# /trade:tradeplan — L4 Trade Plan

Non-interactive. Opus synth of entry/stop/TP + Python-side IDX tick rounding + lot sizing. Two modes:

- **No arg → Mode A batch** — loops `lists.{superlist,exitlist}` where `current_plan.mode ∈ {buy_at_price, sell_at_price}` AND `plan is None`. Intended post-L2 morning run.
- **Ticker arg → Mode B (if L3 BUY-NOW within 20m) OR Mode A single re-plan** — L3 async-popens this on BUY-NOW.

**Playbook:** `playbooks/trader/layer-4-tradeplan.md`.

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-6-l4-tradeplan.md`.

**CRON (spec #8):** Mon–Fri ~05:30 WIB batch (after L2). Mode B fires on-demand from L3 during 09:00–15:30 WIB.

**Guardrails:** writes per-ticker `plan` + `current_plan.price` + `details`, `layer_runs['l4']`. No writes to watchlist / regime / sectors / narratives / holdings / balance / aggressiveness. No order placement.
