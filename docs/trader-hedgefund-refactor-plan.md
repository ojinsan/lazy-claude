# Trader Hedge-Fund Refactor — Execution Plan

**For:** a cheaper AI (Sonnet or smaller) executing this end-to-end.
**Objective:** transform the current signal-based trader into a hedge-fund-style operation with portfolio thinking, deeper skills, integrated execution, and better journaling.

---

## Ground Rules (READ FIRST)

1. **Scope control**: work phase by phase. Do NOT jump ahead. Complete a phase, commit, ask user for confirmation, move on.
2. **No silent destructive changes**: anything that replaces existing code/skills → move the old version to `archive/` inside the same folder. Never delete.
3. **Index every new file**: if you create a skill → add to `skills/trader/CLAUDE.md` Skills Index. If you create a tool → add to `tools/CLAUDE.md` script index. If you create a playbook → add to `playbooks/trader/CLAUDE.md`.
4. **Commit every phase**: `git add -p` then commit with prefix `[Phase N]`. Then `git push`. Ask user before pushing the first time.
5. **Telegram over everything**: any new workflow that produces a decision → wire it through `tools/trader/telegram_client.py`. If a telegram subcommand is missing, add one.
6. **Confirm destructive/ambiguous decisions with Boss O** before acting. Non-code decisions below marked **[NEEDS CONFIRM]** are already pre-answered — if unsure, re-ask.
7. **Working directory**: `/home/lazywork/workspace` throughout.
8. **Token efficiency**: don't bulk-read. Grep/glob first, read only the specific file and line range you need.

---

## Current State Summary (as of 2026-04-15)

- **Playbooks**: `playbooks/trader/` has L1, L2, L3, L4, and `execution.md`. All exist but thin in places.
- **Skills**: 25 skills in `skills/trader/`. Several are shallow (e.g. `bid-offer-analysis.md` is 26 lines).
- **Tools**: ~30 `.py` files in `tools/trader/` — all documented in `tools/CLAUDE.md` now.
- **Journal**: `tools/trader/journal.py` → writes to `/home/lazywork/lazyboy/trade/journal/` (OUTSIDE workspace, bad). Uses JSON + daily MD. No Obsidian, no Airtable sync in journal module.
- **Portfolio**: `api.py` has `get_portfolio`, `get_position_detail`, `get_cash_info`, but NO dedicated portfolio-level skill or playbook.
- **Execution**: `playbooks/trader/execution.md` exists but is NOT numbered as a layer.
- **L0**: does not exist.

---

## Phase 0 — Setup & Decisions (do before coding)

### Decisions already made by Boss O (use these)

| Question | Decision |
|----------|----------|
| L0 exists? | YES — new hedge-fund portfolio layer |
| L5 exists? | YES — execution is renamed L5 |
| Execution inside every layer? | YES, **when confident**, with Telegram notify first |
| Journal system | Hybrid: Obsidian vault (MD, human) + JSON (machine) + Airtable (dashboard). See Phase 5. |
| Keep old code when replacing? | YES, archive folder |
| Commit + push every phase | YES, ask first time |

### Confirmed by Boss O (USE THESE — do not re-ask)

- **Obsidian vault location**: top-level `/home/lazywork/workspace/vault/` (NOT inside `runtime/`). Vault is first-class, used for both thesis writing AND journaling.
- **Old journal migration**: do NOT migrate `/home/lazywork/lazyboy/trade/journal/` contents. Start fresh in the new vault.
- **`journal.py` paths**: migrate to workspace-internal — but more importantly, **make journaling useful, not trash**. See Phase 5 for the upgrade list.
- **Portfolio capital figure**: compute live from `api.get_cash_info()` + sum of `api.get_portfolio()` positions. No hardcoded capital constant.
- **`config.py`**: pure infra plumbing — paths, env loader, backend URL/token. Hedge fund assistant never thinks about it directly. Classify as infra in `tools/CLAUDE.md` (same bucket as `stockbit_auth.py`, `stockbit_headers.py`).

