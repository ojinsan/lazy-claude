#!/usr/bin/env bash
set -euo pipefail
USER_ID="${1:-boss-o}"
MESSAGE="${2:-}"
ASSISTANT="${3:-}"
if [ -z "$MESSAGE" ]; then
  echo "Usage: mem0_add.sh [user_id] "user message" [assistant message]" >&2
  exit 1
fi
exec /home/lazywork/.openclaw/workspace/.venv-mem0/bin/python /home/lazywork/workspace/tools/other/mem0_helper.py add --user-id "$USER_ID" --message "$MESSAGE" --assistant "$ASSISTANT"
