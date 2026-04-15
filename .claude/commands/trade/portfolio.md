---
name: trade:portfolio
description: L0 portfolio health check — hedge-fund view before daily screening. Runs at 04:30 WIB non-interactively.
disable-model-invocation: true
---

Non-interactive. Run to completion and exit. Do not wait for user input.

## Sequence

Execute `playbooks/trader/layer-0-portfolio.md` in full.

## Output

1. Write portfolio health card to `runtime/portfolio/YYYY-MM-DD.md` (WIB date).
2. Update `vault/data/portfolio-state.json` via `tools/trader/portfolio_health.py`.
3. Send Telegram `layer0` message with computed equity, MTD return, drawdown, open risk, top exposure, and action summary.
