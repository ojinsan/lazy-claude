# Auto-Trigger

## Purpose
High-conviction tape signals are time-sensitive. Let the monitoring cron auto-invoke Claude when the signal beats every gate — without letting costs run away.

## Gates (all must pass)
- `confluence_score.bucket == "execute"` (score ≥ 80)
- `tape_runner.snapshot(...).composite in {"ideal_markup","spring_ready","healthy_markup"}` with `confidence == "high"`
- Portfolio: DD < 5%, posture ≥ 2, kill switch inactive
- Dedup: no trigger fired for this `{ticker, signal_kind}` in the last 60 minutes
- Budget: fewer than 5 auto-triggers fired today

Any gate fails → telegram only (`auto_trigger_detected` with context), NO Claude invocation.

## Prompt Contract
The auto-trigger prompt always asks Claude to:
1. Re-read today's L1 posture + L0 state.
2. Verify the tape + confluence evidence at the invocation time.
3. Decide: proceed to L4+L5, or abort. State the reason.
4. Telegram-first before any order.

## Logging
Every trigger writes to `vault/data/auto_trigger_log.jsonl`:
```json
{"ts":"...","ticker":"...","kind":"spring|ideal_markup|healthy_markup","confluence":85,"outcome":"fired|deduped|budget|gate_failed"}
```

## Tuning
- Confluence threshold (80) and budget (5) live in `tools/trader/auto_trigger.py`. Adjust only via commit — no env flag.
- Increase budget only after reviewing the log shows all prior triggers were worthwhile.

## Anti-pattern
- Never call `auto_trigger.trigger` from anywhere except the monitoring runtime. No inline scripts, no REPL shortcuts.
- Never skip the telegram step, even when firing Claude.

## Tools
- `auto_trigger.should_trigger(ticker, signal_kind)` → `(bool, reason)`
- `auto_trigger.trigger(ticker, signal_kind, context)` → log entry
- CLI: `python tools/trader/auto_trigger.py BBCA ideal_markup --dry-run`
