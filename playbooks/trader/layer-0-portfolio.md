# L0 — Portfolio Analysis (daily 03:00 WIB)

Entry: `/trade:portfolio`. Triggered by CRON Mon–Fri.

L0 writes `trader_status.balance`, `trader_status.pnl`, `trader_status.holdings`, `trader_status.aggressiveness`. Does NOT touch regime/sectors/narratives (L1) or superlist/exitlist (L2). Does NOT execute orders.

Spec: `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`.

## Step 1 — Load prior state

```python
from tools._lib import current_trade as ct
ct_prior = ct.load()
prior_status = ct_prior.trader_status
```

If `load()` raises `ValueError`, send Telegram alert and exit — manual repair required.

## Step 2 — Fetch broker + orders snapshots

Call `mcp__lazytools__carina_portfolio` → `portfolio_resp` (one call returns `{summary, positions}` — replaces per-ticker position_detail loop and standalone cash balance call).

Retry up to 3 times with 2s backoff on 5xx/timeout. If it still fails: `ct.save(ct_prior, layer="l0", status="error", note="carina unreachable")`, send Telegram alert, exit. Do NOT write partial `trader_status`.

Then read local order journal (no MCP — filesystem):

```python
from tools.trader import journal
journal_rows = journal.load_previous_orders(days_back=365)
```

Carina exposes no historical-orders endpoint, so MtD/YtD realized is rolled up from `runtime/orders/*.jsonl` (written by L5). On first run this is empty → l0_synth falls back to `prior_status.pnl.mtd`/`ytd` (spec §8.4).

## Step 3 — Assemble mechanical draft

```python
import datetime as dt
from tools.trader import l0_synth

today_wib = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
draft = l0_synth.assemble_trader_status_draft(
    carina_portfolio=portfolio_resp,
    journal_rows=journal_rows,
    prior_status=prior_status,
    today=today_wib,
)
```

At this point `draft.balance`, `draft.pnl`, `draft.holdings` are populated. `draft.aggressiveness == ""` and every `holding.details == ""` — Opus fills next.

## Step 4 — Per-holding details synthesis

For each holding in `draft.holdings`:

1. Try to read `vault/thesis/<TICKER>.md`. If missing → `holding.details = "no thesis: <brief pnl_pct + lot summary>"` and move on.
2. If present, read last 3 days of `vault/daily/YYYY-MM-DD.md` files and extract lines mentioning the ticker.
3. Send Opus the thesis content + last-3-day ticker context + current pnl_pct + hold age (days since entry in thesis). Ask Opus to classify using ONE prefix, following the priority chain:
   - `redflag:` when any of: pnl ≤ −8%, price < thesis invalidation level, hold_age > 30d without thesis progress, ≥3 defensive/reduce/invalidation mentions in last 3 days.
   - `thesis-drift:` when thesis present but holding diverging.
   - `thesis-on-track:` when thesis present and aligned.
   - (`no thesis:` already handled in step 1.)
4. Validate the response: must start with one of the 4 prefixes exactly. If invalid, retry once with an explicit reminder of the prefix list. Still invalid → `status=error`, Telegram alert, exit.

Fallback: if Opus + openclaude both fail (`claude_model.ModelError`), mark status=error, Telegram, exit.

## Step 5 — Aggressiveness synthesis

Send Opus a single prompt with: `draft.balance`, `draft.pnl` (mtd/ytd/unrealized), holdings summary (ticker + pnl_pct + details prefix), count of `redflag:` holdings, and `prior_status.aggressiveness`.

Ask for one of: `very_defensive | defensive | neutral | aggressive | very_aggressive` — nothing else — plus a one-sentence reason.

Validate tier is in the 5-literal set. Invalid → retry once with explicit literal list reminder. Still invalid → `status=error` + keep `draft.aggressiveness = prior_status.aggressiveness`, Telegram alert, exit.

Valid → `draft.aggressiveness = <tier>`; keep the one-sentence reason in a local variable for the daily note.

## Step 6 — Commit to current_trade

```python
ct_prior.trader_status = draft
summary = f"balance {draft.balance.cash:.0f}, {len(draft.holdings)} holdings, mtd {draft.pnl.mtd:+.0f}, aggr {draft.aggressiveness}"
ct.save(ct_prior, layer="l0", status="ok", note=summary)
```

Spec #1 `save()` is atomic (tempfile + fsync + os.replace), bumps `version`, writes live + snapshot at `runtime/history/YYYY-MM-DD/l0-HHMM.json`.

## Step 7 — Daily note append

```python
from tools._lib import daily_note

hhmm = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).strftime("%H:%M")
body = (
    f"Balance Rp {draft.balance.cash/1_000_000:.1f}M. "
    f"Holdings: {', '.join(h.ticker for h in draft.holdings)}. "
    f"MtD {draft.pnl.mtd:+,.0f}. "
    f"Aggressiveness: {draft.aggressiveness} ({aggressiveness_reason_one_sentence})."
)
redflags = [h for h in draft.holdings if h.details.startswith("redflag:")]
if redflags:
    body += f" Redflag: {', '.join(h.ticker for h in redflags)}."

daily_note.append_section(
    date_str=today_wib.isoformat(),
    section_heading=f"L0 — {hhmm}",
    body=body,
)
```

## Step 8 — Conditional Telegram

```python
from tools.trader import telegram_client

if redflags:
    lines = [f"L0 redflags ({len(redflags)}):"]
    for h in redflags:
        lines.append(f"• {h.ticker} — {h.details[len('redflag: '):]}")
    telegram_client.send_message("\n".join(lines))
```

Silent when zero redflags.

## Guardrails

- Never write orders, never cancel orders.
- Never write to `regime`, `sectors`, `narratives`, `superlist`, `exitlist`.
- If any step before Step 6 fails, keep previous `trader_status` untouched (already on disk).
- Idempotent: a second run at the same date creates a new `l0-HHMM.json` snapshot and appends a new `### L0 — HH:MM` section.
