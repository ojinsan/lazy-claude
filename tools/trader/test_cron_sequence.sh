#!/usr/bin/env bash
# test_cron_sequence.sh — sequential integration test for all cron layers.
#
# Fires each layer in order, waits for completion, 30s buffer between.
# L3/L5 will abort at healthcheck (market-hours gate) — that's expected.
# Logs to runtime/cron/test-YYYYMMDD.log
#
# Usage: bash tools/trader/test_cron_sequence.sh [--skip-data]
#   --skip-data  skip overnight_macro / universe_scan / catalyst_calendar
set -uo pipefail

WORKSPACE="/home/lazywork/workspace"
COMMAND_DIR="$WORKSPACE/.claude/commands/trade"
PYTHON="python3"
CLAUDE="/home/lazywork/.local/bin/claude"
LOG_DIR="$WORKSPACE/runtime/cron"
MONITORING_SETTINGS="$WORKSPACE/.claude/settings.openclaude.json"
BUFFER=30  # seconds between steps

SKIP_DATA=0
for arg in "$@"; do
    [[ "$arg" == "--skip-data" ]] && SKIP_DATA=1
done

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/test-$(TZ='Asia/Jakarta' date +%Y%m%d-%H%M).log"

log() { echo "[$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

run_python() {
    local label="$1"; shift
    log ">>> $label START"
    "$PYTHON" "$@" >> "$LOG" 2>&1 \
        && log "<<< $label OK" \
        || log "<<< $label FAILED (exit $?)"
    sleep "$BUFFER"
}

run_claude() {
    local label="$1"
    local cmd_file="$2"
    local prompt="Non-interactive cron run. Read the instructions in $cmd_file and execute them. Run to completion and exit. Do not wait for user input."
    log ">>> $label START"
    cd "$WORKSPACE"
    "$CLAUDE" --dangerously-skip-permissions -p "$prompt" >> "$LOG" 2>&1 \
        && log "<<< $label OK" \
        || log "<<< $label FAILED (exit $?)"
    sleep "$BUFFER"
}

run_claude_monitoring() {
    local label="$1"
    local cmd_file="$2"
    local prompt="Non-interactive cron run. Read the instructions in $cmd_file and execute them. Run to completion and exit. Do not wait for user input."
    log ">>> $label START"
    cd "$WORKSPACE"
    if [[ -f "$MONITORING_SETTINGS" ]] && \
       "$CLAUDE" --dangerously-skip-permissions --settings "$MONITORING_SETTINGS" \
                 -p "$prompt" >> "$LOG" 2>&1; then
        log "<<< $label OK"
    else
        log "WARN $label openclaude failed — fallback"
        "$CLAUDE" --dangerously-skip-permissions -p "$prompt" >> "$LOG" 2>&1 \
            && log "<<< $label OK" \
            || log "<<< $label FAILED (exit $?)"
    fi
    sleep "$BUFFER"
}

log "=== TEST CRON SEQUENCE START ==="
log "Log: $LOG"
log "Buffer between steps: ${BUFFER}s"
log "Skip data prep: $SKIP_DATA"

# ── Step 1: Pre-market data ───────────────────────────────────────────────────
if [[ $SKIP_DATA -eq 0 ]]; then
    run_python "OVERNIGHT MACRO"    "$WORKSPACE/tools/trader/overnight_macro.py"
    run_python "UNIVERSE SCAN"      "$WORKSPACE/tools/trader/universe_scan.py"
    run_python "CATALYST CALENDAR"  "$WORKSPACE/tools/trader/catalyst_calendar.py"
else
    log "--- data prep skipped (--skip-data) ---"
fi

# ── Step 2: L0 Portfolio ──────────────────────────────────────────────────────
run_claude "L0 PORTFOLIO" "$COMMAND_DIR/portfolio.md"

# ── Step 3: L1 Insight ───────────────────────────────────────────────────────
run_claude "L1 INSIGHT" "$COMMAND_DIR/insight.md"

# ── Step 4: L2 Screening ─────────────────────────────────────────────────────
run_claude "L2 SCREENING" "$COMMAND_DIR/screening.md"

# ── Step 5: L4 Tradeplan ─────────────────────────────────────────────────────
run_claude "L4 TRADEPLAN" "$COMMAND_DIR/tradeplan.md"

# ── Step 6: L3 Monitor (expect healthcheck abort — outside market hours) ─────
run_claude_monitoring "L3 MONITOR" "$COMMAND_DIR/monitor.md"

# ── Step 7: L5 Execute (expect healthcheck abort — outside market hours) ──────
run_claude "L5 EXECUTE" "$COMMAND_DIR/execute.md"

# ── Step 8: Watchdog ─────────────────────────────────────────────────────────
run_python "WATCHDOG" "$WORKSPACE/tools/trader/runtime_cron_watchdog.py"

log "=== TEST CRON SEQUENCE COMPLETE ==="
log "Full log: $LOG"
