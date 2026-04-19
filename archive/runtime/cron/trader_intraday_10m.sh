#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date '+%F %T')
PY="$HOME/workspace/tools/trader/runtime_monitoring.py"
LOG="$HOME/workspace/runtime/monitoring/intraday-10m.log"
mkdir -p "$(dirname "$LOG")"
echo "[$STAMP] layer-3-stock-overseeing / intraday-10m" >> "$LOG"
python3 "$PY" >> "$LOG" 2>&1
