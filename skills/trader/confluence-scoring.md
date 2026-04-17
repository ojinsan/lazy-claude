# Confluence Scoring

One score, one decision. Every L2/L3 cycle computes it for every candidate.

## Components & Weights
| Component | Range | Source |
|-----------|-------|--------|
| Narrative fit | 0..10 | L1 themes + konglo_flow |
| Technical | 0..15 | structure + RS + trend |
| Broker flow | -15..+15 | broker_profile net |
| SID | -10..+10 | sid_tracker trend |
| VP state | -10..+10 | vp_analyzer.classify |
| Orderbook | -10..+10 | tape_runner case1/6/8 |
| Imposter | -10..+10 | imposter_detector.score |
| Wyckoff phase | 0..10 | wyckoff.py classifier |
| Spring bonus | 0..15 | spring_detector.confidence |
| Konglo bonus | 0..10 | konglo_flow alignment |

Sum, clamp to 0..100.

## Buckets
- < 40 — reject. Log rejection reason.
- 40–59 — watch. Keep on monitoring list; no plan yet.
- 60–79 — plan. Promote to L4.
- 80+ — execute. Eligible for inline execution if other gates pass.

## When To Call
- L2: compute for each shortlisted ticker. Only promote `plan`+ to L4.
- L3: recompute every cycle; if score transitions up a bucket → telegram + signal row.
- L4: attach score to every tradeplan as `conviction_score`.
- L5: pre-entry, require score ≥ 60. Execute inline only if score ≥ 80.

## Anti-game
Do not inflate components to hit a threshold. Each must have its own data source firing, not narrative reasoning.

## Tools
- `confluence_score.score(ticker)` → full dict with components + bucket
- CLI: `python tools/trader/confluence_score.py BBCA`
