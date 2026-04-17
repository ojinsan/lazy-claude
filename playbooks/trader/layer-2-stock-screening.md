# Layer 2 — Stock Screening

Filter the full universe down to a high-conviction shortlist.

## Input

- Layer 1 market regime, sector view, and narrative list
- Current watchlist from Airtable `Superlist`
- Today's thesis-action state: `journal.get_thesis_actions()` → `vault/data/thesis-actions.json`
  - Any ticker with action `exit-candidate` must NOT be promoted or added today. Substitution in the same sector is allowed.
- Kill-switch check (already run in L0 Step 0): if active, skip all screening. Document only.

## Universe Prep (Run Before Screening)

Load today's expanded candidate pool:

1. **Universe**: `vault/data/universe-<today>.json` — run `python tools/trader/universe_scan.py` first if missing. Filters: price 50–50K, avg vol ≥ 500K lots.
2. **Catalyst calendar**: `vault/data/catalyst-<today>.json` — run `python tools/trader/catalyst_calendar.py` if missing. Note any events within 3 trading days for shortlisted names.
3. **Relative strength**: `python tools/trader/relative_strength.py --sector <L1 top sector> --days 20`. Prefer names in top 5 RS; deprioritize bottom 5 unless clear accumulation overrides.

## Portfolio Health (Run First)

Before screening new candidates, check existing holds:

For each ticker in Airtable `Superlist` where Status = `Hold`:
1. Re-run screening criteria — does it still pass ≥3/5?
2. Check SID direction — still accumulation or flipped to distribution?
3. Check broker flow — smart money still holding or exiting?

If hold fails ≥2 criteria → flag for exit review in L4.
If hold still passes → confirm thesis intact, carry forward.

## Screening Criteria (Apply In Order)

1. **Narrative fit** — does the stock match an active Layer 1 theme?
2. **Technical structure** — base formation, trend, near support, not extended
2.5. **Volume-price state** <!-- M3.2 --> — `vp_analyzer.classify(ticker, '1d')`. Drop if `weak_rally` or `distribution` without offset signal (spring or shakeout).
3. **Volume / liquidity** — adequate volume, no illiquid traps
3.5. **Relative strength** — in top 5 of sector RS (`relative_strength.py`)? If bottom 5 without strong accumulation → skip.
4. **Broker / whale signal** — accumulation pattern in broker flow or SID
5. **Orderbook quality** — is there real bid support, or just noise?
6. **Konglo fit** <!-- M3.1 --> — `konglo_loader.group_for(ticker)`. If ticker belongs to a group in today's L1 `rotation_in` list → +1 conviction bucket. If portfolio already holds a peer in the same group → either substitute (if weaker peer exists) or skip.

## Tools

| Tool | How |
|------|-----|
| Stockbit screener | `tools/trader/stockbit_screener.py` (**placeholder** — API credentials pending) |
| Watchlist API | `tools/trader/api.py` → `get_watchlist()`, `get_price()`, `get_broker_summary()` |
| Runtime script | `tools/trader/runtime_layer2_screening.py` |
| Wyckoff lens | `skills/trader/wyckoff-lens.md` |
| SID tracker | `skills/trader/sid-tracker.md` |
| Psychology at levels | `tools/trader/psychology.py` — call when price near key support/resistance to judge who is absorbing vs fleeing |

## Advance Decision (Run After Shortlist)

Three questions before advancing. Purpose: size correctly and fit portfolio, not block trades. Only hard-stop at extremes (DD > 10%, posture = risk-off).

### Gate 1 — Ada yang menarik? (Is anything genuinely compelling?)
Quick gut check:
- Has the move already started? (late = smaller size or skip)
- Is this the same recycled idea from last week with no new catalyst?

TIDAK → document "nothing fresh today", stop screening. Do not force a name.
ADA → continue.

### Gate 2 — Bisa substitute atau add? (Portfolio fit)
Pull L0 state (`vault/data/portfolio-state.json`):

| Situation | Action |
|-----------|--------|
| Sector already at 50%+ exposure | Reduce planned size by 50%; or substitute a weaker hold instead of adding |
| Ticker already held, conviction unchanged | Skip — don't double-add without new catalyst |
| Ticker already held, price dipped into add-zone + conviction higher | Add allowed — flag in plan |
| Weaker hold exists in same sector | Flag it for reduction; this name can substitute |
| Portfolio utilization > 80% | Reduce planned size to fit within cap |

No hard block — fit the name into the portfolio with the right size.

### Gate 3 — OK untuk lanjut? (Risk state check)

| L0 state | Adjustment |
|----------|------------|
| DD < 5% | Normal size |
| DD 5–10% | Reduce planned size 25–50% |
| DD > 10% | No new entries — focus on managing existing holds only |
| Posture ≤ 1 (risk-off) | No new entries |
| Posture = 2 | Reduced size only, high-conviction names only |
| Posture ≥ 3 | Normal |

Document the adjustment — do not silently skip. If DD > 10% or posture = 1: stop here and write the reason.

---

**Advance with adjusted size.** Two paths:
- Confidence HIGH (5/5 criteria + clear entry zone) → **L4 Full Plan**
- Confidence MED (4/5 criteria, entry zone developing) → **L3 Monitoring** first

## Execution Trigger

L2 inline gate: 5/5 criteria + price in open entry window + DD < 5%. If met → invoke `skills/trader/execution.md` (`## Confidence Gate`). Otherwise → pass to L4.

## Output (Required)

1. **Shortlist**: 3–8 tickers, each with one-line reason
2. **Rejected names**: quick note on why each screened-out candidate was skipped
3. **Superlist updates**: promote strong names to Airtable `Superlist`
4. **Post to Airtable** `Insights` for any strong screening signal
5. **Daily-note append** — call `journal.append_daily_layer_section('2', summary)` with shortlist + top pick + reason

## Telegram Notify

Send `layer2` via `skills/trader/telegram-notify.md`.

Triggers: shortlist has ≥1 high-conviction name (≥4/5 criteria); or any name promoted to Superlist. Skip if empty.

## Skills To Load

- `skills/trader/technical-analysis.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/sid-tracker.md`
- `skills/trader/wyckoff-lens.md`
- `skills/trader/airtable-trading.md`
