# Connector: Instagram

Type: Playwright scraper (logged-in Firefox profile)
Scripts:
- `tools/general/playwright/instagram-scraper.js` — profile/post scraping via Firefox session
- `tools/general/browser/instagram_browser.py` — Python Playwright automation

## Capability
Scrapes public and logged-in Instagram profiles, posts, and search results.
Requires a pre-seeded Firefox profile with an active Instagram session.

## Usage
```bash
node tools/general/playwright/instagram-scraper.js profile --username <username>
```

## Profile
Firefox profile with Instagram session: `tools/general/playwright/.firefox-profile-instagram/`
To seed: copy from `~/.mozilla/firefox/<profile>/` after logging in to Instagram manually.
Do NOT overwrite or clear this profile.

## Constraints
- Read-only. No posting, liking, following, or interacting.
- Do not expose cookies or session data outside local analysis.
