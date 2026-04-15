#!/usr/bin/env bash
# cron-dispatcher.sh — runs trader command files on a WIB schedule.
# Claude uses the openclaude context/settings while writing outputs into workspace.
set -euo pipefail

WORKSPACE="/home/lazywork/workspace"
CLAUDE_CONTEXT="/home/lazywork/openclaude"
CLAUDE_SETTINGS="$CLAUDE_CONTEXT/.claude/settings.local.json"
COMMAND_DIR="$WORKSPACE/.claude/commands/trade"
CLAUDE="/home/lazywork/.local/bin/claude"
LOG_DIR="$WORKSPACE/runtime/cron"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/$(TZ='Asia/Jakarta' date +%Y%m%d).log"

WIB_HOUR=$(TZ='Asia/Jakarta' date +%-H)
WIB_MIN=$(TZ='Asia/Jakarta' date +%-M)

log() { echo "[$(TZ='Asia/Jakarta' date '+%Y-%m-%d %H:%M')] $*" >> "$LOG"; }

run_claude_job() {
    local command_file="$1"
    local prompt="Non-interactive cron run. Use /home/lazywork/openclaude as the Claude context root and settings source. Use /home/lazywork/workspace for all reads, writes, and outputs. Read the instructions in $command_file and execute them. Run to completion and exit. Do not wait for user input."

    cd "$WORKSPACE"
    "$CLAUDE" \
        --dangerously-skip-permissions \
        --bare \
        --setting-sources user \
        --add-dir "$CLAUDE_CONTEXT" \
        --settings "$CLAUDE_SETTINGS" \
        -p "$prompt" \
        >> "$LOG" 2>&1
}

log "tick — WIB ${WIB_HOUR}:$(printf '%02d' "$WIB_MIN")"

# ── Screening window: 05:00, 05:30 WIB ─────────────────────────────────────
if [[ $WIB_HOUR -eq 5 ]]; then
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
    run_claude_job "$COMMAND_DIR/monitoring.md"
    log "← MONITORING done"

    log "→ EXECUTE (intraday signals) start"
    run_claude_job "$COMMAND_DIR/execute.md"
    log "← EXECUTE done"

# ── Off-hours ───────────────────────────────────────────────────────────────
else
    log "off-hours — skip"
fi
