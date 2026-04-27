# Layer 5 — Execute Playbook

**Spec:** `docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-7-l5-execute.md`
**Model:** none — pure Python dispatch only. No AI judgment here.

This playbook is invoked by `/trade:execute` for:
1. **Pre-open sweep (08:30 WIB)** — place entry orders for all planned tickers.
2. **Reconcile (every 30m, 09:00–15:00 WIB)** — detect fills → place stop+TP; detect stale/cancelled → alert.

The intraday fire path (L4 Mode B → L5) runs `python -m tools.trader.l5_run --ticker T` directly and does NOT use this playbook.

---

## Step 1 — Identify path

Check current WIB time:
- 08:00–08:45 → **pre-open sweep**
- 09:00–15:15 → **reconcile**
- Otherwise → abort (log, no telegram)

```python
from tools.trader.l5_healthcheck import check
from tools._lib import current_trade as ct_mod
import datetime as _dt

WIB = _dt.timezone(_dt.timedelta(hours=7))
now = _dt.datetime.now(WIB)
ct = ct_mod.load()

# Determine path from time
hour = now.hour
if 8 <= hour < 9:
    path = "pre_open"
elif 9 <= hour < 16:
    path = "reconcile"
else:
    print("outside L5 windows — exit")
    exit(0)

hc = check(ct, path, now=now)
if not hc["ok"]:
    # send telegram warn, mark skipped
    from tools.trader.telegram_client import send_message
    send_message(f"⚠️ <b>L5 skip</b> — {hc['reason']}")
    ct_mod.save(ct, "l5", "skipped", note=hc["reason"])
    exit(0)
```

---

## Step 2A — Pre-open sweep

For each item in `superlist + exitlist` where `plan is not None` and `execution is None`:

```python
from tools.trader.l5_synth import (
    validate_plan_for_execute, check_price_drift,
    check_cash_sufficient, check_holdings_sufficient,
    fmt_place_event, fmt_error_event, fmt_circuit_breaker_event,
)
from tools.trader.l5_dim_gather import gather_cash_balance
from tools.trader.l5_executor import place_entry
from tools._lib.current_trade import ExecutionState
from tools.trader.telegram_client import send_message
import datetime as _dt

now_iso = now.replace(microsecond=0).isoformat()
events = []

for lst in (ct.lists.superlist, ct.lists.exitlist):
    for item in lst:
        if item.plan is None or item.execution is not None:
            continue

        ticker = item.ticker
        plan = item.plan
        side = "sell" if (item.current_plan and item.current_plan.mode == "sell_at_price") else "buy"

        # Validate plan
        err = validate_plan_for_execute(plan, side)
        if err:
            msg = fmt_error_event(ticker, err)
            send_message(msg)
            events.append(msg)
            continue

        # Cash / holdings gate
        if side == "buy":
            cash = gather_cash_balance()
            if not check_cash_sufficient(cash or 0, plan.lots, plan.entry):
                notional = plan.lots * 100 * plan.entry
                msg = fmt_error_event(ticker, "insufficient_funds",
                                      cash=cash or 0, notional=notional)
                send_message(msg)
                events.append(msg)
                continue
        else:
            holdings_lot = next((h.lot for h in ct.trader_status.holdings
                                 if h.ticker == ticker), 0)
            if not check_holdings_sufficient(holdings_lot, plan.lots):
                msg = fmt_error_event(ticker,
                                      f"sell_blockade: hold {holdings_lot}lot < plan {plan.lots}lot")
                send_message(msg)
                events.append(msg)
                continue

        # Place entry
        resp = place_entry(ticker, side, plan.lots * 100, plan.entry)
        if resp.get("error"):
            msg = fmt_error_event(ticker, resp["error"])
            send_message(msg)
            events.append(msg)
            continue

        order_id = resp["order_id"]
        item.execution = ExecutionState(
            status="placed",
            path="pre_open",
            entry_order_id=order_id,
            last_check=now_iso,
        )
        msg = fmt_place_event(ticker, side, plan.lots, plan.entry, order_id)
        send_message(msg)
        events.append(msg)
```

---

## Step 2B — Reconcile cycle

For each item where `execution is not None` and `status in {placed, partial}`:

```python
from tools.trader.l5_synth import (
    classify_order_state, is_order_stale, append_fill,
    fmt_fill_event, fmt_stale_event, fmt_error_event,
)
from tools.trader.l5_dim_gather import gather_orders
from tools.trader.l5_executor import place_stop, place_tp

for lst in (ct.lists.superlist, ct.lists.exitlist):
    for item in lst:
        ex = item.execution
        if ex is None or ex.status not in ("placed", "partial"):
            continue

        ticker = item.ticker
        plan = item.plan
        side = "sell" if (item.current_plan and item.current_plan.mode == "sell_at_price") else "buy"
        orders = gather_orders(ticker)

        # Find entry order
        entry_order = next((o for o in orders
                            if o.get("order_id") == ex.entry_order_id), None)
        if entry_order is None:
            ex.last_check = now_iso
            continue

        state = classify_order_state(entry_order)

        if state == "filled":
            append_fill(ex, entry_order, "entry")
            ex.status = "filled"
            ex.last_check = now_iso

            # Place stop + TP1
            stop_resp = place_stop(ticker, side, plan.lots * 100, plan.stop)
            if not stop_resp.get("error"):
                ex.stop_order_id = stop_resp["order_id"]

            tp_resp = place_tp(ticker, side, plan.lots * 100, plan.tp1)
            if not tp_resp.get("error"):
                ex.tp1_order_id = tp_resp["order_id"]

            # Update holdings
            for h in ct.trader_status.holdings:
                if h.ticker == ticker:
                    if side == "buy":
                        h.lot += plan.lots
                    else:
                        h.lot -= plan.lots
                    break

            msg = fmt_fill_event(ticker, plan.lots,
                                 entry_order.get("avg_fill_price", plan.entry),
                                 plan.stop, plan.tp1)
            send_message(msg)
            events.append(msg)

        elif state == "partial":
            append_fill(ex, entry_order, "entry")
            ex.status = "partial"
            ex.last_check = now_iso

        elif state in ("cancelled", "failed"):
            ex.status = state
            ex.last_error = entry_order.get("reject_reason", state)
            ex.last_check = now_iso
            msg = fmt_error_event(ticker, ex.last_error or state)
            send_message(msg)
            events.append(msg)

        elif state == "open":
            if is_order_stale(entry_order, stale_hours=3.0, now=now):
                age_h = (now - _dt.datetime.fromisoformat(
                    entry_order["created_at"])).total_seconds() / 3600
                msg = fmt_stale_event(ticker, age_h)
                send_message(msg)
                events.append(msg)
            ex.last_check = now_iso
```

---

## Step 3 — Save + daily note

```python
from tools.trader.l5_synth import fmt_daily_note_block
from tools._lib.daily_note import append as append_note
import datetime as _dt

ct_mod.save(ct, "l5", "ok", note=f"{path}:{len(events)} events")

if events:
    date_str = now.strftime("%Y-%m-%d")
    block = fmt_daily_note_block(date_str, events)
    append_note(block)
```

---

## Guardrails

- **Idempotency**: `execution is not None` → skip pre-open place. Reconcile mutates status in place.
- **No auto-cancel**: stale orders → telegram warn only. Boss decides.
- **Fill hook**: holdings updated atomically in same `save()` call as execution write.
- **Execution never writes `plan`** — L4 owns plan; L5 reads.
- **Circuit breaker**: if needed, call `check_price_drift(plan.entry, live_price)` before place.