### Actions for Phase 0
1. Read this whole plan.
2. `git status` — ensure clean start. If dirty, ask Boss O whether to stash or commit first.
3. Create vault structure:
   ```bash
   mkdir -p /home/lazywork/workspace/vault/{daily,thesis,journal,lessons,layer-output/{l0,l1,l2,l3,l4,l5},data,reviews/{weekly,monthly}}
   mkdir -p /home/lazywork/workspace/tools/trader/archive
   mkdir -p /home/lazywork/workspace/skills/trader/archive
   ```
4. Create `vault/README.md` (template in Phase 5.3) so Boss O knows how to open it in Obsidian.

---

## Phase 1 — Layer 0: Hedge-Fund Portfolio

**Goal:** before any per-stock work each morning, Claude must look at the portfolio as a whole.

### 1.1 Create playbook `playbooks/trader/layer-0-portfolio.md`

Structure (mirror L1-L4 style — inputs / what to gather / tools / output / telegram / skills):

```markdown
# Layer 0 — Portfolio (Hedge-Fund View)

Run BEFORE L1 every morning. Evaluate portfolio as a whole — don't think per-stock yet.

## Inputs
- `api.get_portfolio()` → full positions + summary
- `api.get_cash_info()` → buying power + cash
- Airtable `Superlist` where Status = Hold → thesis snapshot for each hold
- Yesterday's EOD from `runtime/eod/YYYY-MM-DD.md`
- Last 30d transactions from `vault/data/transactions.json`
- **Total capital is computed live**: `api.get_cash_info()['cash'] + sum(pos['market_value'] for pos in api.get_portfolio()['positions'])`. Never hardcode capital.

## Step 1 — Portfolio Growth & Health
Compute:
- Total equity = cash + sum(positions market value)
- MTD return % vs IHSG MTD
- Drawdown from high-water mark (stored in runtime/vault/portfolio-state.json)
- Open risk: sum of (entry - current stop) × qty / total equity
- Realized PnL last 5/20/60 trading days

## Step 2 — Weighting & Concentration
For each hold:
- Position size % of total equity
- Flag any >20% single position, or >50% sector concentration
- Correlation check: are holds moving together? (simple: same sector + same broker flow direction)

## Step 3 — Sector Exposure
- Map holds to sectors (use Stockbit sector codes via api.get_emitten_info)
- Compare vs L1 theme focus from yesterday — are we aligned with narrative?
- Flag orphan holds (not in any active theme)

## Step 4 — Thesis Drift per Hold
For each hold, read latest thesis from `vault/thesis/<TICKER>.md`:
- Still valid? (re-check the 6 screening criteria briefly)
- Days held vs planned horizon
- Broker flow: is smart money still there?

## Step 5 — Probability & Money Flow Aggregate
- Overall money flow: sum of net foreign flow for held tickers last 5 days
- Win probability estimate: win_rate × avg_r from last 30 closed trades (journal.py review_trades)
- Cash utilization ratio

## Step 6 — Self-Evaluation
Look at yesterday's L0+L1+L2+L3+L4 decisions vs actual outcomes:
- Which calls worked? Which didn't? Write to `vault/journal/YYYY-MM-DD-review.md`
- Log lessons via `journal.log_lesson(...)` for any pattern (auto-tagged by category)
- If a hold breached invalidation overnight → flag for L5 exit AND write a "what I missed yesterday" lesson

## Output (Required)
1. **Portfolio health card** (MTD%, DD, exposure, open risk)
2. **Action list**: rebalance / reduce / add-to / exit-candidate per hold
3. **Sector exposure snapshot**
4. **Self-review note** → `vault/journal/YYYY-MM-DD-review.md`
5. **Post to Airtable `PortfolioLog`** (new table — see Phase 5)
6. **Update `vault/data/portfolio-state.json`** with today's equity/DD/exposure for tomorrow's diff

## Telegram
Send layer0 message after output. Trigger conditions:
- Always send on scheduled 04:30 WIB run
- Urgent if DD > 5% from HWM, or any position breaches invalidation overnight

## Skills To Load
- `skills/trader/portfolio-management.md` (NEW)
- `skills/trader/sector-exposure.md` (NEW)
- `skills/trader/thesis-drift-check.md` (exists in archive — restore)
- `skills/trader/journal-review.md`
```

### 1.2 Create new skills in `skills/trader/`

