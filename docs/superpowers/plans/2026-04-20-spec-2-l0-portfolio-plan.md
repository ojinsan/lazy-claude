# Spec #2 — L0 Portfolio Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build L0 portfolio-health layer: mechanical Python helpers + Claude-executed playbook that runs at CRON 03:00 WIB, writes `trader_status.{balance, pnl, holdings, aggressiveness}` + `holding.details` notes to `current_trade.json`, appends daily note, sends conditional Telegram on redflags.

**Architecture:** Path C — thin helpers in `tools/trader/l0_synth.py` for mechanical data reshaping (Carina MCP responses → dataclasses + pnl rollup). Shared `tools/_lib/daily_note.py` for daily-note appends (reused by L1/L3/L5 later). Claude-executed Markdown playbook at `playbooks/trader/layer-0-portfolio.md` orchestrates: calls helpers, feeds assembled draft to Opus for aggressiveness tier + per-holding `details` synth, writes via spec #1 `current_trade.save()`, appends daily note, conditional Telegram.

**Tech Stack:** Python 3.12 stdlib only (dataclasses, json, pathlib, datetime, unittest). No pydantic, no pytest. Spec #1 modules: `tools/_lib/current_trade.py`, `tools/_lib/claude_model.py`. Carina MCP tools `carina_cash_balance`, `carina_position_detail`, `carina_orders`. Existing `tools/trader/telegram_client.py`.

