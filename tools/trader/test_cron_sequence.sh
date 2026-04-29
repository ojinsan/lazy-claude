#!/usr/bin/env bash
# test_cron_sequence.sh — sequential one-off run of all cron layers.
#
# Checkpoint: runtime/cron/test-checkpoint-YYYYMMDD.txt
#   Each completed label written on success. Re-run skips completed steps.
#   Delete checkpoint file to force full restart.
#
# Usage:
#   bash tools/trader/test_cron_sequence.sh             # full run
#   bash tools/trader/test_cron_sequence.sh --skip-data # skip data prep
#   bash tools/trader/test_cron_sequence.sh --reset     # clear checkpoint + restart
set -uo pipefail

WORKSPACE="/home/lazywork/workspace"
COMMAND_DIR="$WORKSPACE/.claude/commands/trade"
PYTHON="python3"
CLAUDE="/home/lazywork/.local/bin/claude"
LOG_DIR="$WORKSPACE/runtime/cron"
MONITORING_SETTINGS="$WORKSPACE/.claude/settings.openclaude.json"
BUFFER=30  # seconds between steps

SKIP_DATA=0
RESET=0
for arg in "$@"; do
    [[ "$arg" == "--skip-data" ]] && SKIP_DATA=1
    [[ "$arg" == "--reset" ]]     && RESET=1
done

WIB_DATE=$(TZ='Asia/Jakarta' date +%Y%m%d)
mkdir -p "$LOG_DIR"

CHECKPOINT="$LOG_DIR/test-checkpoint-${WIB_DATE}.txt"
LOG="$LOG_DIR/test-${WIB_DATE}.log"  # single log per day (append)

[[ $RESET -eq 1 ]] && rm -f "$CHECKPOINT" && echo "checkpoint cleared"

log() { echo "[$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# Returns 0 if label already completed today
is_done() { grep -qxF "$1" "$CHECKPOINT" 2>/dev/null; }

mark_done() { echo "$1" >> "$CHECKPOINT"; }

run_python() {
    local label="$1"; shift
    if is_done "$label"; then log "--- $label already done (checkpoint) ---"; return 0; fi
    log ">>> $label START"
    if "$PYTHON" "$@" >> "$LOG" 2>&1; then
        log "<<< $label OK"
        mark_done "$label"
    else
        log "<<< $label FAILED (exit $?) — check $LOG"
    fi
    sleep "$BUFFER"
}

run_claude() {
    local label="$1"
    local cmd_file="$2"
    if is_done "$label"; then log "--- $label already done (checkpoint) ---"; return 0; fi
    local prompt="Non-interactive cron run. Read the instructions in $cmd_file and execute them. Run to completion and exit. Do not wait for user input."
    log ">>> $label START"
    cd "$WORKSPACE"
    local ok=0
    if [[ -f "$MONITORING_SETTINGS" ]] && \
       "$CLAUDE" --dangerously-skip-permissions --settings "$MONITORING_SETTINGS" \
                 -p "$prompt" >> "$LOG" 2>&1; then
        ok=1
    else
        log "WARN $label openclaude failed — fallback to default"
        "$CLAUDE" --dangerously-skip-permissions -p "$prompt" >> "$LOG" 2>&1 && ok=1
    fi
    if [[ $ok -eq 1 ]]; then
        log "<<< $label OK"
        mark_done "$label"
    else
        log "<<< $label FAILED — check $LOG"
    fi
    sleep "$BUFFER"
}

log "=== TEST CRON SEQUENCE $(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M') ==="
log "Log: $LOG  |  Checkpoint: $CHECKPOINT  |  skip-data: $SKIP_DATA"

# ── Step 1: Pre-market data ───────────────────────────────────────────────────
if [[ $SKIP_DATA -eq 0 ]]; then
    run_python "OVERNIGHT MACRO"   "$WORKSPACE/tools/trader/overnight_macro.py"
    run_python "UNIVERSE SCAN"     "$WORKSPACE/tools/trader/universe_scan.py"
    run_python "CATALYST CALENDAR" "$WORKSPACE/tools/trader/catalyst_calendar.py"
else
    log "--- data prep skipped (--skip-data) ---"
fi

# ── Step 2–5: L0 → L1 → L2 → L4 ─────────────────────────────────────────────
run_claude "L0 PORTFOLIO" "$COMMAND_DIR/portfolio.md"
run_claude "L1 INSIGHT"   "$COMMAND_DIR/insight.md"
run_claude "L2 SCREENING" "$COMMAND_DIR/screening.md"
run_claude "L4 TRADEPLAN" "$COMMAND_DIR/tradeplan.md"

# ── Step 6: L3 Monitor ───────────────────────────────────────────────────────
run_claude "L3 MONITOR"   "$COMMAND_DIR/monitor.md"

# ── Step 7: L5 Execute ───────────────────────────────────────────────────────
run_claude "L5 EXECUTE"   "$COMMAND_DIR/execute.md"

# ── Step 8: Watchdog ─────────────────────────────────────────────────────────
run_python "WATCHDOG" "$WORKSPACE/tools/trader/runtime_cron_watchdog.py"

log "=== TEST CRON SEQUENCE COMPLETE ==="
