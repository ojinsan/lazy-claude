#!/usr/bin/env bash
set -euo pipefail
LOGDIR="$HOME/workspace/runtime/logs"
mkdir -p "$LOGDIR"
nohup python3 "$HOME/workspace/tools/trader/running_trade_poller.py" >> "$LOGDIR/running-trade-poller.log" 2>&1 &
echo $! > "$LOGDIR/running-trade-poller.pid"
echo "started running_trade_poller pid $(cat "$LOGDIR/running-trade-poller.pid")"
