#!/usr/bin/env bash
# cron-dispatcher.sh — runs trader command files on a WIB schedule.
# Monitoring window: tries --settings openclaude.json first, falls back to default Claude.
# All other windows: default Claude only (no --settings).
set -euo pipefail

WORKSPACE="/home/lazywork/workspace"
MONITORING_SETTINGS="$WORKSPACE/.claude/settings.openclaude.json"
COMMAND_DIR="$WORKSPACE/.claude/commands/trade"
CLAUDE="/home/lazywork/.local/bin/claude"
LOG_DIR="$WORKSPACE/runtime/cron"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(TZ='Asia/Jakarta' date +%Y%m%d).log"

WIB_HOUR=$(TZ='Asia/Jakarta' date +%-H)
WIB_MIN=$(TZ='Asia/Jakarta' date +%-M)

log() { echo "[$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M')] $*" >> "$LOG"; }

# Default: no special settings (one-shot daily jobs — L0, screening, tradeplan, 08:30 execute)
run_claude_job() {
    local command_file="$1"
    local prompt="Non-interactive cron run. Read the instructions in $command_file and execute them. Run to completion and exit. Do not wait for user input."
    cd "$WORKSPACE"
    "$CLAUDE" --dangerously-skip-permissions --bare -p "$prompt" >> "$LOG" 2>&1
}

# Monitoring: try --settings first; if it fails, fall back to default Claude
run_monitoring_job() {
    local command_file="$1"
    local prompt="Non-interactive cron run. Read the instructions in $command_file and execute them. Run to completion and exit. Do not wait for user input."
    cd "$WORKSPACE"
    if "$CLAUDE" --dangerously-skip-permissions --bare --settings "$MONITORING_SETTINGS" -p "$prompt" >> "$LOG" 2>&1; then
        return 0
    fi
    log "⚠ --settings run failed — falling back to default Claude"
    "$CLAUDE" --dangerously-skip-permissions --bare -p "$prompt" >> "$LOG" 2>&1
}

log "tick — WIB ${WIB_HOUR}:$(printf '%02d' "$WIB_MIN")"

# ── Pre-market data fetch: 04:00 WIB ────────────────────────────────────────
if [[ $WIB_HOUR -eq 4 && $WIB_MIN -eq 0 ]]; then
    log "→ PRE-MARKET DATA start"
    python "$WORKSPACE/tools/trader/universe_scan.py" >> "$LOG" 2>&1 || log "⚠ universe_scan failed"
    python "$WORKSPACE/tools/trader/catalyst_calendar.py" >> "$LOG" 2>&1 || log "⚠ catalyst_calendar failed"
    log "← PRE-MARKET DATA done"

# ── Portfolio window: 04:30 WIB ─────────────────────────────────────────────
elif [[ $WIB_HOUR -eq 4 && $WIB_MIN -eq 30 ]]; then
    log "→ PORTFOLIO (L0) start"
    run_claude_job "$COMMAND_DIR/portfolio.md"
    log "← PORTFOLIO done"

# ── Screening window: 05:00, 05:30 WIB ─────────────────────────────────────
elif [[ $WIB_HOUR -eq 5 ]]; then
    log "→ SCREENING (L1+L2) start"
    run_claude_job "$COMMAND_DIR/screening.md"
    log "← SCREENING done"

# ── Trade plan window: 06:00 WIB ────────────────────────────────────────────
elif [[ $WIB_HOUR -eq 6 && $WIB_MIN -eq 0 ]]; then
    log "→ TRADEPLAN (L4 pre-market) start"
    run_claude_job "$COMMAND_DIR/tradeplan.md"
    log "← TRADEPLAN done"

# ── Execute window: 08:30 WIB ────────────────────────────────────────────────
elif [[ $WIB_HOUR -eq 8 && $WIB_MIN -eq 30 ]]; then
    log "→ EXECUTE (portfolio check + orders) start"
    run_claude_job "$COMMAND_DIR/execute.md"
    log "← EXECUTE done"

# ── Monitoring window: 09:00–15:00 WIB (inclusive) ─────────────────────────
elif [[ $WIB_HOUR -ge 9 ]] && [[ $WIB_HOUR -lt 15 || ($WIB_HOUR -eq 15 && $WIB_MIN -eq 0) ]]; then
    log "→ MONITORING (L3+L4) start"
    run_monitoring_job "$COMMAND_DIR/monitoring.md"
    log "← MONITORING done"

    log "→ EXECUTE (intraday signals) start"
    run_monitoring_job "$COMMAND_DIR/execute.md"
    log "← EXECUTE done"

# ── EOD publish: 15:20 WIB ──────────────────────────────────────────────────
elif [[ $WIB_HOUR -eq 15 && $WIB_MIN -eq 20 ]]; then
    log "→ EOD PUBLISH start"
    run_claude_job "$COMMAND_DIR/eod.md"
    log "← EOD PUBLISH done"

# ── Weekly review: Sunday 20:00 WIB ─────────────────────────────────────────
elif [[ $(TZ='Asia/Jakarta' date +%u) -eq 7 && $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 ]]; then
    log "→ WEEKLY REVIEW start"
    python "$WORKSPACE/tools/trader/journal.py" weekly >> "$LOG" 2>&1 || log "⚠ weekly review failed"
    log "← WEEKLY REVIEW done"

# ── Monthly review: last calendar day of month 20:00 WIB ────────────────────
elif [[ $WIB_HOUR -eq 20 && $WIB_MIN -eq 0 ]] && [[ $(TZ='Asia/Jakarta' date -d '+1 day' +%d) == "01" ]]; then
    log "→ MONTHLY REVIEW start"
    python "$WORKSPACE/tools/trader/journal.py" monthly >> "$LOG" 2>&1 || log "⚠ monthly review failed"
    log "← MONTHLY REVIEW done"

# ── Overnight macro: 03:00 WIB ───────────────────────────────────────────────
elif [[ $WIB_HOUR -eq 3 && $WIB_MIN -eq 0 ]]; then
    log "→ OVERNIGHT MACRO start"
    python "$WORKSPACE/tools/trader/overnight_macro.py" >> "$LOG" 2>&1 || log "⚠ overnight_macro failed"
    log "← OVERNIGHT MACRO done"

# ── Mid-day regime check: 11:30 WIB ──────────────────────────────────────────
elif [[ $WIB_HOUR -eq 11 && $WIB_MIN -eq 30 ]]; then
    log "→ MIDDAY REGIME (11:30) start"
    run_monitoring_job "$COMMAND_DIR/monitoring.md"
    log "← MIDDAY REGIME done"

# ── Mid-day regime check: 14:00 WIB ──────────────────────────────────────────
elif [[ $WIB_HOUR -eq 14 && $WIB_MIN -eq 0 ]]; then
    log "→ MIDDAY REGIME (14:00) start"
    run_monitoring_job "$COMMAND_DIR/monitoring.md"
    log "← MIDDAY REGIME done"

# ── Off-hours ───────────────────────────────────────────────────────────────
else
    log "off-hours — skip"
fi
