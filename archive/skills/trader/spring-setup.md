# Spring Setup (Wyckoff Phase C)

Engineered break below a published support where smart money absorbs retail panic. A spring is not "price fell then bounced" — it is "price was *made to fall* so weak hands would sell, and a known buyer was waiting."

## Detection (see `spring_detector.detect`)
1. Price breaks support by ≥2%.
2. Bid stack quality remains — thick near-bid or bid/offer ≥1.5.
3. Smart money net bidding in recent trades (broker_profile).
4. Volume ≥1.5× average in breach window.

## Entry
- Entry zone: support ±1 tick on first successful reclaim of support level.
- Stop: low of spring bar - 1 tick (or -2% if bar is narrow).
- Risk bucket: `med` conviction by default; `high` only if all 4 + vol_spike and the group has konglo alignment.

## Target
- T1 = pre-spring swing high (typical 1.5R–2R).
- T2 = next Wyckoff phase D breakout level (3R+).

## Failure Mode
If price closes below spring low with smart money flipping to net-sell → thesis invalid. Do not average down.

## Integration
- L2: spring firing adds +15 confluence; overrides a `weak_rally` VP state veto.
- L3: spring event triggers a `signal` of kind `spring` with severity based on confidence.
- L4: Mode B (sizing-only) is the default path for `high` confidence springs — tape already defines entry.
  - If arrived via `spring` signal → use spring entry rule from this skill (`## Entry`).
- L5: auto-trigger eligible (see `auto-trigger.md`).

## Example (from shared playbook)
> DEF support 5000. XYZ + ABC offer thin at 5000-5100, RF accumulates at 5000 with heavy volume, ABC breaks 4900 on weak vol, RF keeps bidding at 4900-5000 with volume. By afternoon price tembus 5000. Read: "Bos mulai beli di 5000."

## Tools
- `spring_detector.detect(ticker)` — full spring check
- CLI: `python tools/trader/spring_detector.py BBCA`