| New skill file | Content outline |
|----------------|-----------------|
| `portfolio-management.md` | Position sizing rules at portfolio level, max concentration (20% single / 50% sector), drawdown thresholds (reduce 25% exposure if DD > 5%, halt new entries if DD > 10%), rebalance triggers |
| `sector-exposure.md` | Mapping Stockbit sectors → Boss O theme buckets (Energy, Banking, Property, Nickel-EV, Consumer). Rules for max exposure per sector, rotation triggers |
| `probability-measurement.md` | How to compute win rate, expectancy, Kelly fraction (capped). When to size up or down based on recent hit rate |
| `money-flow-analysis.md` | Foreign net flow aggregation, smart-money flow direction, when aggregate flow contradicts individual names |
| `portfolio-self-review.md` | Daily review protocol: what happened, what surprised me, what to change tomorrow. Template format |

Each skill file: ~60–120 lines. Include concrete thresholds, example prompts, and which `tools/trader/*.py` functions to call.

### 1.3 Restore `thesis-drift-check.md` from archive

```bash
cp playbooks/trader/archive/thesis-drift-check.md skills/trader/thesis-drift-check.md
```
Update content to modern form — reference `api.py` and Airtable. Keep the archive copy.

### 1.4 New tool: `tools/trader/portfolio_health.py`

Single-purpose script:
```python
# API
def compute_portfolio_state() -> dict
def compute_drawdown(equity_history: list) -> float
def compute_exposure_breakdown() -> dict  # by ticker, by sector
def compute_concentration_flags() -> list
def save_state(state: dict) -> None  # to runtime/vault/portfolio-state.json
def load_state() -> dict
```
Add to `tools/CLAUDE.md` script index.

### 1.5 New telegram subcommand

In `tools/trader/telegram_client.py`, add:
```python
# sub.add_parser("layer0") with args: --date, --equity, --mtd-return, --dd, --open-risk, --top-exposure, --action
```
Follow the pattern of existing builders.

### 1.6 Schedule L0

Update `tools/trader/cron-dispatcher.sh`:
```bash
# L0 Portfolio window: 04:30 WIB
elif [[ $WIB_HOUR -eq 4 && $WIB_MIN -eq 30 ]]; then
    log "→ PORTFOLIO (L0) start"
    run_claude_job "$COMMAND_DIR/portfolio.md"
    log "← PORTFOLIO done"
```
Create `.claude/commands/trade/portfolio.md` with a prompt that loads the L0 playbook.

Update `.claude/commands/trade.md` to mention L0 in the layer list.

### 1.7 Update indices

- `playbooks/trader/CLAUDE.md`: add L0 row to the 4-Layer System table (make it 5-Layer or rename). Update daily schedule to include 04:30 entry.
- `skills/trader/CLAUDE.md`: add new skills under a "Layer 0 — Portfolio" section in Skills Index.

### 1.8 Commit
`[Phase 1] Add Layer 0 hedge-fund portfolio view — playbook, 5 new skills, portfolio_health tool, L0 telegram, cron 04:30`

---

## Phase 2 — Layer 5: Execution (rename + integrate)

### 2.1 Rename playbook
```bash
git mv playbooks/trader/execution.md playbooks/trader/layer-5-execution.md
```
Update references in `playbooks/trader/CLAUDE.md`, any skill pointing to it, and `cron-dispatcher.sh`. Grep first: `grep -rn "execution.md" playbooks skills tools .claude`.

### 2.2 Add "Execution Trigger" block to L1, L2, L3, L4 playbooks

Each layer playbook gets a new section BEFORE "Output (Required)":

```markdown
## Execution Trigger (Integrated)

If during this layer you reach **high confidence** (see skills/trader/execution.md for criteria), you may execute immediately instead of waiting for the scheduled L5 run.

**Confidence gate for inline execution:**
- L1: no inline execution (context only)
- L2: only if a name in the shortlist is at an open entry window AND matches all 6 screening criteria → pre-place limit order at entry low
- L3: if `accumulation_setup` + price inside entry zone + thesis intact → execute immediately
- L4: if plan is marked urgent + entry window live → execute immediately
- L5: always, this is the default execution layer

**Before placing ANY order inline:**
1. Send Telegram `layer{N}-intent` message (NEW subcommand — see below)
2. Wait 60 seconds for Boss O to react (observable via later re-read of telegram state)
3. Place order via `api.place_buy_order()` / `place_sell_order()`
4. Send Telegram `order-confirmed`
```

