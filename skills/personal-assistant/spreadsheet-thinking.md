# Spreadsheet Thinking

## Purpose

Design sheets that are easy to maintain and useful for decisions.

## Focus

- required fields
- simple formulas
- readable column names
- low-friction updates
- explicit assumptions

## Rule

Do not build a clever sheet when a simple tracker is enough.
## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`

