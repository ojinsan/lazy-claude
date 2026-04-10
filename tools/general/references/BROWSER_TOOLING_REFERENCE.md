# Browser Tooling Reference

## Standard

Use Firefox persistent profiles by default for browser automation unless a tool explicitly requires another engine.

Primary profile:
- `~/workspace/tools/general/playwright/.firefox-profile-threads`

## Rules

1. Prefer Firefox with existing login state.
2. Do not assume Chromium for Threads workflows.
3. Legacy profile paths are fallback-only.
4. If the original Firefox profile gets new login/session state, refresh the copied profile.
5. Keep obsolete entrypoints only as compatibility wrappers when needed.

## Threads

Preferred:
```bash
node ~/workspace/tools/general/playwright/threads-scraper.js --query "your query" --limit 10
```

Compatibility only:
```bash
python3 ~/workspace/tools/general/playwright/threads_search.py --query "your query" --limit 10
```

Notes:
- `threads-scraper.js` is the main Threads tool
- `threads_search.py` is deprecated and kept only so older calls do not break
- both follow the Firefox profile standard

## Legacy Paths

Do not treat these as the current standard:
- `~/.config/playwright/firefox_profiles/cloned_profile`
- Chromium-first Threads assumptions
- mismatched profile paths between Python and JS tooling

Legacy paths may remain as fallback references only.

## Profile Sync Rule

If the original Firefox profile gets:
- new login
- refreshed cookies
- refreshed session
- important new site state

then refresh the copied Firefox profile too.

## Google Maps

Env file:
- `~/.openclaw/workspace/.env.local`

Required key:
```env
GOOGLE_MAPS_API_KEY=your_key_here
```

Referenced project:
- `claude-home-01`

## Related Files

- `scarlett/tools/general/playwright/threads-scraper.js`
- `scarlett/tools/general/playwright/threads_search.py`
- `scarlett/tools/general/scripts/google_maps.py`
- `scarlett/tools/general/browser/browser_base.py`
- `scarlett/tools/general/scripts/car_comparison_comprehensive.py`

## Validation Status

Validated on 2026-04-03:
- JS syntax check passed for `threads-scraper.js`
- Python compile check passed for:
  - `threads_search.py`
  - `google_maps.py`
  - `browser_base.py`
  - `car_comparison_comprehensive.py`

Not included in this note:
- live external site execution
- live API credential verification