### 2.3 Add new telegram subcommand `intent`

In `telegram_client.py`, generic intent builder:
```python
# sub.add_parser("intent") with --layer, --ticker, --action BUY|SELL, --price, --shares, --reason
# Body: "⚡ EXECUTION INTENT (from Layer {layer}) — about to place {action} {ticker} @ {price}, shares {shares}. Reason: {reason}. Will fire in 60s unless cancelled."
```

### 2.4 Update `skills/trader/execution.md`

Add a "Confidence Gate" section that defines the exact criteria per layer. Rules of thumb:
- 6/6 screening criteria aligned → auto inline
- 5/6 with L1 narrative fit + broker accumulation → inline allowed
- <5/6 → wait for L5 window
- DD > 5% from HWM → inline DISABLED regardless of criteria

### 2.5 Commit
`[Phase 2] Rename execution → layer-5, integrate inline execution gates in L2-L4, add intent telegram`

---

## Phase 3 — Deepen Shallow Skills

### 3.1 Bid-offer-analysis.md (CRITICAL — currently only 26 lines)

Replace with a full skill. Reference doc: `tools/trader/tick_walls.py`, `tools/trader/orderbook_poller.py`, `tools/trader/orderbook_ws.py`.

New structure:

```markdown
# Bid-Offer Analysis

## Purpose
Read orderbook behavior to detect fake walls, real supply/demand, and absorption patterns. Translate shape into action.

## Wall Size Classification

| Term (ID) | Depth | Behavior signal |
|-----------|-------|-----------------|
| Satu papan | Wall visible only at best bid/offer (1 level) | Weakest — easily faked, often retail blocker |
| Dua papan | Wall spans 2 levels | Medium — real defense but still flippable |
| Keseluruhan (overall) | Wall across 3+ levels | Strong — either true resistance/support OR coordinated whale distribution/accumulation |

## Fake Wall Detection

A wall is likely **fake** when:
- Appears right before a price level and vanishes within 30 seconds without trades
- Size is large but order_count is small (1 broker with huge lot → whale placeholder, not real liquidity)
- Wall moves up/down as price approaches (chasing the tape)
- Reappears at similar size after being "eaten" → same broker re-listing

A wall is likely **real** when:
- Stays >2 minutes with consistent size
- Multiple broker IDs contributing to the level
- Absorbs trades (offer count drops tick-by-tick as buys hit it) and price eventually grinds through

## Absorption Patterns (Bandar Eating Retail)

### Near Resistance (likely to break)
- Thick offer wall + whale bids underneath absorbing retail sells
- Pattern: retail sells hit bid, whale bid refreshes without price dropping
- Offer wall slowly thins as whale buys hidden orders
- → expect breakout, size up entry

### Near Support (likely to bounce)
- Thick bid wall + whale offers above absorbing retail buys
- Wait — this is distribution! Pattern: retail buys hit offer, offer refreshes without price rising
- OR: bid wall holds, sellers give up → bounce incoming
- Distinguish by running trade size: large lot seller + small lot buyer = distribution; small lot seller + large lot buyer = absorption

## Pressure Imbalance Metrics

Compute from orderbook snapshot:
- **Bid/Ask ratio** (top 5 levels): >1.5 = buy pressure, <0.67 = sell pressure
- **Depth asymmetry**: bid_depth_5lv / ask_depth_5lv
- **Wall persistence**: seconds a wall survives before being pulled

## Tool Resolution

| Use case | Tool |
|----------|------|
| Single snapshot | `api.get_stockbit_orderbook(ticker)` |
| Continuous poll | `tools/trader/orderbook_poller.py --ticker X --interval 5` |
| Live WebSocket | `tools/trader/orderbook_ws.py` |
| Wall detection | `tools/trader/tick_walls.py` (identify large threshold walls) |
| Delta detection | `api.get_orderbook_delta(ticker)` |

## Decision Output

Each bid-offer read must produce:
1. **Wall classification**: satu-papan / dua-papan / keseluruhan
2. **Authenticity**: fake / real / unclear
3. **Absorption direction**: bandar absorbing sells (bullish) / bandar distributing (bearish) / no absorption
4. **Action hint**: break likely / bounce likely / wait / exit

## Example prompts
- "Price at 1,250 with thick offer at 1,260 (satu papan, 500k lot, 1 broker). Running trade shows 10k lot buys hitting bid continuously. What's the read?"
- Expected answer: likely fake wall, whale accumulating, break probable if wall persists <2min with shrinking size.
```

