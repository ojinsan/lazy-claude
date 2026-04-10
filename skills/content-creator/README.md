# Content Creator Skills

This library is intentionally empty for now.

Add content-creator skills only after Boss O defines:

- audience
- platforms
- voice
- content types
- quality bar
## Tool Resolution

When a skill needs code or helper scripts, resolve them from `~/.claude/tools` using the matching role folder first, then `other` if needed.

Examples:
- trader skills -> `~/.claude/tools/trader`
- personal-assistant skills -> `~/.claude/tools/personal-assistance`
- content-creator skills -> `~/.claude/tools/content-creator`
- shared helpers -> `~/.claude/tools/other`

