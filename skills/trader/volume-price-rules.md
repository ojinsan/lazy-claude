# Volume-Price Rules (Wyckoff)

Every decision must check the 4-quadrant table before acting on price alone.

| Price | Volume | State | Bias | Action |
|-------|--------|-------|------|--------|
| UP | UP | healthy_up | BULLISH | Allow entry / hold |
| DOWN | DOWN | healthy_correction | BULLISH | Add-to-support permitted |
| UP | DOWN | weak_rally | CAUTION | No chase; reduce plan size |
| DOWN | UP | distribution | BEARISH | Cut on confirmation |

## Thresholds
- Baseline `vol_ratio` = 20-day average.
- `healthy_up` only counts if 2 of last 3 sessions were ≥ 1.0. A single spike ≠ trend.
- `distribution` is only actionable if paired with smart-money net selling (cross-check via `broker_profile.py`). Without the broker read, mark `watch` not `cut`.

## Integration
- L2 screening: drop any name whose 5-day composite is `weak_rally` or `distribution` unless spring or shakeout is simultaneously firing.
- L3 monitoring: run `vp_analyzer.classify` each 30-min cycle on 30m timeframe, append to signal trail.
- L4 sizing: `weak_rally` state caps risk_pct at 1% regardless of conviction.

## Anti-patterns
- Do NOT declare `healthy_up` on a gap-up day with thin vol_ratio. Gaps inflate the return but not the volume confirmation.
- Do NOT treat `distribution` as short signal — Indonesian market is long-only. Use it as exit/avoid.

## Tools
- `vp_analyzer.classify(ticker, timeframe)` — single candle state
- `vp_analyzer.classify_series(ticker, days)` — trend continuity check
- CLI: `python tools/trader/vp_analyzer.py BBCA` or `--series 10`