### 3.2 Deepen `orderbook-reading.md` and `whale-retail-analysis.md`

Apply same treatment. Current versions likely thin. Read first, then rewrite. Put old version under `skills/trader/archive/` before replacing.

### 3.3 Deepen `realtime-monitoring.md` and `thesis-evaluation.md`

Same treatment. Thesis evaluation must reference the 6 screening criteria by name and require ticker-by-ticker re-check.

### 3.4 Commit
`[Phase 3] Deepen bid-offer-analysis, orderbook-reading, whale-retail-analysis, realtime-monitoring, thesis-evaluation skills`

---

## Phase 4 — Tool ↔ Skill Coverage Audit

### 4.1 Build coverage matrix

For every `.py` in `tools/trader/`, identify:
- Is it referenced in any `playbooks/trader/*.md`?
- Is it referenced in any `skills/trader/*.md`?
- Is it in `tools/CLAUDE.md` script index?

Produce `docs/coverage-matrix.md`:

```markdown
| Script | In playbook | In skill | In tools index | Gap? |
|--------|-------------|----------|----------------|------|
| api.py | L1-L5 | many | yes | ok |
| telegram_client.py | L1-L5 | execution | yes | ok |
| ... | ... | ... | ... | ... |
```

Use this script to build the matrix:
```bash
for f in tools/trader/*.py; do
  base=$(basename "$f" .py)
  in_pb=$(grep -l "$base" playbooks/trader/*.md | wc -l)
  in_sk=$(grep -l "$base" skills/trader/*.md | wc -l)
  in_idx=$(grep -c "$base" tools/CLAUDE.md)
  echo "$base | $in_pb | $in_sk | $in_idx"
done
```

### 4.2 Close gaps

For each tool with a Gap:
- Infra tools (config, auth, headers): note as infra only, no skill needed
- Analysis tools without skill: write a minimal skill OR add a section to an existing skill
- Orphan tools no one uses: ask Boss O — delete or restore to active use

### 4.3 Commit
`[Phase 4] Tool-skill coverage audit + close gaps`

---

## Phase 5 — Vault + Useful Journaling

The vault is **first-class** — not buried inside `runtime/`. Boss O opens it in Obsidian for thesis writing, daily journaling, and lesson review. The current `journal.py` is barely used because it's just append-and-forget. We make it useful.

### 5.1 Vault layout (top-level `vault/`)

```
/home/lazywork/workspace/vault/
├── README.md                ← "Open this folder in Obsidian"
├── daily/                   ← YYYY-MM-DD.md — Boss O's free-form notes + Claude appends
├── thesis/                  ← one MD per ticker — written L2, appended L3/L4/L5
│   └── <TICKER>.md
├── themes/                  ← L1 narrative themes (one MD per active theme)
│   └── <theme-slug>.md
├── journal/                 ← Claude self-review per day (from L0)
│   └── YYYY-MM-DD-review.md
├── lessons/                 ← one MD per lesson (linkable, taggable)
│   └── YYYY-MM-DD-<slug>.md
├── layer-output/            ← raw L0-L5 outputs archived
│   ├── l0/YYYY-MM-DD.md
│   ├── l1/YYYY-MM-DD.md
│   ├── l2/YYYY-MM-DD.md
│   ├── l3/YYYY-MM-DD-HHMM.md
│   ├── l4/YYYY-MM-DD-<TICKER>.md
│   └── l5/YYYY-MM-DD.md
├── reviews/
│   ├── weekly/YYYY-Www.md   ← auto-generated Sun night
│   └── monthly/YYYY-MM.md   ← auto-generated last day of month
└── data/                    ← machine-read JSON (DO NOT edit by hand)
    ├── transactions.json
    ├── lessons.json
    ├── portfolio-state.json
    └── thesis-index.json    ← {ticker: status, last_review_date, related_lessons[]}
```

