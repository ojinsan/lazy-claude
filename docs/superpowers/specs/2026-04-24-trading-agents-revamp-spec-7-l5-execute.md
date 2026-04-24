# Spec #7 — L5 Execute (pure-Python order placement + reconcile)

**Parent:** `docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-0-master-design.md`
**PRD bible:** `vault/developer_notes/REVAMP PLAN.md`
**Prereqs:** spec #1 (core), #2 (L0), #6 (L4 — provides `plan`).

## 1. Scope & Trigger

- **Model:** **none** — pure Python, no AI. Precision matters; judgment already done by L2/L3/L4.
- **Triggers (3 paths):**
  1. **Pre-open sweep** — 08:30 WIB Mon–Fri (CRON, spec #8). Scans `lists.{superlist,exitlist}` for items with `plan is not None` and `execution is None` → places entry bid/offer.
  2. **Intraday fire** — L4 Mode B (after writing plan) calls L5 inline via `subprocess.Popen(['python', '-m', 'tools.trader.l5_run', '--ticker', t])` (no AI path). Places entry at market for BUY-NOW speed.
  3. **Reconcile cycle** — every 30m 09:00–15:00 WIB Mon–Fri (CRON). Fetches `get_orders()`, reconciles vs `execution` state per ticker, detects fills → places stop+TP legs, detects cancels/errors → Telegram alert.
- **Writes:** `lists.{superlist,exitlist}[i].execution` (new struct; see §6), `trader_status.holdings` on fill, `layer_runs['l5']`.
- **Does NOT write:** `plan` (L4 owns), `current_plan.mode`/`price` (L4 owns), `watchlist` / `regime` / `sectors` / `narratives` / `aggressiveness` / `balance.buying_power` (L0 owns).

## 2. Inputs

| Source | Field | Use |
|--------|-------|-----|
| `current_trade.json` | `lists.{superlist,exitlist}[i].{current_plan, plan, execution}` | target set + dup guard |
| `current_trade.json` | `trader_status.aggressiveness` | kill-switch gate (`off` → abort) |
| `current_trade.json` | `trader_status.holdings` | sell-order validation (must hold lots before sell) |
| `api.get_cash_balance()` | float | pre-place sanity vs notional |
| `api.get_orders(stock_code=t)` | list | dup detect, reconcile on cycle |
| `api.get_position_detail(t)` | dict | post-fill lot verification |

## 3. Outputs

### 3.1 `execution` struct (new) written per ticker

```json
{
  "status": "placed",
  "entry_order_id": "CR-12345",
  "stop_order_id": null,
  "tp1_order_id": null,
  "tp2_order_id": null,
  "fills": [],
  "last_check": "2026-04-22T08:31:05+07:00",
  "last_error": null,
  "path": "pre_open"
}
```

`status` ∈ `{pending, placed, partial, filled, cancelled, failed}`.
`path` ∈ `{pre_open, intraday, reconcile}` — which trigger created/updated the state.
`fills[]` = append-only list of `{ts, lot, price, order_id, leg}` for audit.

### 3.2 Telegram events

One message per state change:
```
[L5 place] ADMR buy 50lot @ 1855 (order CR-12345)
[L5 fill]  ADMR entry 50lot @ 1855 → placing stop@1830 + TP1@1955
[L5 error] ADMR place failed: insufficient_funds — BP 2.1M < notional 9.25M
[L5 stale] ADMR entry open 6h, no fill; cancel? (reconcile)
```

### 3.3 Daily note (EOD-aligned)

Append `## L5 Execution — {date}` with per-ticker summary: placed / filled / cancelled / failed counts + IDs.

## 4. Order Placement Logic

### 4.1 Pre-open sweep (08:30 WIB path)

For each item with `plan ≠ None` and `execution is None`:
1. Validate: `lot % 1 == 0`, `entry == round_to_tick(entry, side, 'entry')` (L4 already did this; assert).
2. Sell-side only: `holdings[t].lot >= plan.lots` (else skip + telegram warn).
3. Buy-side: `cash_balance >= plan.lots * 100 * plan.entry * 1.002` (0.2% buffer for fees).
4. `api.place_buy_order(stock_code=t, shares=plan.lots*100, price=plan.entry, order_type="LIMIT_DAY")` (or sell).
5. Write `execution = ExecutionState(status="placed", entry_order_id=resp["order_id"], path="pre_open", last_check=now_iso)`.
6. Telegram `[L5 place]`.

Stop + TP legs are NOT placed at entry time (Carina rejects conditional orders pre-fill). They are placed by the reconcile cycle when entry fills.

### 4.2 Intraday fire (L4 Mode B → L5)

Invoked with `--ticker t` arg. Pure-Python script, no playbook needed:
1. Load `current_trade`. Find item.
2. If `item.execution is not None` and `status in {placed, partial, filled}` → skip (idempotent).
3. Market-hours check (else exit 0 silently).
4. Place as **limit at best_offer** (from fresh orderbook snapshot) for speed. Fall back to `plan.entry` if orderbook stale (>5m).
5. Write `execution` with `path="intraday"`.
6. Telegram event.

### 4.3 Reconcile cycle (every 30m)

For each item with `execution is not None` and `status in {placed, partial}`:
1. `orders = api.get_orders(stock_code=t)`.
2. Find entry_order_id → read `status` field.
3. Branch:
   - **Filled** → `status="filled"`, append to `fills`. Place stop-loss at `plan.stop` (stop-order type) + TP1 at `plan.tp1` (limit). Write `stop_order_id`, `tp1_order_id`. Also update `holdings` (lot += plan.lots for buy; lot -= for sell).
   - **Partial** → `status="partial"`, append partial fill. Wait next cycle.
   - **Cancelled/Rejected** → `status="cancelled"` or `"failed"`, store `last_error`. Telegram alert.
   - **Open with stale age (>3h)** → Telegram warn ("stale, cancel?"). Do NOT auto-cancel (user decides).

Cycle also checks filled positions for stop/TP fills → update `status="closed"` (new enum) and append to holdings-exit log.

## 5. IDX-specific constraints

- Lot: always multiples of 100 shares. `plan.lots * 100` → shares param.
- Tick: L4 already rounded; L5 asserts.
- Order type: `LIMIT_DAY` (day-order, auto-cancel at EOD).
- 0.15% buy fee / 0.25% sell fee (incl. withholding tax) → used in cash-buffer check.
- Circuit breaker: if price moved >5% between plan creation and sweep, abort + telegram (stale plan).

## 6. `current_trade.py` schema addition

```python
@dataclass
class FillEvent:
    ts: str
    lot: int
    price: float
    order_id: str
    leg: str  # "entry" | "stop" | "tp1" | "tp2"

@dataclass
class ExecutionState:
    status: str = "pending"   # pending|placed|partial|filled|cancelled|failed|closed
    path: str = ""            # pre_open|intraday|reconcile
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    tp1_order_id: Optional[str] = None
    tp2_order_id: Optional[str] = None
    fills: list[FillEvent] = field(default_factory=list)
    last_check: str = ""
    last_error: Optional[str] = None

@dataclass
class ListItem:
    ticker: str
    confidence: int
    current_plan: Optional[CurrentPlan] = None
    details: str = ""
    plan: Optional[TradePlan] = None
    execution: Optional[ExecutionState] = None   # NEW
```

Back-compat: missing `execution` key → `None`.

## 7. Healthcheck gates

Pre-run aborts (telegram warn + `layer_runs['l5'].status='skipped'`):
- `aggressiveness == "off"` (kill-switch)
- Carina token expired/missing
- Pre-open sweep outside 08:00–08:45 WIB window
- Reconcile outside 09:00–15:15 WIB window
- Intraday fire with ticker not in lists OR without `plan`
- `plan.updated_at` > 24h old (stale plan guard)

## 8. Guardrails

- **Idempotency per-ticker**: `execution ≠ None` → no duplicate places. Reconcile cycle mutates status in place.
- **No auto-cancel**: stale orders → telegram warn only, Boss decides.
- **Circuit breaker**: 5% price move between plan & sweep → abort.
- **Sell blockade**: `holdings[t].lot < plan.lots` → skip with telegram.
- **Cash blockade**: cash < notional * 1.002 → skip with telegram.
- **Fill hook**: on fill, update `holdings` atomically with execution write (single `save()` call).
- **Execution never writes `plan`** — L4 owns plan; L5 reads.

## 9. Files

**Create:**
- `tools/trader/l5_synth.py` — pure helpers: validators, payload builders, reconcile decision tree, Telegram+daily-note formatters.
- `tools/trader/l5_dim_gather.py` — Carina reads (cash, orders, position) with graceful-degrade.
- `tools/trader/l5_healthcheck.py` — §7 gates.
- `tools/trader/l5_executor.py` — thin wrappers around `api.place_buy_order`, `place_sell_order`, `cancel_order`, `amend_orders`; idempotency + retry.
- `tools/trader/l5_run.py` — CLI entrypoint for intraday fire: `python -m tools.trader.l5_run --ticker ADMR`.
- `playbooks/trader/layer-5-execute.md` — for pre-open sweep + reconcile (these invoke `claude -p /trade:execute`). Intraday path skips playbook (pure Python).
- Tests + fixtures per module.

**Modify:**
- `tools/_lib/current_trade.py` — add `ExecutionState` + `FillEvent` + `ListItem.execution`.
- `.claude/commands/trade/execute.md` — replace stub.
- `playbooks/trader/CLAUDE.md` — flip L5 stub → live.
- `skills/trader/CLAUDE.md` — add L5 row.
- `docs/revamp-progress.md` — L5 tool used-by + new rows.
- `tools/INDEX.md` — add 5 L5 rows.

## 10. Task breakdown (TDD, 10 tasks)

1. **Fixtures** — Carina order/cash/position JSON samples; filled/partial/cancelled responses.
2. **Schema** — `current_trade.py` + `ExecutionState` + `FillEvent` + back-compat tests.
3. **`l5_synth.py`** — validators (`validate_plan_for_execute`), payload builders (`build_entry_payload`, `build_stop_payload`, `build_tp_payload`), circuit-breaker `check_price_drift(plan_price, live_price, pct=0.05)`.
4. **`l5_synth.py`** — reconcile decision tree (`classify_order_state(resp) → {filled|partial|open|cancelled|failed}`), stale-age detector, fills list append helper.
5. **`l5_synth.py`** — formatters (telegram events per state, daily-note block).
6. **`l5_dim_gather.py`** — cash + open orders + position detail, graceful-degrade.
7. **`l5_healthcheck.py`** — §7 gates with timezone windows, token-age check.
8. **`l5_executor.py`** — place/cancel/amend wrappers, retry w/ exponential backoff (3 tries), idempotency key from `(ticker, leg, plan_updated_at)`.
9. **`l5_run.py` + playbook + slash** — intraday CLI + pre-open/reconcile playbook + `.claude/commands/trade/execute.md` rewrite.
10. **Progress doc + INDEX + tag** — `spec-7-plan-complete`.

Deferred tasks 11–12: market-hours dry-run + accept.

## 11. Out of scope

- Conditional/bracket orders (Carina doesn't support natively; emulated via reconcile cycle).
- Margin/leverage (IDX cash-only for this system).
- After-hours trading (IDX has no post-market session for this use case).
- Order amend (use cancel + re-place if plan changes).
