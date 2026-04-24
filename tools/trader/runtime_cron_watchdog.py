"""Cron watchdog: scan today's dispatcher log for missed expected windows.

Runs at 09:05 WIB via cron-dispatcher.sh.
- Reads runtime/cron/YYYYMMDD.log
- Checks each expected window fired (grepping log for '→ <LABEL> start')
- Telegrams once per missed window per day (state: runtime/cron/watchdog-state.json)
- Prunes log files older than 30 days

See docs/superpowers/specs/2026-04-24-trading-agents-revamp-spec-8-orchestration.md §5.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
LOG_DIR = WORKSPACE / "runtime" / "cron"
STATE_FILE = LOG_DIR / "watchdog-state.json"
HOLIDAY_FILE = WORKSPACE / "vault" / "data" / "idx_holidays.json"
LOG_PRUNE_DAYS = 30

WIB = _dt.timezone(_dt.timedelta(hours=7))

# Windows expected by 09:05 on a trading day
EXPECTED_BY_0905 = [
    "OVERNIGHT MACRO",      # 03:00
    "UNIVERSE SCAN",        # 04:00
    "L0 PORTFOLIO",         # 04:30
    "L1 INSIGHT",           # 05:00
    "L2 SCREENING",         # 05:30
    "L4 TRADEPLAN",         # 06:00
    "L5 EXECUTE pre-open",  # 08:30
]


def _is_holiday(date_str: str) -> bool:
    if not HOLIDAY_FILE.exists():
        return False
    try:
        data = json.loads(HOLIDAY_FILE.read_text())
        year = date_str[:4]
        return date_str in data.get(year, [])
    except Exception:
        return False


def _is_trading_day(dt: _dt.datetime) -> bool:
    return dt.weekday() < 5 and not _is_holiday(dt.strftime("%Y-%m-%d"))


def _today_log(now: _dt.datetime) -> Path:
    return LOG_DIR / now.strftime("%Y%m%d") + ".log"


def _read_log(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(errors="replace")


def _fired(label: str, log_content: str) -> bool:
    return f"→ {label} start" in log_content


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _prune_old_logs(now: _dt.datetime) -> None:
    cutoff = now - _dt.timedelta(days=LOG_PRUNE_DAYS)
    cutoff_str = cutoff.strftime("%Y%m%d")
    for p in LOG_DIR.glob("*.log"):
        if p.stem < cutoff_str:
            try:
                p.unlink()
                print(f"[watchdog] pruned {p.name}")
            except Exception as e:
                print(f"[watchdog] prune failed {p.name}: {e}")


def _send_telegram(msg: str) -> None:
    try:
        from tools.trader.telegram_client import send_message
        send_message(msg)
    except Exception as e:
        print(f"[watchdog] telegram failed: {e}")


def run(now: _dt.datetime | None = None) -> None:
    if now is None:
        now = _dt.datetime.now(WIB)

    today_str = now.strftime("%Y-%m-%d")
    log_path = LOG_DIR / (now.strftime("%Y%m%d") + ".log")
    log_content = _read_log(log_path)
    state = _load_state()
    alerted_today = state.get(today_str, [])

    if not _is_trading_day(now):
        print(f"[watchdog] {today_str} not a trading day — skip window checks")
        _prune_old_logs(now)
        return

    if not log_path.exists():
        msg = f"[CRON watchdog] no log file for {today_str} — dispatcher may not be running"
        if "no_log" not in alerted_today:
            _send_telegram(msg)
            alerted_today.append("no_log")
            state[today_str] = alerted_today
            _save_state(state)
        print(msg)
        _prune_old_logs(now)
        return

    missed = []
    for label in EXPECTED_BY_0905:
        if not _fired(label, log_content):
            key = f"missed:{label}"
            if key not in alerted_today:
                missed.append(label)
                alerted_today.append(key)

    if missed:
        msg = "[CRON watchdog] missed windows by 09:05:\n" + "\n".join(f"  - {m}" for m in missed)
        _send_telegram(msg)
        print(msg)
    else:
        print(f"[watchdog] {today_str} all pre-market windows confirmed")

    state[today_str] = alerted_today
    _save_state(state)
    _prune_old_logs(now)


if __name__ == "__main__":
    run()