**Conventions**:
- All thesis & lesson files use Obsidian `[[wikilinks]]` to cross-reference
- Tags via YAML frontmatter and inline `#sector/energy #setup/accumulation`
- Daily notes use Obsidian's daily-note format (one per day, free-form on top, Claude-appended sections below `## Auto-Appended`)

### 5.2 Migrate `journal.py` paths (do NOT migrate old data)

Archive then edit:
```bash
cp tools/trader/journal.py tools/trader/archive/journal.py.v1
```

New constants in `journal.py`:
```python
VAULT = Path("/home/lazywork/workspace/vault")
DAILY_DIR = VAULT / "daily"
JOURNAL_DIR = VAULT / "journal"
LESSONS_DIR = VAULT / "lessons"
THESIS_DIR = VAULT / "thesis"
DATA_DIR = VAULT / "data"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
LESSONS_FILE = DATA_DIR / "lessons.json"
THESIS_INDEX = DATA_DIR / "thesis-index.json"
```

Old data at `/home/lazywork/lazyboy/trade/journal/` is left alone (Boss O said don't migrate). Fresh start.

### 5.3 Make journaling actually useful (the big upgrade)

**Current `journal.py` capabilities:** append, search by string, simple PnL summary. That's it. Trash for hedge-fund work.

**Add these capabilities:**

#### A. Lesson auto-categorization & confidence calibration
```python
def log_lesson_v2(
    lesson: str,
    category: str,                # entry_timing|exit_timing|thesis_quality|sizing|psychology|missed_trade|portfolio
    tickers: list[str] = None,
    severity: str = "medium",     # low|medium|high
    pattern_tag: str = None,      # e.g. "fake-wall-trap", "early-exit-on-noise"
    related_thesis: str = None,   # path to vault/thesis/<TICKER>.md
):
    # Writes BOTH to lessons.json AND vault/lessons/YYYY-MM-DD-<slug>.md as Obsidian note
    # MD includes frontmatter (category, tickers, severity, tags), backlinks to thesis
```

#### B. Pattern detection
```python
def detect_recurring_mistakes(days: int = 30) -> dict:
    """
    Group lessons by pattern_tag in the last N days.
    Return: {pattern_tag: {count, tickers, severity_avg, latest_date, lesson_ids}}
    Surface anything that occurred ≥3 times → Boss O sees same mistake.
    """
```
Called by L0 Step 6 — if any pattern hits ≥3 occurrences, Telegram urgent alert.

#### C. Per-trade attribution
```python
def attribute_trade(trade_id: int) -> dict:
    """
    For a closed trade, return: which signals were the deciding factor.
    {
      "thesis_quality": 0.0-1.0,
      "entry_timing": 0.0-1.0,
      "exit_timing": 0.0-1.0,
      "sizing": 0.0-1.0,
      "biggest_contributor": "entry_timing",
      "biggest_detractor": "exit_timing"
    }
    Uses thesis MD + Layer outputs for that ticker on entry/exit dates.
    """
```

#### D. Confidence calibration
At entry, Claude logs predicted conviction (HIGH/MED/LOW). At exit, journal computes actual outcome bucket. Over time produces calibration:
```python
def confidence_calibration(days: int = 90) -> dict:
    """
    Returns: {HIGH: {predicted: 0.7, actual_win_rate: 0.55, drift: -0.15}, ...}
    If drift > 0.2 in either direction → flag in L0 review.
    """
```

#### E. Weekly + monthly auto-reviews (cron-driven)
```python
def generate_weekly_review() -> str:
    """Render full week summary as Obsidian MD → vault/reviews/weekly/YYYY-Www.md"""
def generate_monthly_review() -> str:
    """Render month summary → vault/reviews/monthly/YYYY-MM.md"""
```
Cron: Sun 20:00 WIB for weekly, last day of month 20:00 WIB for monthly. Add to `cron-dispatcher.sh`.

Both reviews include:
- PnL, win rate, expectancy, R-multiple distribution
- Top 3 winners + losers with attribution
- Recurring mistake patterns
- Confidence calibration drift
- Thesis hit rate by setup type (accumulation / breakout / shakeout-recovery)
- Sector exposure heatmap (text table)
- One actionable recommendation for next period

#### F. Thesis-aware queries
```python
def get_thesis(ticker: str) -> dict:
    """Read vault/thesis/<TICKER>.md, return frontmatter + sections as dict."""

def append_thesis_review(ticker: str, layer: str, note: str):
    """Append a new dated entry under the ## Review Log section."""

def thesis_status_summary() -> dict:
    """Scan all vault/thesis/*.md, return {active: [...], archived: [...], stale: [...]}."""
```
Stale = no review log entry in 7+ days while status is `active`.

### 5.4 Thesis & theme protocol

**L1 produces** `vault/themes/<theme-slug>.md` for each active narrative theme:
```markdown
---
theme: nickel-ev-rebound
created: 2026-04-15
status: active
sector: nickel
related_tickers: [ANTM, INCO, MBMA]
---

# Nickel EV Rebound

## Why Now
[macro context, China demand, LME inventory]

## Confluence Required
- [criteria 1]
- [criteria 2]

## Watch Names
- [[ANTM]] — primary, structural play
- [[INCO]] — beta to nickel price
- [[MBMA]] — speculative, smaller cap

## Invalidation
[one sentence — what kills this theme]

## Review Log
- 2026-04-15: theme initiated
```

**L2 produces** `vault/thesis/<TICKER>.md` per shortlisted name:
```markdown
---
ticker: ANTM
created: 2026-04-15
layer_origin: L2
status: active
setup: accumulation
related_themes: [[nickel-ev-rebound]]
related_lessons: []
---

# ANTM — Accumulation Thesis

## Why Now
Linked to [[nickel-ev-rebound]]. SID -8% over 14d, smart money (BK, ZP) net buying since Apr 8.

## The Operator View
[broker flow, SID detail]

## Technical
[S/R, Wyckoff phase, key levels]

## Entry Logic
[link to L4 plan when created]

## Invalidation
Close below 1,420 (last accumulation low)

## Review Log
- 2026-04-15: created at L2
```

**L3, L4, L5** APPEND to the Review Log section — never rewrite the file.

When a position closes (full exit), `status` flips to `closed`, and `append_thesis_review` writes the post-mortem with PnL + attribution.

### 5.5 Airtable sync (light)

Don't replace JSON — Airtable is for Boss O's dashboard view. Sync only:
- **Journal** table: closed trades (1 row per transaction with PnL, attribution, lesson link)
- **Lessons** table: high-severity lessons only (low-severity stays in vault)
- **PortfolioLog** table: daily L0 portfolio state snapshot (1 row per day)

Helper:
```python
def sync_to_airtable(table: str, kind: str = "incremental") -> int:
    """Push new/changed rows to Airtable. Returns count synced."""
```
Run at EOD via `runtime_eod_publish.py`.

### 5.6 Daily-note auto-append

At end of each layer, append a section to today's `vault/daily/YYYY-MM-DD.md`:
```markdown
## Auto-Appended

### L1 — 05:02
Regime: cautious. Themes: nickel-ev-rebound, banking-bi-cut.
[full output linked → [[layer-output/l1/2026-04-15]]]

### L2 — 05:33
Shortlist: ANTM, INCO, BBRI. Top: [[ANTM]] (matches [[nickel-ev-rebound]]).

### L3 — 09:34
[[ANTM]] accumulation_setup detected at 1,455. Promoted to L4.

### L5 — 09:36
BUY [[ANTM]] 5000 @ 1,455. Order ABC123.
```

This makes the daily note a single timeline Boss O can scroll in Obsidian.

### 5.7 Update skill `journal-review.md`

Rewrite to teach Claude how to use the new journaling capabilities:
- Before any L4 plan → call `detect_recurring_mistakes` + `get_thesis` if ticker has prior history
- Before sizing in L5 → check `confidence_calibration` for current setup type
- Reference vault paths and Obsidian wikilink syntax

Archive old version: `cp skills/trader/journal-review.md skills/trader/archive/journal-review.v1.md`

### 5.8 vault/README.md template

```markdown
# Trader Vault

This folder is your Obsidian vault. Open it in Obsidian.app.

## Folders
- `daily/` — your daily notes (free-form, with Claude-appended layer summaries)
- `thesis/` — one note per ticker with an active thesis
- `themes/` — L1 narrative themes
- `journal/` — Claude's self-review per day
- `lessons/` — lessons learned, linked to thesis & themes
- `layer-output/` — raw L0–L5 outputs archived per day
- `reviews/` — auto-generated weekly + monthly reviews
- `data/` — JSON files Claude reads programmatically (DO NOT EDIT)

## Conventions
- Wikilinks: `[[ANTM]]`, `[[nickel-ev-rebound]]`
- Tags: `#sector/nickel #setup/accumulation #layer/l2`
- Severity tags on lessons: `#severity/high`

## Search examples
- "All active thesis" → search `status: active path:thesis/`
- "All high-severity lessons last 30d" → search `#severity/high created:>2026-03-15`
- "Everything about ANTM" → click `[[ANTM]]` backlinks
```

### 5.9 Commit
`[Phase 5] First-class vault + useful journaling — pattern detection, attribution, confidence calibration, weekly/monthly auto-reviews, thesis protocol`

---

## Phase 6 — Final Indexing & Push

### 6.1 Update every CLAUDE.md

| File | Update |
|------|--------|
| `CLAUDE.md` (root) | Already lean — verify still accurate |
| `playbooks/trader/CLAUDE.md` | 6-layer system table (L0 + L1-L5), updated schedule |
| `skills/trader/CLAUDE.md` | Add L0 section, portfolio skills, update Skills Index |
| `tools/CLAUDE.md` | Add `portfolio_health.py`, updated telegram sub-commands |
| `tools/manual/telegram.md` | Add `layer0`, `intent` subcommands |

### 6.2 Verify imports still work

```bash
cd tools/trader
python3 -c "import screener, tradeplan, eval_pipeline, indicators, watchlist_4group_scan"
python3 -c "from _lib import api, broker_profile, wyckoff"
```

### 6.3 Final commit + push
```
git log --oneline main..HEAD   # review all phase commits
git push origin main
```
Ask Boss O before first push of this series.

### 6.4 Post-push summary

Write `docs/2026-04-refactor-summary.md` — what changed, what's new, what to watch for.

---

## Out of Scope (do NOT touch)

- `tools/general/*` — not trader, not this refactor
- `code/` subdirs — independent projects
- `.claude/settings.local.json` — settings only Boss O owns
- `think.py` — legacy, leave alone (flagged in tools/CLAUDE.md)
- Existing Airtable schema — propose changes but do not create tables without confirmation

---

## Checkpoint Prompts (copy-paste for the executor)

After each phase, the executor should output this to Boss O:

```
✅ Phase N done.
Changed files: [list]
New files: [list]
Archived: [list]
Next phase: [N+1, one-line description]

Proceed? [yes / pause / redirect]
```

Wait for response before the next phase.

---

## Files That Should Exist When Plan Completes

New:
- `playbooks/trader/layer-0-portfolio.md`
- `playbooks/trader/layer-5-execution.md` (renamed from execution.md)
- `skills/trader/portfolio-management.md`
- `skills/trader/sector-exposure.md`
- `skills/trader/probability-measurement.md`
- `skills/trader/money-flow-analysis.md`
- `skills/trader/portfolio-self-review.md`
- `skills/trader/thesis-drift-check.md` (restored)
- `tools/trader/portfolio_health.py`
- `.claude/commands/trade/portfolio.md`
- `vault/` (top-level Obsidian vault — full tree per Phase 5.1)
- `vault/README.md`
- `docs/coverage-matrix.md`
- `docs/2026-04-refactor-summary.md`

Deepened:
- `skills/trader/bid-offer-analysis.md` (26 → ~150 lines)
- `skills/trader/orderbook-reading.md`
- `skills/trader/whale-retail-analysis.md`
- `skills/trader/realtime-monitoring.md`
- `skills/trader/thesis-evaluation.md`
- `skills/trader/execution.md` (confidence gate)
- `skills/trader/journal-review.md`

Updated:
- `playbooks/trader/CLAUDE.md`
- `skills/trader/CLAUDE.md`
- `tools/CLAUDE.md`
- `tools/manual/telegram.md`
- `tools/trader/telegram_client.py`
- `tools/trader/cron-dispatcher.sh`
- `tools/trader/journal.py` (paths)
- `.claude/commands/trade.md`
- All L1-L4 playbooks (execution trigger section)

Archived:
- `tools/trader/archive/journal.py.bak`
- `skills/trader/archive/<old shallow versions>`
