# Spec #8 — Orchestration / CRON (end-to-end wiring)

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Prereqs:** all layer specs (#2–#7). This spec wires them into the daily rhythm.

## 1. Scope

Single entry point for the day: `tools/trader/cron-dispatcher.sh`, invoked once per minute by system crontab. Decides what (if anything) to run based on WIB wall-clock. Every layer call goes through the dispatcher — no per-layer crontab entries.

- **Creates/replaces:** `tools/trader/cron-dispatcher.sh` (rewrite), `crontab` wiring, `runtime/cron/YYYYMMDD.log`.
- **Does NOT own:** layer logic (each spec owns its own), data gathering, AI judgment.

## 2. Daily rhythm (WIB, Mon–Fri unless noted)

```
03:00  overnight_macro.py                     → vault/data/overnight-*.json
04:00  universe_scan.py + catalyst_calendar   → pre-market data freshness
04:30  /trade:portfolio     (L0, spec #2)     → holdings + redflags + aggressiveness
05:00  /trade:insight       (L1, spec #3)     → watchlist + regime + narratives
05:30  /trade:screening     (L2, spec #4)     → superlist + exitlist (overnight judge)
06:00  /trade:tradeplan     (L4 Mode A batch) → plan for superlist/exitlist buy/sell_at_price
08:30  /trade:execute       (L5 pre-open)     → place entry orders at limit
09:00→15:30 every 10m /trade:monitor (L3, spec #5) → BUY-NOW/thesis-break/notch + Mode B L4→L5 Popen chain
09:00, 09:30 … 15:00 every 30m /trade:execute (L5 reconcile) → fills/stops/TPs
11:30, 14:00 /trade:monitor (regime/midday re-check — legacy, kept)
15:20  /trade:eod                              → publish + daily-note seal + journal
Sun 20:00  journal.py weekly
Last-day-of-month 20:00  journal.py monthly
```

Weekend/holiday gate: dispatcher checks `TZ='Asia/Jakarta' date +%u` + IDX holiday file (`vault/data/idx_holidays.json`); off-day skips market-hours jobs but still runs journal + macro.

## 3. Dispatcher contract

`cron-dispatcher.sh`:
1. Read WIB hour+minute, weekday, holiday table.
2. Match window → call `run_claude_job <cmd>` or `run_python_job <script>`.
3. Log start + exit code to `runtime/cron/YYYYMMDD.log`.
4. Never fan-out: at most one Claude subprocess per tick (avoids session collisions on `current_trade.json`).
5. Monitoring + execute-reconcile share the 09:00–15:00 window → dispatcher serializes: monitor first, then execute.

## 4. Crontab wiring

`crontab -e` (user `lazywork`):
```
* * * * * /home/lazywork/workspace/tools/trader/cron-dispatcher.sh
```

Single line. Idempotent — re-runs mid-minute (rare) are safe because every layer has its own idempotency guard (L3 `buy_now_ledger`, L5 `execution ≠ None`, etc.).

## 5. Failure handling

- **Soft fail per job:** each `run_*_job` returns non-zero → logged, dispatcher continues. Next window still fires.
- **Hard gate via healthcheck:** each layer owns a `*_healthcheck.py` that aborts + telegram-warns (aggressiveness=off, stale inputs, etc.). Dispatcher does not re-check.
- **Watchdog:** `runtime_cron_watchdog.py` (new, small) — scans today's log for missing expected windows (e.g. L0 never ran) → telegram warn once. Runs at 09:05 WIB via dispatcher.
- **Cleanup:** `runtime/cron/*.log` older than 30d pruned by `runtime_cron_watchdog.py`.

## 6. Files

**Create:**
- `tools/trader/runtime_cron_watchdog.py` — daily log scan + missed-window alert + log pruning.
- `vault/data/idx_holidays.json` — seed `{"2026": ["2026-01-01", "2026-04-10", ...]}`. Maintained by hand; fetched yearly from IDX.
- `playbooks/trader/ops-runbook.md` — how to pause CRON (comment crontab line), rotate broker token, force-rerun a layer, read logs, Telegram kill-switch sequence.

**Modify:**
- `tools/trader/cron-dispatcher.sh` — holiday gate + L5 reconcile every-30m branch + watchdog slot + single-subprocess guarantee.
- `.claude/commands/trade/eod.md` — align with spec #2/#3/#4/#5/#6/#7 daily-note blocks (one seal, all layers).

## 7. Healthcheck + kill-switch

- Global kill-switch: `trader_status.aggressiveness == "off"` in `current_trade.json` → L2/L3/L4/L5 all abort at their own healthcheck. Dispatcher does not gate — layers do.
- Per-layer healthcheck owns its own reason (market-hours, empty universe, stale plan, …) per spec.
- Telegram `[CRON skip]` only from watchdog, not per-tick — dispatcher log is source of truth for "did it run."

## 8. Task breakdown (5 tasks)

1. **Dispatcher rewrite** — full WIB window table, L5 reconcile 30m branch, single-subprocess guarantee, holiday JSON gate. Keep backwards-compat with old windows during transition.
2. **Holiday seed** — `vault/data/idx_holidays.json` + loader helper in dispatcher (pure bash `jq` or python one-liner).
3. **Watchdog** — `runtime_cron_watchdog.py` with missed-window detector (reads `runtime/cron/YYYYMMDD.log`, compares vs expected schedule, telegram warn) + 30d log prune.
4. **Ops runbook** — `playbooks/trader/ops-runbook.md` covering pause/resume, token rotate, forced rerun, how to read the log, emergency stop.
5. **Progress doc + INDEX + tag** — `spec-8-plan-complete`.

Deferred: 6. E2E dry-run full day (03:00→15:30 simulated via timestamp injection). 7. Accept + tag.

## 9. Guardrails

- No per-layer crontab entries — dispatcher is sole entry.
- No concurrent Claude subprocesses (single-subprocess guarantee).
- Logs rotate daily, pruned at 30d.
- Holiday file required — missing file → treat as trading day (fail-open, warn telegram once).
- Watchdog fires at most one alert per missed window per day (state file `runtime/cron/watchdog-state.json`).

## 10. Out of scope

- systemd timers (crontab sufficient for single host).
- Multi-host failover (single-host system).
- Secrets rotation automation (manual per ops-runbook).
- Metrics export / Prometheus (log-grep sufficient).
