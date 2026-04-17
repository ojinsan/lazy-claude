# Thesis Evaluation

## Purpose

Re-test whether an open thesis is still working. Owns: 6-criteria re-check protocol, invalidation test, status verdict. Does NOT own SID rules (see `whale-retail-analysis.md`) or screening criteria definitions (in `skills/trader/CLAUDE.md`).

## When To Run

- L0 Step 4: every hold, every morning
- L3: every monitoring cycle for tracked names with signals
- L4: before finalizing a new plan on a ticker with prior history
- Pre-exit: before placing any sell from L5

## Inputs

- Original thesis from `vault/thesis/<TICKER>.md` (or Airtable `Superlist` if no thesis note)
- Original L4 plan: entry, stop, target, invalidation, days held vs horizon
- Live: `api.get_price(ticker)`, `api.get_broker_distribution(ticker)`, `api.get_stockbit_sid_count(ticker)`, latest L3 monitoring log

## 6-Criteria Re-Check

Re-run each screening criterion (definitions in `skills/trader/CLAUDE.md`):

| # | Criterion | How to re-test now |
|---|-----------|--------------------|
| 1 | Narrative fit | Does today's L1 theme list still include this stock's sector? |
| 2 | Technical structure | Is structure intact (above last accumulation low / above invalidation)? |
| 3 | Volume / liquidity | Is daily volume holding above 20d avg? Or drying up? |
| 4 | Broker / whale signal | Smart-money still net buy in last 5 sessions? Use `broker_profile.py` |
| 5 | Orderbook quality | Bid stack still genuine? Or spoofed? Use `orderbook-reading.md` |
| 6 | SID direction | Still decreasing (accumulation)? Use `sid_tracker.py` |

Score: how many of 6 still pass.

## Invalidation Test (Hard)

Mark thesis BROKEN when ANY of:
- Price closed below the L4 invalidation level (intraday wick OK, close not OK)
- SID flipped to clearly increasing for ≥ 3 sessions
- All smart-money codes flipped to net `sell_days` ≥ 3 sessions
- Original catalyst confirmed cancelled (catalyst-driven thesis only)

Broken = exit decision goes to L5, no debate.

## Status Verdict

Combine 6-criteria score + invalidation test:

| Score (of 6) | Invalidation hit? | Status |
|--------------|-------------------|--------|
| 6 | no | `intact` — hold or add |
| 4–5 | no | `weakening` — hold, no add |
| ≤ 3 | no | `needs more evidence` — pause, monitor closely |
| any | yes | `broken` — exit |

Time gate: regardless of score, if `days_held > 1.5× planned_horizon` and price < entry → mark `weakening` minimum.

## Output

Produce per ticker:
1. **Status** — `intact | weakening | needs more evidence | broken`
2. **Score** — N of 6 + which criteria failed
3. **Invalidation hit?** — yes/no + which one
4. **Action** — hold / add / pause / reduce / exit
5. **One-line reason** for journal

Append to `vault/thesis/<TICKER>.md` Review Log section. Never overwrite original thesis.

## Tool Resolution

| Use case | Tool |
|----------|------|
| Live price + flow | `api.get_price`, `get_broker_distribution`, `get_stockbit_sid_count` |
| Packaged broker read | `tools/trader/broker_profile.py` |
| SID trend | `tools/trader/sid_tracker.py` |
| Original plan + notes | Airtable `Superlist` via `airtable_client.py` |
| Past lessons on similar setup | `tools/trader/journal.py` |

## Hard Rules

- Do not protect the old idea. Protect Boss O's capital.
- Status `broken` is not negotiable — exit, do not "give it one more day."
- Never invent missing evidence. If a criterion can't be tested, score it as failed.
- Re-check is cheap; assuming the thesis still works is expensive.
