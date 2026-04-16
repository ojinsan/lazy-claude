# Layer 2 — Stock Screening

Filter the full universe down to a high-conviction shortlist.

## Input

- Layer 1 market regime, sector view, and narrative list
- Current watchlist from Airtable `Superlist`

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
3. **Volume / liquidity** — adequate volume, no illiquid traps
4. **Broker / whale signal** — accumulation pattern in broker flow or SID
5. **Orderbook quality** — is there real bid support, or just noise?

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

Three gates must pass before advancing. Each gate is a real question, not a formality. If any gate fails → document why, loop back to screening, do not force advancement.

### Gate 1 — Ada yang menarik? (Is anything genuinely compelling?)
Not "technically fine" — actually compelling. Ask:
- Is the setup early enough to have edge, or has the move already started?
- Is the narrative fresh, or is this a recycled idea from last week?
- Would you explain this trade confidently to another fund manager?

TIDAK → stop. Document: "Nothing compelling today — [reason]." Loop back.

### Gate 2 — Bisa substitute atau add? (Portfolio fit check)
Pull current L0 state (`vault/data/portfolio-state.json`):
- Is the sector already at or above max exposure? → Block new entry in same sector
- Is the ticker already held? → Is there room to add (conviction risen, price dipped into add-zone)?
- Is there a weaker hold that this new name clearly substitutes? → Flag the weaker hold for reduction

TIDAK → loop back, find a name with portfolio room, or note no room today.

### Gate 3 — OK untuk lanjut? (Final go/no-go)
- L0 DD < 5% from HWM? (if not → reduce planned size or skip)
- L1 aggression posture ≥ 2?
- Portfolio has unused capacity (utilization < 80%)?

TIDAK → loop back or stop entirely if conditions don't support new entries.

---

**If all 3 gates pass → advance.** Two paths:
- Confidence HIGH (all 5/5 criteria + clear entry zone) → go to **L4 Full Plan**
- Confidence MED (4/5 criteria, entry zone developing) → go to **L3 Monitoring** first

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
