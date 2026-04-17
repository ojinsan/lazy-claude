# Tape Reading — Order Book + Trade Book + Running Trade

**Use during L3 monitoring cycles.** Time-sensitive. For any ticker in `Superlist` status `Hold` or on today's shortlist, snapshot once per cycle via `tape_runner.snapshot(ticker)`.

## Glossary
- **HAKA** — Hajar Kanan; buyer hits the offer (offer eaten).
- **HAKI** — Hajar Kiri; seller hits the bid (bid eaten).
- **Freq** — number of distinct accounts queued at a price. Low = bandar-like; high = retail-like.
- **Lot** — queue size. Big lot + low freq = bandar. Small lot + high freq = retail.

## 9 Cases (Quick Reference)

| # | Pattern | Signal | Action |
|---|---------|--------|--------|
| 1 | Thick bid/offer at 1–2 prices | S/R defined | Entry near support, TP near resistance |
| 2 | Thick bid eaten (not pulled) on downtrend | Fake support | EXIT / avoid |
| 3 | Thick offer eaten (not pulled) on uptrend | Bullish absorption | Consider entry |
| 4 | Big lot + low freq at one level | Bandar queue | Wait — can be pulled |
| 5 | Repeated "thick" lots all ≤3 freq each | Ganjelan / fake queue | Distribution warning |
| 6 | Offer eaten → bid thickens next tick, repeat | Healthy markup | Positive bias, add permitted |
| 7 | Same-price crossing 100K+ lot in seconds | Cross-trade flag | Investigate broker code |
| 8 | Every offer eaten → bid rebuilt next tick up the ladder | Ideal markup | Strongest buy tape |
| 9 | Frequent HAKA 1-lot spam then HAKI big | Running-trade manipulation | EXIT fast |

## Case Detail

### Case 1 — Walls as S/R
Thick bid at one price = bandar defending support; thick offer = bandar capping. Useful for scalping entries and tighter stops. Validate with `case2_eaten_vs_pulled.classify_wall_fate` next cycle.

### Case 2 — Bid Thick But Eaten (Fake Support)
If a thick bid gets eaten in heavy HAKI, it was a tool for the operator to unload. Trade-book `buy_lot` at that price rises sharply confirms eaten (vs. pulled). Distribution read — exit any existing long.

### Case 3 — Offer Thick But Eaten (Bullish)
Opposite. Offer continually eaten, replaced with bid thickening below. Operator is willing to pay through a fake cap to scare retail out. Entry allowed.

### Case 4 — Freq/Lot Mismatch
Lot=242K at 5 freq is three traders with big books. Entry tactic: add-on near the wall if it has held one cycle. Stop: one tick below the wall (they can cancel, and when they do, price drops hard).

### Case 5 — Ganjelan
Multiple price levels each show a "thick" queue but each has ≤3 freq. That is one or two accounts faking depth. Cancel risk is high — expect a sharp drop once the show ends.

### Case 6 — Healthy Markup
Offer eaten → bid thickens at the next tick → offer above eaten → pattern repeats. Trade-book buy_lot grows at each level. Strong accumulation; good for adding.

### Case 7 — Crossing
Big same-price transaction between two counterparties repeatedly. Common Prajogo/Barito crossings (DP↔NI). Not tradeable — investigate broker codes via `case7_crossing.detect_crossing` and pause judgement until the source is known.

### Case 8 — Ideal Markup
Stepwise: each offer fully eaten, bid immediately restacked at the same or higher level. Continues up the ladder. Enter on pullback to the last restacked bid. Stop: one tick under the last restack that held.

### Case 9 — Spam Lot
Running trade floods with 1-lot HAKA to create FOMO; seconds later a large HAKI prints. Price falls; retail sells into the hole. Treat any spam pattern as immediate exit signal for tight-stop positions.

## Integration
- L3 every cycle: `tape_runner.snapshot(ticker)` for each hold + shortlist. Log `composite` + `confidence` to monitoring trail. Push `signal` row when composite changes vs previous cycle.
- Confluence: composite maps to +/- points (see `confluence-scoring.md`).
- Auto-trigger: `ideal_markup` or `spring_ready` with `confidence="high"` eligible — see `auto-trigger.md`.
- Exit: `fake_support` or `distribution_trap` with `confidence="high"` on a hold → immediate `exit-candidate` flag in `vault/data/thesis-actions.json` and `layer3` telegram.

## Anti-patterns
- Do NOT act on one cycle alone for ambiguous composites (`neutral`, `crossing_flag`). Wait for confirmation.
- Do NOT chase into `spam_warning` even if price is moving up.
- Do NOT interpret crossing as bullish or bearish without broker-code resolution.

## Tools
- `tape_runner.snapshot(ticker)` → full TapeState
- Individual case modules in `tools/trader/tape/` — each has standalone CLI
- CLI: `python tools/trader/tape_runner.py BBCA`
