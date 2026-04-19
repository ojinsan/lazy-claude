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

## Catalyst Expiry (Catalyst-Driven Thesis Only)

For theses dependent on a specific catalyst (BI rate cut, dividend, rights issue, government contract):

1. **Pre-catalyst**: score all 6 criteria. Confirm catalyst date/timeline still active.
2. **Catalyst window** (T-2 to T+1 days): apply a tighter test. If price hasn't moved AND broker flow is still net buy → wait. If price hasn't moved AND broker flow flipped to sell → catalyst already priced in or failed. Mark `broken`.
3. **Post-catalyst** (T+2 or later): re-score from scratch. Catalyst is over. Is the structural thesis (broker + SID + technical) still intact without the catalyst? No → mark `broken`.

Special rule: "waiting for catalyst" is not a thesis. If the 6 structural criteria are below 4 and you're only holding for the catalyst → mark `weakening`. Reduce exposure 50%.

## Journal Protocol

Every thesis re-check must produce a journal entry. Use `tools/trader/journal.py`:

```python
# After each re-check, append to the vault thesis file:
journal.append_thesis_review(ticker, layer="L0" or "L3", note=f"score={N}/6, {status}: {one_line_reason}")

# If thesis is broken and trade closed:
journal.log_lesson_v2(
    lesson=f"Exit {ticker}: {reason}",
    category="thesis_quality",     # or "exit_timing" if timing was the issue
    tickers=[ticker],
    severity="medium",             # high if SID flip was missed early
    pattern_tag="thesis-break",    # or "catalyst-failed", "late-exit" etc.
)
```

This creates the feedback loop that catches recurring mistakes in L0 Step 6 (`detect_recurring_mistakes`).

## Hard Rules

- Do not protect the old idea. Protect Boss O's capital.
- Status `broken` is not negotiable — exit, do not "give it one more day."
- Never invent missing evidence. If a criterion can't be tested, score it as failed.
- Re-check is cheap; assuming the thesis still works is expensive.
