#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date '+%F %T')
PY="$HOME/workspace/tools/trader/runtime_summary_30m.py"
LOG="$HOME/workspace/runtime/monitoring/summary-30m.log"
mkdir -p "$(dirname "$LOG")"
echo "[$STAMP] layer-3-stock-overseeing / summary-30m (local compression only)-30m" >> "$LOG"
python3 "$PY" >> "$LOG" 2>&1