**Spec:** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`

---

## File Structure

**Create:**
- `tools/trader/l0_synth.py` — mechanical data reshaping helpers + assembler.
- `tools/_lib/daily_note.py` — shared daily-note append helper.
- `playbooks/trader/layer-0-portfolio.md` — Claude-executed playbook (step-by-step, prompts, tool-call examples).
- `tests/_lib/test_daily_note.py` — append helper tests.
- `tests/trader/__init__.py` — package marker.
- `tests/trader/test_l0_synth.py` — synth helper tests.
- `tests/trader/fixtures/__init__.py` — package marker.
- `tests/trader/fixtures/l0/carina_cash.json` — canned cash_balance response.
- `tests/trader/fixtures/l0/carina_positions.json` — canned position_detail response.
- `tests/trader/fixtures/l0/carina_orders.json` — canned orders response (mix of buy/sell, within and outside month window).
- `tests/trader/fixtures/l0/thesis_ADMR.md` — sample thesis file.
- `tests/trader/fixtures/l0/thesis_IMPC.md` — sample thesis file.

**Modify:**
- `tools/_lib/current_trade.py` — add `details: str = ""` to `Holding` dataclass (line 68–73).
- `tests/_lib/test_current_trade.py` — add round-trip test for `holding.details`.
- `.claude/commands/trade/portfolio.md` — replace stub with thin trigger.
- `playbooks/trader/CLAUDE.md` — replace stub with layer index row for L0.
- `skills/trader/CLAUDE.md` — note L0 playbook location.
- `docs/revamp-progress.md` — fill Used-by-layer for `telegram_client.py` + add rows for new `l0_synth.py`, `_lib/daily_note.py`, Carina MCP tools.

---

## Task 1: Add `details` field to `Holding` dataclass

**Files:**
- Modify: `tools/_lib/current_trade.py:67-73`
- Modify: `tests/_lib/test_current_trade.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/_lib/test_current_trade.py`:

```python
class HoldingDetailsRoundTripTest(unittest.TestCase):
    def test_details_field_round_trips(self):
        import os as _os
        import tempfile as _tmp
        with _tmp.TemporaryDirectory() as tmp:
            live = _os.path.join(tmp, "current_trade.json")
            hist = _os.path.join(tmp, "history")
            with patch.object(ct_mod, "LIVE_PATH", live), \
                 patch.object(ct_mod, "HISTORY_DIR", hist):
                ct = ct_mod.load()
                ct.trader_status.holdings.append(
                    ct_mod.Holding(
                        ticker="ADMR",
                        lot=40,
                        avg_price=1950.0,
                        current_price=1940.0,
                        pnl_pct=-0.5,
                        details="thesis-drift: supply wall unbroken 3d",
                    )
                )
                ct_mod.save(ct, layer="l0", status="ok", note="test")
                ct2 = ct_mod.load()
        self.assertEqual(len(ct2.trader_status.holdings), 1)
        self.assertEqual(
            ct2.trader_status.holdings[0].details,
            "thesis-drift: supply wall unbroken 3d",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/lazywork/workspace && python -m unittest tests._lib.test_current_trade.HoldingDetailsRoundTripTest -v`

Expected: FAIL with `TypeError: Holding.__init__() got an unexpected keyword argument 'details'` or similar.

- [ ] **Step 3: Add `details` field to `Holding` dataclass**

Edit `tools/_lib/current_trade.py` lines 67–73:

```python
@dataclass
class Holding:
    ticker: str
    lot: int
    avg_price: float
    current_price: float
    pnl_pct: float
    details: str = ""
```

Also locate `_parse_trader_status` (or equivalent holdings parser) in the same file and ensure `details` is read when loading JSON. If the parser uses `**row` or `asdict`-based round-trip, no change needed — verify.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/lazywork/workspace && python -m unittest tests._lib.test_current_trade.HoldingDetailsRoundTripTest -v`

Expected: PASS. Also run full spec #1 suite to confirm no regression: `python -m unittest discover -s tests/_lib -v` — all prior tests still pass.

- [ ] **Step 5: Commit**

```bash
git add tools/_lib/current_trade.py tests/_lib/test_current_trade.py
git commit -m "Add details field to Holding dataclass for L0 notes"
```

---

## Task 2: Shared daily-note append helper

**Files:**
- Create: `tools/_lib/daily_note.py`
- Create: `tests/_lib/test_daily_note.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/_lib/test_daily_note.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

from tools._lib import daily_note as dn


class AppendCreatesFileIfMissingTest(unittest.TestCase):
    def test_creates_file_with_header_then_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dn, "VAULT_DAILY_DIR", tmp):
                dn.append_section(
                    date_str="2026-04-20",
                    section_heading="L0 — 03:00",
                    body="Balance Rp 19.6M. Aggressiveness: defensive.",
                )
                path = os.path.join(tmp, "2026-04-20.md")
                self.assertTrue(os.path.exists(path))
                with open(path) as f:
                    content = f.read()
        self.assertIn("# 2026-04-20", content)
        self.assertIn("## Auto-Appended", content)
        self.assertIn("### L0 — 03:00", content)
        self.assertIn("Balance Rp 19.6M. Aggressiveness: defensive.", content)


class AppendPreservesExistingContentTest(unittest.TestCase):
    def test_existing_sections_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(dn, "VAULT_DAILY_DIR", tmp):
                existing = "# 2026-04-20\n\n## Auto-Appended\n\n### L0 — 03:00\nold body\n"
                path = os.path.join(tmp, "2026-04-20.md")
                with open(path, "w") as f:
                    f.write(existing)
                dn.append_section(
                    date_str="2026-04-20",
                    section_heading="L1 — 04:00",
                    body="Regime: cautious.",
                )
                with open(path) as f:
                    content = f.read()
        self.assertIn("### L0 — 03:00\nold body", content)
        self.assertIn("### L1 — 04:00\nRegime: cautious.", content)
        # L0 section appears before L1 section (chronological)
        self.assertLess(content.index("### L0 — 03:00"), content.index("### L1 — 04:00"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/lazywork/workspace && python -m unittest tests._lib.test_daily_note -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tools._lib.daily_note'`.

- [ ] **Step 3: Create the module**

Create `tools/_lib/daily_note.py`:

```python
"""Shared daily-note append helper. Used by L0 now, L1/L3/L5 later.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md §3.2.
"""
from __future__ import annotations

import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
VAULT_DAILY_DIR = str(WORKSPACE / "vault" / "daily")


def append_section(date_str: str, section_heading: str, body: str) -> str:
    """Append a `### {section_heading}` block under `## Auto-Appended` in
    vault/daily/{date_str}.md. Create file with header if missing.

    Returns absolute path to the file.
    """
    path = os.path.join(VAULT_DAILY_DIR, f"{date_str}.md")
    os.makedirs(VAULT_DAILY_DIR, exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {date_str}\n\n## Auto-Appended\n\n")

    with open(path, "a", encoding="utf-8") as f:
        f.write(f"### {section_heading}\n{body}\n\n")

    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/lazywork/workspace && python -m unittest tests._lib.test_daily_note -v`

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/_lib/daily_note.py tests/_lib/test_daily_note.py
git commit -m "Add shared daily_note.append_section helper"
```

---

## Task 3: L0 test fixtures

**Files:**
- Create: `tests/trader/__init__.py`
- Create: `tests/trader/fixtures/__init__.py`
- Create: `tests/trader/fixtures/l0/carina_cash.json`
- Create: `tests/trader/fixtures/l0/carina_positions.json`
- Create: `tests/trader/fixtures/l0/carina_orders.json`
- Create: `tests/trader/fixtures/l0/thesis_ADMR.md`
- Create: `tests/trader/fixtures/l0/thesis_IMPC.md`

- [ ] **Step 1: Create empty `__init__.py` package markers**

```bash
mkdir -p /home/lazywork/workspace/tests/trader/fixtures/l0
touch /home/lazywork/workspace/tests/trader/__init__.py
touch /home/lazywork/workspace/tests/trader/fixtures/__init__.py
```

- [ ] **Step 2: Write `carina_cash.json`**

Create `tests/trader/fixtures/l0/carina_cash.json`. Shape mirrors what Carina MCP `carina_cash_balance` typically returns — values in IDR as floats:

```json
{
  "cash": 19612924.64,
  "buying_power": 19612924.64,
  "currency": "IDR",
  "as_of": "2026-04-20T03:00:00+07:00"
}
```

> Note: actual Carina response shape must be validated during playbook dry-run (§8.4 of spec). If shape differs, adjust synth parser + fixture together.

- [ ] **Step 3: Write `carina_positions.json`**

Create `tests/trader/fixtures/l0/carina_positions.json`. Two holdings, one underwater (ADMR) and one profitable (IMPC):

```json
{
  "positions": [
    {
      "ticker": "ADMR",
      "lot": 40,
      "avg_price": 1950.0,
      "current_price": 1940.0,
      "unrealized_pnl": -40000.0,
      "pnl_pct": -0.51
    },
    {
      "ticker": "IMPC",
      "lot": 20,
      "avg_price": 1200.0,
      "current_price": 1250.0,
      "unrealized_pnl": 100000.0,
      "pnl_pct": 4.17
    }
  ]
}
```

- [ ] **Step 4: Write `carina_orders.json`**

Create `tests/trader/fixtures/l0/carina_orders.json`. Mix of statuses and dates — one filled sell in current month (contributes to MtD), one filled sell last month (contributes to YtD only), one cancelled:

```json
{
  "orders": [
    {
      "order_id": "O-2026-04-15-001",
      "ticker": "BUMI",
      "side": "sell",
      "status": "filled",
      "lot": 50,
      "avg_fill_price": 180.0,
      "realized_pnl": -125000.0,
      "filled_at": "2026-04-15T10:30:00+07:00"
    },
    {
      "order_id": "O-2026-03-20-007",
      "ticker": "AADI",
      "side": "sell",
      "status": "filled",
      "lot": 30,
      "avg_fill_price": 8500.0,
      "realized_pnl": 1325000.0,
      "filled_at": "2026-03-20T14:15:00+07:00"
    },
    {
      "order_id": "O-2026-04-18-003",
      "ticker": "ADMR",
      "side": "buy",
      "status": "cancelled",
      "lot": 20,
      "avg_fill_price": 0,
      "realized_pnl": 0,
      "filled_at": null
    }
  ]
}
```

- [ ] **Step 5: Write thesis samples**

Create `tests/trader/fixtures/l0/thesis_ADMR.md`:

```markdown
# ADMR — coal exporter, China winter restock play

**Entry:** 1950 on 2026-04-02
**Invalidation:** close < 1820 for 2 days OR supply wall at 1985 unbroken for 10d
**Target:** 2150 (consensus EPS upgrade tier)
**Thesis:** coal prices firming on China heating demand + weak rupiah tailwind. ADMR has strongest margin leverage in group.
```

Create `tests/trader/fixtures/l0/thesis_IMPC.md`:

```markdown
# IMPC — property / cement recovery

**Entry:** 1200 on 2026-03-28
**Invalidation:** close < 1130 or BI rate hike surprise
**Target:** 1350
**Thesis:** BI rate hold + Lebaran construction restock benefits cement margin.
```

- [ ] **Step 6: Commit**

```bash
git add tests/trader/__init__.py tests/trader/fixtures/__init__.py tests/trader/fixtures/l0/
git commit -m "Add L0 test fixtures: carina responses + thesis samples"
```

---

## Task 4: `l0_synth.balance_from_cash`

**Files:**
- Create: `tools/trader/l0_synth.py`
- Create: `tests/trader/test_l0_synth.py`

- [ ] **Step 1: Write the failing test**

Create `tests/trader/test_l0_synth.py`:

```python
import json
import os
import unittest
from pathlib import Path

from tools._lib import current_trade as ct
from tools.trader import l0_synth

FIXTURES = Path(__file__).parent / "fixtures" / "l0"


def _load(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


class BalanceFromCashTest(unittest.TestCase):
    def test_parses_cash_and_buying_power(self):
        resp = _load("carina_cash.json")
        balance = l0_synth.balance_from_cash(resp)
        self.assertIsInstance(balance, ct.Balance)
        self.assertEqual(balance.cash, 19612924.64)
        self.assertEqual(balance.buying_power, 19612924.64)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'tools.trader.l0_synth'`.

- [ ] **Step 3: Create `l0_synth.py` with `balance_from_cash`**

Create `tools/trader/l0_synth.py`:

```python
"""L0 mechanical data reshaping helpers.

Pure functions — no AI, no I/O, no side effects. Carina MCP responses
(plain dicts from tool calls) → spec #1 dataclasses. The playbook
orchestrates calls and feeds assembled TraderStatus draft to Opus for
aggressiveness tier + per-holding details synth.

See docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md.
"""
from __future__ import annotations

from tools._lib.current_trade import Balance


def balance_from_cash(carina_cash: dict) -> Balance:
    """Parse Carina cash_balance response into Balance dataclass.

    Expected keys: `cash` (float, IDR), `buying_power` (float, IDR).
    """
    return Balance(
        cash=float(carina_cash["cash"]),
        buying_power=float(carina_cash["buying_power"]),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.BalanceFromCashTest -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/trader/l0_synth.py tests/trader/test_l0_synth.py
git commit -m "Add l0_synth.balance_from_cash"
```

---

## Task 5: `l0_synth.holdings_from_positions`

**Files:**
- Modify: `tools/trader/l0_synth.py`
- Modify: `tests/trader/test_l0_synth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/trader/test_l0_synth.py`:

```python
class HoldingsFromPositionsTest(unittest.TestCase):
    def test_parses_each_position_into_holding(self):
        resp = _load("carina_positions.json")
        holdings = l0_synth.holdings_from_positions(resp)
        self.assertEqual(len(holdings), 2)

        admr = next(h for h in holdings if h.ticker == "ADMR")
        self.assertEqual(admr.lot, 40)
        self.assertEqual(admr.avg_price, 1950.0)
        self.assertEqual(admr.current_price, 1940.0)
        self.assertAlmostEqual(admr.pnl_pct, -0.51)
        self.assertEqual(admr.details, "")

        impc = next(h for h in holdings if h.ticker == "IMPC")
        self.assertEqual(impc.lot, 20)
        self.assertAlmostEqual(impc.pnl_pct, 4.17)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.HoldingsFromPositionsTest -v`

Expected: FAIL with `AttributeError: module 'tools.trader.l0_synth' has no attribute 'holdings_from_positions'`.

- [ ] **Step 3: Add `holdings_from_positions`**

Append to `tools/trader/l0_synth.py`:

```python
from tools._lib.current_trade import Holding


def holdings_from_positions(carina_positions: dict) -> list[Holding]:
    """Parse Carina position_detail response into list[Holding].

    Expected shape: `{"positions": [{ticker, lot, avg_price, current_price, pnl_pct, ...}, ...]}`.
    `details` always starts empty; playbook fills via Opus.
    """
    out: list[Holding] = []
    for p in carina_positions.get("positions", []):
        out.append(
            Holding(
                ticker=str(p["ticker"]),
                lot=int(p["lot"]),
                avg_price=float(p["avg_price"]),
                current_price=float(p["current_price"]),
                pnl_pct=float(p["pnl_pct"]),
                details="",
            )
        )
    return out
```

Also add `from tools._lib.current_trade import Holding` next to the existing `Balance` import (or merge into a single line).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.HoldingsFromPositionsTest -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/trader/l0_synth.py tests/trader/test_l0_synth.py
git commit -m "Add l0_synth.holdings_from_positions"
```

---

## Task 6: `l0_synth.pnl_rollup_from_orders`

**Files:**
- Modify: `tools/trader/l0_synth.py`
- Modify: `tests/trader/test_l0_synth.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/trader/test_l0_synth.py`:

```python
import datetime as dt
from tools._lib.current_trade import PnL


class PnLRollupFromOrdersTest(unittest.TestCase):
    def test_sums_filled_sells_in_current_month_for_mtd(self):
        resp = _load("carina_orders.json")
        # today = 2026-04-20 → April window
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=0.0, ytd=0.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        # Only the 2026-04-15 BUMI sell counts for MtD (-125000).
        self.assertEqual(pnl.mtd, -125000.0)
        # YtD = MtD + 2026-03-20 AADI sell (1325000) = 1200000.
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_empty_window_falls_back_to_prior_values(self):
        resp = {"orders": []}
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=-250000.0, ytd=1200000.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        self.assertEqual(pnl.mtd, -250000.0)
        self.assertEqual(pnl.ytd, 1200000.0)

    def test_cancelled_orders_excluded(self):
        resp = _load("carina_orders.json")
        today = dt.date(2026, 4, 20)
        prior = PnL(realized=0.0, unrealized=0.0, mtd=0.0, ytd=0.0)
        pnl = l0_synth.pnl_rollup_from_orders(resp, prior_pnl=prior, today=today)
        # Cancelled ADMR order on 2026-04-18 must not change MtD.
        self.assertEqual(pnl.mtd, -125000.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.PnLRollupFromOrdersTest -v`

Expected: FAIL with `AttributeError: module 'tools.trader.l0_synth' has no attribute 'pnl_rollup_from_orders'`.

- [ ] **Step 3: Add `pnl_rollup_from_orders`**

Append to `tools/trader/l0_synth.py`:

```python
import datetime as _dt
from tools._lib.current_trade import PnL


def pnl_rollup_from_orders(
    carina_orders: dict,
    prior_pnl: PnL,
    today: _dt.date,
) -> PnL:
    """Sum realized PnL across filled sell orders within month/year window.

    If the window is empty (Carina did not return orders spanning the period),
    fall back to `prior_pnl.mtd` / `prior_pnl.ytd` verbatim. `realized_today`
    is left at 0 (L0 runs pre-market; L5 fills during the day).

    Only filled orders with a truthy `filled_at` timestamp contribute. Cancelled
    or unfilled orders are ignored.
    """
    mtd = 0.0
    ytd = 0.0
    mtd_had_row = False
    ytd_had_row = False

    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    for o in carina_orders.get("orders", []):
        if o.get("status") != "filled":
            continue
        filled_at = o.get("filled_at")
        if not filled_at:
            continue
        # ISO8601 with offset — take the date portion only.
        filled_date = _dt.date.fromisoformat(filled_at[:10])
        realized = float(o.get("realized_pnl") or 0.0)

        if filled_date >= year_start:
            ytd += realized
            ytd_had_row = True
            if filled_date >= month_start:
                mtd += realized
                mtd_had_row = True

    return PnL(
        realized=0.0,
        unrealized=prior_pnl.unrealized,  # unrealized is set by holdings merge elsewhere
        mtd=mtd if mtd_had_row else prior_pnl.mtd,
        ytd=ytd if ytd_had_row else prior_pnl.ytd,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.PnLRollupFromOrdersTest -v`

Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/trader/l0_synth.py tests/trader/test_l0_synth.py
git commit -m "Add l0_synth.pnl_rollup_from_orders with window + fallback"
```

---

## Task 7: `l0_synth.assemble_trader_status_draft`

**Files:**
- Modify: `tools/trader/l0_synth.py`
- Modify: `tests/trader/test_l0_synth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/trader/test_l0_synth.py`:

```python
from tools._lib.current_trade import TraderStatus


class AssembleTraderStatusDraftTest(unittest.TestCase):
    def test_combines_balance_holdings_pnl_leaves_judgment_fields_empty(self):
        cash = _load("carina_cash.json")
        positions = _load("carina_positions.json")
        orders = _load("carina_orders.json")
        today = dt.date(2026, 4, 20)
        prior = TraderStatus()  # regime="", aggressiveness="", blank PnL

        draft = l0_synth.assemble_trader_status_draft(
            carina_cash=cash,
            carina_positions=positions,
            carina_orders=orders,
            prior_status=prior,
            today=today,
        )

        self.assertIsInstance(draft, TraderStatus)
        # Balance populated.
        self.assertEqual(draft.balance.cash, 19612924.64)
        # Holdings populated, details left empty for Opus.
        self.assertEqual(len(draft.holdings), 2)
        self.assertTrue(all(h.details == "" for h in draft.holdings))
        # PnL rolled up.
        self.assertEqual(draft.pnl.mtd, -125000.0)
        self.assertEqual(draft.pnl.ytd, 1200000.0)
        # Unrealized = sum of position unrealized_pnl fields.
        self.assertAlmostEqual(draft.pnl.unrealized, 60000.0)  # -40000 + 100000
        # Judgment fields untouched — Opus fills later.
        self.assertEqual(draft.aggressiveness, "")
        # Regime/sectors/narratives remain whatever prior was (L0 does not write).
        self.assertEqual(draft.regime, prior.regime)
        self.assertEqual(draft.sectors, prior.sectors)
        self.assertEqual(draft.narratives, prior.narratives)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth.AssembleTraderStatusDraftTest -v`

Expected: FAIL with `AttributeError: module 'tools.trader.l0_synth' has no attribute 'assemble_trader_status_draft'`.

- [ ] **Step 3: Add assembler + unrealized summation**

Append to `tools/trader/l0_synth.py`:

```python
from tools._lib.current_trade import TraderStatus


def _sum_unrealized(carina_positions: dict) -> float:
    return sum(
        float(p.get("unrealized_pnl") or 0.0)
        for p in carina_positions.get("positions", [])
    )


def assemble_trader_status_draft(
    carina_cash: dict,
    carina_positions: dict,
    carina_orders: dict,
    prior_status: TraderStatus,
    today: _dt.date,
) -> TraderStatus:
    """Build a TraderStatus with mechanical fields filled (balance, pnl, holdings).
    Judgment fields (aggressiveness, holding.details) are left at spec-#1 defaults
    for the Claude playbook to synthesize via Opus. L1-owned fields
    (regime, sectors, narratives) are carried over from `prior_status` unchanged.
    """
    balance = balance_from_cash(carina_cash)
    holdings = holdings_from_positions(carina_positions)

    prior_pnl = prior_status.pnl
    pnl = pnl_rollup_from_orders(carina_orders, prior_pnl=prior_pnl, today=today)
    pnl.unrealized = _sum_unrealized(carina_positions)

    draft = TraderStatus(
        regime=prior_status.regime,
        aggressiveness="",  # Opus fills from playbook
        sectors=list(prior_status.sectors),
        narratives=list(prior_status.narratives),
        balance=balance,
        pnl=pnl,
        holdings=holdings,
    )
    return draft
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/lazywork/workspace && python -m unittest tests.trader.test_l0_synth -v`

Expected: all l0_synth tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/trader/l0_synth.py tests/trader/test_l0_synth.py
git commit -m "Add l0_synth.assemble_trader_status_draft wrapper"
```

---

## Task 8: Write L0 playbook

**Files:**
- Create: `playbooks/trader/layer-0-portfolio.md`

- [ ] **Step 1: Create the playbook**

Create `playbooks/trader/layer-0-portfolio.md`:

````markdown
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

## Step 2 — Fetch Carina snapshots

Call MCP tools in parallel:

- `mcp__lazytools__carina_cash_balance` → `cash_resp`
- `mcp__lazytools__carina_position_detail` → `positions_resp`
- `mcp__lazytools__carina_orders` with date range covering the current year (inclusive of today) → `orders_resp`

Retry each up to 3 times with 2s backoff on 5xx/timeout. If any still fails after retries: `ct.save(ct_prior, layer="l0", status="error", note="carina unreachable: <which>")`, send Telegram alert, exit. Do NOT write partial `trader_status`.

## Step 3 — Assemble mechanical draft

```python
import datetime as dt
from tools.trader import l0_synth

today_wib = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
draft = l0_synth.assemble_trader_status_draft(
    carina_cash=cash_resp,
    carina_positions=positions_resp,
    carina_orders=orders_resp,
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
    telegram_client.send("\n".join(lines))
```

Silent when zero redflags.

## Guardrails

- Never write orders, never cancel orders.
- Never write to `regime`, `sectors`, `narratives`, `superlist`, `exitlist`.
- If any step before Step 6 fails, keep previous `trader_status` untouched (already on disk).
- Idempotent: a second run at the same date creates a new `l0-HHMM.json` snapshot and appends a new `### L0 — HH:MM` section.
````

- [ ] **Step 2: Commit**

```bash
git add playbooks/trader/layer-0-portfolio.md
git commit -m "Add L0 portfolio playbook — orchestrator for /trade:portfolio"
```

---

## Task 9: Replace `/trade:portfolio` stub with thin trigger

**Files:**
- Modify: `.claude/commands/trade/portfolio.md`

- [ ] **Step 1: Write the thin trigger**

Replace `.claude/commands/trade/portfolio.md` contents:

```markdown
# /trade:portfolio — L0 Portfolio Analysis

Run the L0 layer: read Carina balance/positions/orders, compute pnl rollup, synthesize aggressiveness + per-holding thesis drift notes with Opus, write `trader_status.{balance, pnl, holdings, aggressiveness}` via `current_trade.save()`, append daily note, alert Telegram on redflags.

Load playbook and follow it exactly:

**Playbook:** `playbooks/trader/layer-0-portfolio.md`

**Spec:** `docs/superpowers/specs/2026-04-20-trading-agents-revamp-spec-2-l0-portfolio.md`

Guardrails (see playbook §Guardrails): no order writes, no regime/list writes, keep previous state on error.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/trade/portfolio.md
git commit -m "Replace /trade:portfolio stub with thin trigger"
```

---

## Task 10: Update trader index docs + progress tracker

**Files:**
- Modify: `playbooks/trader/CLAUDE.md`
- Modify: `skills/trader/CLAUDE.md`
- Modify: `docs/revamp-progress.md`

- [ ] **Step 1: Replace `playbooks/trader/CLAUDE.md` stub with layer index**

Replace contents:

```markdown
# Trader Playbooks — Layer Index

Each layer has one combined skill+workflow playbook. Slash command under `.claude/commands/trade/` is a thin trigger that loads the playbook.

| Layer | Playbook | Slash | Status |
|-------|----------|-------|--------|
| L0 Portfolio | `layer-0-portfolio.md` | `/trade:portfolio` | live |
| L1 Insight | stub — spec #3 | `/trade:insight` | stub |
| L2 Screening | stub — spec #4 | `/trade:screening` | stub |
| L3 Monitoring | stub — spec #5 | `/trade:monitor` | stub |
| L4 Tradeplan | stub — spec #6 | `/trade:tradeplan` | stub |
| L5 Execute | stub — spec #7 | `/trade:execute` | stub |

Master design: `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`.
Old version archived at `archive/playbooks/trader/`.
```

- [ ] **Step 2: Update `skills/trader/CLAUDE.md`**

Append after the existing stub content:

```markdown
## Active layer playbooks

| Layer | Playbook |
|-------|----------|
| L0 Portfolio | `playbooks/trader/layer-0-portfolio.md` |
```

If the stub is too bare (e.g. just "stub"), rewrite to the minimal form above with pointer to `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md` for philosophy.

- [ ] **Step 3: Update `docs/revamp-progress.md`**

In the `tools/trader/*.py — Used By` table, fill `Used-by-layer` column:

- `telegram_client.py` → `L0`

Add two new rows (alphabetically sorted into the table):

- `l0_synth.py` | `L0` | `live` | `mechanical data reshaping for L0 playbook`

In a new `## External MCP tools (used-by-layer)` section after the existing `## Archived references` section:

```markdown
## External MCP tools (used-by-layer)

| MCP tool | Used-by-layer | Notes |
|----------|---------------|-------|
| `mcp__lazytools__carina_cash_balance` | L0 | live balance input |
| `mcp__lazytools__carina_position_detail` | L0 | live holdings input |
| `mcp__lazytools__carina_orders` | L0 | MtD/YtD rollup input |
```

In a new `## tools/_lib/*.py` section right before the `tools/trader/*.py` section:

```markdown
## `tools/_lib/*.py` — Used By

| Tool | Used-by-layer | Status | Notes |
|------|---------------|--------|-------|
| `current_trade.py` | L0, L1, L2, L3, L4, L5 | live | spec #1 — shared schema + save/load |
| `ratelimit.py` | L2, L3, L5 | live | spec #1 — token buckets |
| `claude_model.py` | L0, L1, L2, L4 | live | spec #1 — Opus↔openclaude fallback |
| `daily_note.py` | L0 (L1/L3/L5 later) | live | spec #2 — shared daily-note append |
```

Update the `## Spec status` row for spec #2 from `not started` to `design+plan locked, executing`. Once this plan finishes, the final commit will flip it to `complete`.

- [ ] **Step 4: Commit**

```bash
git add docs/revamp-progress.md playbooks/trader/CLAUDE.md skills/trader/CLAUDE.md
git commit -m "Update trader indexes + progress tracker for L0"
```

---

## Task 11: Full test suite run + smoke import check

**Files:** none (verification only)

- [ ] **Step 1: Run every test**

```bash
cd /home/lazywork/workspace
python -m unittest discover -s tests -v
```

Expected: all tests under `tests/_lib/` and `tests/trader/` pass. No failures, no errors.

- [ ] **Step 2: Smoke import the synth module directly**

```bash
cd /home/lazywork/workspace
python -c "from tools.trader import l0_synth; from tools._lib import daily_note, current_trade; print('imports ok:', l0_synth.assemble_trader_status_draft.__name__, daily_note.append_section.__name__)"
```

Expected output:

```
imports ok: assemble_trader_status_draft append_section
```

- [ ] **Step 3: Tag the plan as done**

```bash
git tag -a spec-2-plan-complete -m "L0 helpers + playbook in place; manual dry-run pending"
```

---

## Task 12: Manual dry-run checklist (spec §8.4)

**Files:** none (acceptance only — Claude runs `/trade:portfolio` interactively, user inspects outputs)

- [ ] **Step 1: Trigger `/trade:portfolio` in a dry run**

Boss O invokes `/trade:portfolio` during a non-CRON window. Claude follows `playbooks/trader/layer-0-portfolio.md`. Verify during the run:

- Carina MCP responses look as expected (compare against fixture shapes — adjust fixtures + synth parsers together if divergent).
- No partial `trader_status` is written when any step fails.
- Opus returns an aggressiveness tier in the 5-literal set.
- Every `holding.details` starts with one of: `redflag:`, `thesis-drift:`, `thesis-on-track:`, `no thesis:`.
- Telegram sends iff ≥1 redflag holding; silent otherwise.
- `vault/daily/YYYY-MM-DD.md` gains a `### L0 — HH:MM` section.
- `runtime/current_trade.json` shows `layer_runs.l0.status = "ok"`, version bumped.
- `runtime/history/YYYY-MM-DD/l0-HHMM.json` snapshot exists.

- [ ] **Step 2: If Carina response shape differs from fixtures, update both**

When the real MCP response has different keys (e.g., positions under `data.positions` instead of `positions`), update the synth parser AND the corresponding fixture JSON in the same commit. Re-run synth unit tests. Document the shape in a comment at the top of `l0_synth.py`.

- [ ] **Step 3: Mark spec #2 complete in progress tracker**

Once the dry-run checklist passes cleanly, flip `docs/revamp-progress.md` spec status row for #2 from `design+plan locked, executing` to `complete`.

```bash
git add docs/revamp-progress.md
git commit -m "Mark spec #2 L0 complete after dry-run"
git tag -a spec-2-complete -m "L0 portfolio layer live"
```

---

## Self-Review Notes

**Spec coverage:**
- §1 Scope & Trigger → covered by playbook step-by-step + thin trigger (Tasks 8, 9).
- §2 Inputs → Carina MCP tools (Task 8 playbook Step 2), thesis files (Task 8 playbook Step 4), prior `current_trade` (Task 8 Step 1).
- §3.1 trader_status fields → synth helpers (Tasks 4–7) + playbook Opus synthesis (Task 8 Steps 4, 5).
- §3.2 Daily note append → `daily_note.py` (Task 2) + playbook Step 7 (Task 8).
- §3.3 Telegram conditional → playbook Step 8 (Task 8).
- §3.4 `layer_runs.l0` → playbook Step 6 via `ct.save()` (Task 8).
- §4.1/4.2/4.3/4.4 Files → Tasks 1–10.
- §5 Aggressiveness Logic → playbook Step 5 (Task 8).
- §6 Thesis drift + Redflag → playbook Step 4 (Task 8).
- §7 Error Handling → playbook Guardrails + Step 2 retry + Step 4/5 validation (Task 8).
- §8 Testing → Tasks 1–7 for unit tests; Task 12 for manual dry-run.

**Placeholder scan:** none — every code block is concrete. No "TBD" / "TODO" / "implement later".

**Type consistency:** `Balance`, `PnL`, `Holding`, `TraderStatus` all from `tools._lib.current_trade` (spec #1 dataclasses). `l0_synth` function signatures declared once in Task 4, extended in Tasks 5–7 — names match (`balance_from_cash`, `holdings_from_positions`, `pnl_rollup_from_orders`, `assemble_trader_status_draft`). `append_section(date_str, section_heading, body)` signature stable from Task 2 through Task 8.

**Known limitation (explicit):** Fixture JSON shapes are educated guesses. Task 12 Step 2 explicitly allows adjusting fixtures + parsers together if the real MCP response shape differs. This is the acceptable cost of not having a live Carina session available at plan-write time.
