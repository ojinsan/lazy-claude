# Journal Review

## Purpose

Convert market experience into reusable lessons AND pull prior evidence when sizing or planning a new trade. Owns: lesson protocol, thesis append protocol, when to call each journal capability. Does NOT own telegram (see `telegram-notify.md`) or portfolio thresholds (see `portfolio-management.md`).

## Tool

All functions live in `tools/trader/journal.py`. The vault layout convention lives in `vault/README.md` — do not duplicate here.

## When To Call Each Capability

| Before this work | Call this | Reason |
|------------------|-----------|--------|
| L4 plan on ticker with prior history | `get_thesis(ticker)` | Re-read the live thesis frontmatter + sections before writing a new plan |
| L4 plan on any ticker | `detect_recurring_mistakes(days=30)` | If a repeating pattern is active, size down or skip |
| L5 sizing for new entry | `confidence_calibration(days=90)` | If the current conviction bucket drift is > +0.2 (over-optimistic) → cap risk at 1% |
| Close any trade | `close_trade(id, price, lesson)` + `log_lesson_v2(...)` | Every close produces at least one lesson entry |
| L0 Step 6 | `detect_recurring_mistakes` + `confidence_calibration` | Feeds the self-review; any ≥ 3× pattern → Telegram urgent |
| L3 new signal on tracked hold | `append_thesis_review(ticker, 'L3', note)` | Always append-only — never rewrite a thesis file |
| EOD publish | `sync_to_airtable('all')` via `vault_sync.py` | Dashboard refresh |
| Sunday 20:00 WIB | `generate_weekly_review()` | Writes `vault/reviews/weekly/YYYY-Www.md` |
| Last day of month 20:00 WIB | `generate_monthly_review()` | Writes `vault/reviews/monthly/YYYY-MM.md` |

## Lesson Protocol (log_lesson_v2)

Every lesson needs a category + severity. Optional pattern_tag triggers pattern detection over time.

Categories: `entry_timing | exit_timing | thesis_quality | sizing | psychology | missed_trade | portfolio`

Severity:
- `high` — real capital impact (> 1% of equity hit, or thesis blew up)
- `medium` — process mistake that compounds if uncorrected
- `low` — minor friction, worth noting but not urgent

Pattern tag: short kebab-case label like `fake-wall-trap`, `early-exit-on-noise`, `chased-entry-above-zone`. **Use the same tag for the same mistake** — that is what enables `detect_recurring_mistakes` to group them.

Related thesis: pass ticker symbol if the lesson ties to an active thesis. That writes a backlink into the lesson MD so it surfaces in Obsidian.

Example call:
```python
journal.log_lesson_v2(
    lesson="Exited ANTM at 1,420 on a satu-papan wall that turned out fake — re-entered 50bp higher",
    category="exit_timing",
    tickers=["ANTM"],
    severity="medium",
    pattern_tag="early-exit-on-noise",
    related_thesis="ANTM",
)
```

## Thesis Append Protocol

**Never overwrite `vault/thesis/<TICKER>.md`.** Always append a dated line under `## Review Log`.

Use `append_thesis_review(ticker, layer, note)`:
- Creates file from template + Review Log section if missing
- Prepends `- YYYY-MM-DD (L{layer}): {note}` to the section
- One line, one date, one layer. If multiple events in one day → multiple lines.

When status flips (thesis closes, position exits, theme invalidated): update the frontmatter `status:` field manually in Obsidian. Do NOT add a sync helper that rewrites the file from outside.

## Reading Thesis Before Action

```python
t = journal.get_thesis("ANTM")
if t:
    invalidation = t["sections"].get("Invalidation", "")
    setup = t["frontmatter"].get("setup")
```

Always re-read before L4 plan or L5 exit decision. A thesis file is the most recent agreed-upon story; the code writes it, Claude reads it, Boss O audits it in Obsidian.

## Stale Thesis Detection

`thesis_status_summary()` returns active / archived / closed / stale buckets. Stale = status `active` with no Review Log entry in 7+ days. L0 Step 4 should walk the stale list and force a drift check on each.

## Hard Rules

- Be honest. A flattering journal is useless.
- Every closed trade writes a lesson — even wins (lesson: why it worked).
- Never skip `pattern_tag` when the mistake fits an existing pattern.
- Thesis files are append-only from code paths. Manual edits in Obsidian are fine.
- Low-severity lessons stay in vault only; `vault_sync.py` does NOT push them to Airtable.
