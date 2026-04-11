# Connector: Browser (Playwright Base)

Type: Playwright automation
Base script: `tools/general/browser/browser_base.py`

## Derived connectors (all extend browser_base)
| Script                        | Service      |
|-------------------------------|--------------|
| `instagram_browser.py`        | Instagram    |
| `notion_browser.py`           | Notion       |
| `shopee_browser.py`           | Shopee       |
| `tokopedia_browser.py`        | Tokopedia    |
| `slack_reader.py`             | Slack        |
| `web_browse.py`               | Generic web  |

## Pattern
Each derived connector:
1. Inherits browser_base (launch, auth, screenshot helpers)
2. Implements service-specific selectors and actions
3. Returns structured data (dict/list)

## Skills
- `skills/general/shopee.md`
- `skills/general/tokopedia.md`
- `skills/general/instagram.md`
