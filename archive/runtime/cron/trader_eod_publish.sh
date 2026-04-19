#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date '+%F %T')
PY="$HOME/workspace/tools/trader/runtime_eod_publish.py"
LOG="$HOME/workspace/runtime/monitoring/eod-publish.log"
mkdir -p "$(dirname "$LOG")"
echo "[$STAMP] layer-4-trade-plan / eod-publish" >> "$LOG"
python3 "$PY" >> "$LOG" 2>&1
