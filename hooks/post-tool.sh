#!/bin/bash
# post-tool.sh — runs after every tool call
# Hook type: PostToolUse
# Purpose: lightweight logging of tool activity

TOOL="$1"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log to session log (append only, never read back in context)
echo "$TIMESTAMP | $TOOL" >> /home/lazywork/.claude/hooks/tool-log.txt
