#!/usr/bin/env bash
# cron-dispatcher.sh — single entry point for all trader cron jobs.
#
# Crontab: * * * * * /home/lazywork/workspace/tools/trader/cron-dispatcher.sh
#
# Schedule (WIB, Mon–Fri, non-holiday):
#   03:00  overnight_macro.py
#   04:00  universe_scan.py + catalyst_calendar.py
#   04:30  L0 /trade:portfolio
#   05:00  L1 /trade:insight
#   05:30  L2 /trade:screening
#   06:00  L4 /trade:tradeplan (Mode A batch)
#   08:30  L5 /trade:execute  (pre-open sweep)
#   09:05  watchdog (missed-window check)
#   09:00–15:30, min%10==0  L3 /trade:monitor (every 10m)
#   09:00–15:00, min%30==0  L5 /trade:execute (reconcile, every 30m, after monitor)
#   15:20  /trade:eod
#   Sun 20:00  journal weekly
#   Month-end 20:00  journal monthly
#
# Guarantee: at most one Claude subprocess per tick (monitor fires first; reconcile follows).
set -euo pipefail

WORKSPACE="/home/lazywork/workspace"
MONITORING_SETTINGS="$WORKSPACE/.claude/settings.openclaude.json"
COMMAND_DIR="$WORKSPACE/.claude/commands/trade"
PYTHON="python3"
CLAUDE="/home/lazywork/.local/bin/claude"
LOG_DIR="$WORKSPACE/runtime/cron"
HOLIDAY_FILE="$WORKSPACE/vault/data/idx_holidays.json"

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(TZ='Asia/Jakarta' date +%Y%m%d).log"

WIB_DATE=$(TZ='Asia/Jakarta' date +%Y-%m-%d)
WIB_HOUR=$(TZ='Asia/Jakarta' date +%-H)
WIB_MIN=$(TZ='Asia/Jakarta' date +%-M)
WIB_DOW=$(TZ='Asia/Jakarta' date +%u)   # 1=Mon … 7=Sun
WIB_YEAR=$(TZ='Asia/Jakarta' date +%Y)

log() { echo "[$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M')] $*" >> "$LOG"; }

# ── Holiday gate ─────────────────────────────────────────────────────────────
is_holiday() {
    if [[ ! -f "$HOLIDAY_FILE" ]]; then
        log "WARN holiday file missing ($HOLIDAY_FILE) — treating as trading day"
        return 1  # fail-open
    fi
    # Use python3 to parse JSON; avoid jq dependency
    "$PYTHON" - <<EOF
import json, sys
with open("$HOLIDAY_FILE") as f:
    data = json.load(f)
holidays = data.get("$WIB_YEAR", [])
sys.exit(0 if "$WIB_DATE" in holidays else 1)
EOF
}

is_trading_day() {
    [[ $WIB_DOW -le 5 ]] && ! is_holiday
}

# ── Job runners ───────────────────────────────────────────────────────────────

# One-shot daily jobs (L0, L4, L5 pre-open, EOD)
run_claude_job() {
    local label="$1"
    local command_file="$2"
    local prompt="Non-interactive cron run. Read the instructions in $command_file and execute them. Run to completion and exit. Do not wait for user input."
    log "→ $label start"
    cd "$WORKSPACE"
    "$CLAUDE" --dangerously-skip-permissions --bare -p "$prompt" >> "$LOG" 2>&1 \
        && log "← $label done" \
        || log "← $label FAILED (exit $?)"
}

# Monitoring / reconcile: try openclaude settings first, fall back to default
run_monitoring_job() {
    local label="$1"
    local command_file="$2"
    local prompt="Non-interactive cron run. Read the instructions in $command_file and execute them. Run to completion and exit. Do not wait for user input."
    log "→ $label start"
    cd "$WORKSPACE"
    if [[ -f "$MONITORING_SETTINGS" ]] && \
       "$CLAUDE" --dangerously-skip-permissions --bare --settings "$MONITORING_SETTINGS" \
                 -p "$prompt" >> "$LOG" 2>&1; then
        log "← $label done"
        return 0
    fi
    log "WARN $label --settings run failed — falling back to default Claude"
    "$CLAUDE" --dangerously-skip-permissions --bare -p "$prompt" >> "$LOG" 2>&1 \
        && log "← $label done" \
        || log "← $label FAILED (exit $?)"
}

run_python_job() {
    local label="$1"
    local script="$2"
    shift 2
    log "→ $label start"
    "$PYTHON" "$script" "$@" >> "$LOG" 2>&1 \
        && log "← $label done" \
        || log "WARN $label failed (exit $?)"
}

# ── Tick ─────────────────────────────────────────────────────────────────────
log "tick — WIB ${WIB_HOUR}:$(printf '%02d' "$WIB_MIN") dow=$WIB_DOW"

