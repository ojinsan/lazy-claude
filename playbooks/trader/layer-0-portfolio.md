# Layer 0 — Portfolio (Hedge-Fund View)

Run BEFORE Layer 1 every morning. Start with portfolio health, concentration, and thesis quality before screening any new name.

## Inputs

- `tools/trader/api.py` → `get_portfolio()` for live positions and summary
- `tools/trader/api.py` → `get_cash_info()` for cash / trade balance / buying power
- Airtable `Superlist` where Status = `Hold` for current hold list and notes
- `vault/thesis/<TICKER>.md` for each active hold, if the thesis note already exists
- `vault/data/transactions.json` for recent closed-trade review, if available
- `vault/data/portfolio-state.json` for prior equity snapshots and high-water mark
- Latest EOD note or review from yesterday, if available

## Step 1 — Portfolio Growth & Health

Compute first:
- Total equity = cash + sum of current position market value
- MTD return % vs the first saved equity snapshot of the month
- Drawdown % from the saved high-water mark
- Cash utilization ratio
- Position count

Use this first-pass posture:
- Drawdown ≤ 3% → normal risk allowed
- Drawdown > 5% → reduce planned new exposure by 25%
- Drawdown > 10% → no new entries until posture improves

## Step 2 — Weighting & Concentration

For each hold:
- Position size % of total equity
- P&L %, current market value, and average cost
- Sector exposure contribution

Flag immediately when:
- Any single position > 20% of total equity
- Any sector > 50% of total equity
- Total deployed exposure > 80% of total equity

## Step 3 — Sector Exposure

Map each hold into a theme bucket:
- Energy
- Banking
- Property
- Nickel-EV
- Consumer
- Other

Check whether current holdings still match yesterday's Layer 1 narrative.
Flag any orphan hold: a live position that no longer belongs to an active theme.

## Step 4 — Thesis Drift Per Hold

For each hold:
1. Restate the original thesis and invalidation.
2. Re-check the 6 screening criteria briefly:
   - narrative fit
   - technical structure
   - broker flow
   - SID trend
   - orderbook quality
   - volume confirmation
3. Compare days held vs planned horizon.
4. Mark the hold as `intact`, `watch`, `reduce`, or `exit-candidate`.

If thesis evidence is missing, do not invent it. Mark as `needs refresh` and push it into Layer 4 review.

## Step 5 — Aggregate Probability & Money Flow

Review the portfolio as one book, not as isolated names:
- Aggregate smart-money / foreign participation across held names
- Recent realized P&L, win rate, and risk-reward from journal data when available
- Whether recent performance supports sizing up, staying flat, or sizing down

Treat broad contradiction as a warning:
- If one name looks strong but aggregate money flow is weakening across the book, keep sizing conservative.

## Step 6 — Self-Evaluation

Compare yesterday's Layer 0–Layer 4 calls with what the market actually did:
- Which calls worked?
- Which calls failed?
- What was missed?
- What should change today?

Write the self-review into `vault/journal/YYYY-MM-DD-review.md`.
Log any reusable mistake or process lesson through `tools/trader/journal.py`.

## Tools

| Tool | How |
|------|-----|
| Portfolio health | `tools/trader/portfolio_health.py` — equity, drawdown, concentration, sector exposure |
| Carina portfolio | `tools/trader/api.py` → `get_portfolio()`, `get_cash_info()`, `get_position_detail()` |
| Sector lookup | `tools/trader/api.py` → `get_emitten_info()` |
| Airtable hold list | `tools/trader/airtable_client.py` |
| Journal review | `tools/trader/journal.py` |

## Output (Required)

1. **Portfolio health card** — total equity, MTD, drawdown, cash utilization, top exposure
2. **Action list** — rebalance / reduce / add-to / exit-candidate per hold
3. **Sector exposure snapshot**
4. **Self-review note** — `vault/journal/YYYY-MM-DD-review.md`
5. **Portfolio state update** — `vault/data/portfolio-state.json`
6. **PortfolioLog sync candidate** — prepare a clean summary for Airtable once that table exists

## Telegram Notify (Scarlett)

Send once per scheduled Layer 0 run.

**Trigger conditions:**
- Always send on scheduled 04:30 WIB run
- Urgent if drawdown > 5% from HWM
- Urgent if any hold is marked `exit-candidate`

**Send via Bash:**
```bash
python3 tools/trader/telegram_client.py layer0 \
  --date "$(TZ='Asia/Jakarta' date +%Y-%m-%d)" \
  --equity "{total equity}" \
  --mtd-return "{mtd return %}" \
  --dd "{drawdown %}" \
  --open-risk "{open risk or 'n/a'}" \
  --top-exposure "{top position / sector}" \
  --action "{one-line action summary}"
```

## Skills To Load

- `skills/trader/portfolio-management.md`
- `skills/trader/sector-exposure.md`
- `skills/trader/probability-measurement.md`
- `skills/trader/money-flow-analysis.md`
- `skills/trader/portfolio-self-review.md`
- `skills/trader/thesis-drift-check.md`
- `skills/trader/journal-review.md`
