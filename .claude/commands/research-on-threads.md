Research a topic on Threads using the logged-in Firefox Playwright scraper.

## How to use

User invokes: `/research-on-threads <topic or query>`

Extract the query from the user's input (everything after the command name).
If no query is given, ask for one before proceeding.

## Run the scraper

```bash
cd ~/workspace/tools/general/playwright
node threads-scraper.js --query "$QUERY" --limit 15
```

Use the openclaw logged-in Firefox profile (default — already wired into the scraper).
Do NOT pass `--headed` unless the user explicitly asks or login fails.

## Output handling

Parse the JSON output from the scraper. For each result:
- Show `url`, `text` (truncated to ~200 chars), and `views`
- Skip results where `text` is empty or under 20 chars

Summarise key themes, sentiment, and notable posts after listing results.

## Constraints

- Read-only: do not post, like, reply, or follow
- Do not expose cookies or session data
- If scraper returns 0 results or login wall detected, report it and suggest running headed to re-login
