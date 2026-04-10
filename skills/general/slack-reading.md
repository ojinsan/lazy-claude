# Slack Reading

## What This Does
Open Slack in the logged-in Firefox profile and read channels, threads, DMs, and search results.

## Tool Path
`~/.claude/tools/general/browser/slack_reader.py`

## Usage
```bash
python3 ~/.claude/tools/general/browser/slack_reader.py channels
python3 ~/.claude/tools/general/browser/slack_reader.py search --query "launch"
```

## When to use
- read channel history
- search for internal references
- inspect a thread without posting

## Safety
- read-only only
- never post, react, or upload without permission
