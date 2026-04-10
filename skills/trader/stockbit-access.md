# Stockbit Access

## Purpose

Handle Stockbit-related access or auth flows carefully when they are needed for trader work.

## Safety Rules

- tokens, cookies, and credentials are sensitive
- never reveal them in output
- never paste them into notes casually
- use only the minimum access needed
- if Boss O has not authorized the access path, stop and ask

## Rule

Access exists to support analysis, not to justify unsafe handling of secrets.
## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`

