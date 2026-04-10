#!/usr/bin/env bash
set -euo pipefail
USER_ID="${1:-boss-o}"
QUERY="${2:-}"
if [ -z "$QUERY" ]; then
  echo "Usage: mem0_search.sh [user_id] "query"" >&2
  exit 1
fi
exec /home/lazywork/.openclaw/workspace/.venv-mem0/bin/python /home/lazywork/workspace/tools/other/mem0_helper.py search --user-id "$USER_ID" --query "$QUERY"
