#!/bin/bash
# pre-bash.sh — runs before every Bash tool call
# Hook type: PreToolUse (Bash)
# Purpose: safety check — block dangerous commands

CMD="$1"

# Block accidental rm -rf on home root
if echo "$CMD" | grep -qE 'rm -rf /home/lazywork\s*$'; then
  echo "BLOCKED: refusing rm -rf on home root" >&2
  exit 1
fi

# Block accidental rm -rf on workspace root
if echo "$CMD" | grep -qE 'rm -rf /home/lazywork/workspace\s*$'; then
  echo "BLOCKED: refusing rm -rf on workspace root" >&2
  exit 1
fi

exit 0
