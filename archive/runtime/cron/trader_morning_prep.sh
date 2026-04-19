#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$HOME/workspace"
OUT="$WORKSPACE/runtime/monitoring/morning-prep.log"
STATE="$WORKSPACE/memory/summary-30m-state.json"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LAYER1_SCRIPT="$WORKSPACE/tools/trader/runtime_layer1_context.py"
LAYER2_SCRIPT="$WORKSPACE/tools/trader/runtime_layer2_screening.py"

mkdir -p "$(dirname "$OUT")" "$(dirname "$STATE")"
STAMP=$(date '+%F %T')
TODAY=$(date '+%F')

log() {
  echo "[$(date '+%F %T')] $*" >> "$OUT"
}

ensure_state_file() {
  if [ ! -f "$STATE" ]; then
    cat > "$STATE" <<'JSON'
{
  "lastRuns": {}
}
JSON
  fi
}

update_state() {
  local key="$1"
  "$PYTHON_BIN" - "$STATE" "$key" "$TODAY" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
date = sys.argv[3]
data = json.loads(path.read_text()) if path.exists() else {}
data.setdefault('lastRuns', {})[key] = date
path.write_text(json.dumps(data, indent=2) + '\n')
PY
}

run_once_for_today() {
  local key="$1"
  ensure_state_file
  local last
  last=$("$PYTHON_BIN" - "$STATE" "$key" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
if not path.exists():
    print("")
else:
    data = json.loads(path.read_text())
    print(data.get('lastRuns', {}).get(key, ''))
PY
)
  [ "$last" = "$TODAY" ] && return 1 || return 0
}

run_step() {
  local key="$1"
  local label="$2"
  local script="$3"
  if run_once_for_today "$key"; then
    log "START $label"
    if "$PYTHON_BIN" "$script" >> "$OUT" 2>&1; then
      update_state "$key"
      log "DONE $label"
    else
      log "FAIL $label"
      return 1
    fi
  else
    log "SKIP $label already ran today"
  fi
}

log "trader morning prep"
log "Layer sequence: layer-1-global-context -> layer-2-stock-screening -> layer-4-trade-plan -> tradeplan-generation"

run_step "trader-layer-1-global-context" "layer-1-global-context" "$LAYER1_SCRIPT"
run_step "trader-layer-2-stock-screening" "layer-2-stock-screening" "$LAYER2_SCRIPT"

log "DEFER layer-4-trade-plan to Scarlett judgment"
log "DEFER tradeplan-generation to Scarlett judgment"
