# Imposter Detection

## Why
Smart money hides inside retail codes (XL, YP, CC, KK, PD, SQ, NI, AZ, CP) to avoid telegraphing intent. A naive broker-flow read will call it "retail FOMO" and flash a distribution warning — but the lot sizes and timing give it away.

## Red Flags (+imposter_score)
- Retail-coded lot ≥ 50K in one trade (retail rarely moves that size in one click).
- Multiple retail-coded trades at the exact same second (automated).
- Many retail buyers + ONE retail seller dumping large size → that seller may be the real operator offloading.

## How to Use
- L3 monitoring every cycle: call `imposter_detector.score(ticker)`.
- If `imposter_score ≥ +6` during what looks like "retail accumulation" → upgrade to `accumulation_setup` candidate.
- If `imposter_score ≥ +6` during a rally → downgrade to `distribution` suspect (the seller is the operator).

## Integration
- Adds ±10 to confluence score. See `confluence-scoring.md`.

## Limit
This is a heuristic, not proof. Never override a clear distribution_setup on imposter alone — require broker_profile + SID cross-check.

## Tools
- `imposter_detector.score(ticker, window_trades)` — returns imposter_score + breakdown
- CLI: `python tools/trader/imposter_detector.py BBCA --trades 200`
