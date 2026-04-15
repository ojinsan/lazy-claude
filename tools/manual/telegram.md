# Connector: Telegram

Type: Telegram Bot API
Script: `tools/trader/telegram_client.py`
Auth: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_MESSAGE_THREAD_ID` — from `.env.local`

## Purpose
Sends structured HTML messages to a Telegram chat for each trading layer event.

## CLI Usage
```bash
python3 telegram_client.py [--dry-run] <command> [args...]
```

Use `--dry-run` to render the message locally without sending.

## Commands

| Command | When to use | Required args |
|---------|------------|---------------|
| `layer0` | After L0 portfolio check | `--date`, `--equity`, `--mtd-return`, `--dd`, `--open-risk`, `--top-exposure`, `--action` |
| `layer1` | After L1 context run | `--date`, `--regime`, `--posture`, `--sectors` |
| `layer2` | After L2 screening | `--date`, `--shortlist`, `--top-pick`, `--top-reason` |
| `layer3` | Intraday signal alert | `--timestamp`, `--ticker`, `--signal`, `--note`, `--action` |
| `layer4` | Trade plan ready | `--date`, `--ticker`, `--thesis`, `--entry-low/high`, `--stop`, `--target1`, `--size-amount/pct`, `--risk`, `--trigger` |
| `order-placing` | Before placing order | `--side`, `--ticker`, `--shares`, `--price` |
| `order-confirmed` | After order accepted | `--order-id`, `--side`, `--ticker`, `--shares`, `--price` |
| `order-failed` | After order rejected | `--ticker`, `--error` |
| `execution-summary` | End of session | `--timestamp`, `--exits`, `--entries`, `--holds`, `--cash` |

## Example
```bash
python3 telegram_client.py layer1 \
  --date "2026-04-15" \
  --regime "BULL" \
  --posture "1" \
  --sectors "Energy, Consumer"
```