# ── Off-hours / weekend / holiday (non-market jobs still run) ────────────────

# ── 03:00 — overnight macro (any day) ────────────────────────────────────────
if [[ $WIB_HOUR -eq 3 && $WIB_MIN -eq 0 ]]; then
    run_python_job "OVERNIGHT MACRO" "$WORKSPACE/tools/trader/overnight_macro.py"

# ── 04:00 — pre-market data (trading days only) ───────────────────────────────
elif [[ $WIB_HOUR -eq 4 && $WIB_MIN -eq 0 ]] && is_trading_day; then
    run_python_job "UNIVERSE SCAN" "$WORKSPACE/tools/trader/universe_scan.py"
    run_python_job "CATALYST CALENDAR" "$WORKSPACE/tools/trader/catalyst_calendar.py"

# ── 04:30 — L0 Portfolio (trading days) ──────────────────────────────────────
elif [[ $WIB_HOUR -eq 4 && $WIB_MIN -eq 30 ]] && is_trading_day; then
    run_claude_job "L0 PORTFOLIO" "$COMMAND_DIR/portfolio.md"

# ── 05:00 — L1 Insight (trading days) ────────────────────────────────────────
elif [[ $WIB_HOUR -eq 5 && $WIB_MIN -eq 0 ]] && is_trading_day; then
    run_claude_job "L1 INSIGHT" "$COMMAND_DIR/insight.md"

# ── 05:30 — L2 Screening (trading days) ──────────────────────────────────────
elif [[ $WIB_HOUR -eq 5 && $WIB_MIN -eq 30 ]] && is_trading_day; then
    run_claude_job "L2 SCREENING" "$COMMAND_DIR/screening.md"

# ── 06:00 — L4 Tradeplan Mode A batch (trading days) ─────────────────────────
elif [[ $WIB_HOUR -eq 6 && $WIB_MIN -eq 0 ]] && is_trading_day; then
    run_claude_job "L4 TRADEPLAN" "$COMMAND_DIR/tradeplan.md"

# ── 08:30 — L5 pre-open sweep (trading days) ─────────────────────────────────
elif [[ $WIB_HOUR -eq 8 && $WIB_MIN -eq 30 ]] && is_trading_day; then
    run_claude_job "L5 EXECUTE pre-open" "$COMMAND_DIR/execute.md"

# ── 09:05 — watchdog (trading days) ──────────────────────────────────────────
elif [[ $WIB_HOUR -eq 9 && $WIB_MIN -eq 5 ]] && is_trading_day; then
    run_python_job "WATCHDOG" "$WORKSPACE/tools/trader/runtime_cron_watchdog.py"

# ── 09:00–15:30, every 10m — L3 monitor (trading days) ───────────────────────
# ── 09:00–15:00, every 30m — L5 reconcile after monitor (trading days) ───────
elif [[ $WIB_HOUR -ge 9 ]] && \
     [[ $WIB_HOUR -lt 15 || ($WIB_HOUR -eq 15 && $WIB_MIN -le 30) ]] && \
     [[ $((WIB_MIN % 10)) -eq 0 ]] && \
     is_trading_day; then

    # L3 monitor fires every 10m 09:00–15:30
    run_monitoring_job "L3 MONITOR" "$COMMAND_DIR/monitor.md"

    # L5 reconcile fires every 30m 09:00–15:00, after monitor
    if [[ $((WIB_MIN % 30)) -eq 0 ]] && \
       [[ $WIB_HOUR -lt 15 || ($WIB_HOUR -eq 15 && $WIB_MIN -eq 0) ]]; then
        run_monitoring_job "L5 EXECUTE reconcile" "$COMMAND_DIR/execute.md"
    fi

# ── 15:20 — EOD publish (trading days) ───────────────────────────────────────
elif [[ $WIB_HOUR -eq 15 && $WIB_MIN -eq 20 ]] && is_trading_day; then
    run_claude_job "EOD PUBLISH" "$COMMAND_DIR/eod.md"

# ── Sun 20:00 — weekly journal (any week) ────────────────────────────────────
elif [[ $WIB_DOW -eq 7 && $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 ]]; then
    run_python_job "WEEKLY REVIEW" "$WORKSPACE/tools/trader/journal.py" weekly

# ── Month-end 20:00 — monthly journal ────────────────────────────────────────
elif [[ $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 ]] && \
     [[ $(TZ='Asia/Jakarta' date -d '+1 day' +%d) == "01" ]]; then
    run_python_job "MONTHLY REVIEW" "$WORKSPACE/tools/trader/journal.py" monthly

# ── Off-hours ─────────────────────────────────────────────────────────────────
else
    log "off-hours — skip"
fi
