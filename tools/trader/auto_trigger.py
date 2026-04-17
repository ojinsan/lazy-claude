"""
Auto-trigger: invoke Claude when tape + confluence + spring all fire on high conviction.
Gates: confluence >= 80, tape composite high, portfolio health, dedup, daily budget.
Exit codes: 0=triggered, 1=deduped, 2=over_budget, 3=gate_failed.
"""
import sys
import os
import json
import subprocess
import argparse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.trader.telegram_client import send_telegram

VAULT_DIR = Path(__file__).parent.parent.parent / "vault" / "data"
TRIGGER_LOG = VAULT_DIR / "auto_trigger_log.jsonl"

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CONFLUENCE_THRESHOLD = 80
DAILY_BUDGET = 5
DEDUP_TTL_SEC = 3600

ELIGIBLE_COMPOSITES = {"ideal_markup", "spring_ready", "healthy_markup"}
ELIGIBLE_CONFIDENCE = {"high"}


def _redis():
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def _daily_count(r) -> int:
    if r is None:
        return 0
    key = f"autogen:{date.today().isoformat()}"
    val = r.get(key)
    return int(val) if val else 0


def _increment_daily(r) -> None:
    if r is None:
        return
    key = f"autogen:{date.today().isoformat()}"
    r.incr(key)
    r.expire(key, 86400)


def _dedup_key(ticker: str, signal_kind: str) -> str:
    return f"signal:triggered:{ticker.upper()}:{signal_kind}"


def should_trigger(ticker: str, signal_kind: str) -> tuple[bool, str]:
    """Check all gates. Returns (ok, reason)."""
    t = ticker.upper()

    # Gate: confluence
    try:
        from tools.trader.confluence_score import score as get_score
        cs = get_score(t)
        if cs["score"] < CONFLUENCE_THRESHOLD:
            return False, f"confluence {cs['score']} < {CONFLUENCE_THRESHOLD}"
    except Exception as e:
        return False, f"confluence error: {e}"

    # Gate: tape composite
    try:
        from tools.trader.tape_runner import snapshot
        tape = snapshot(t)
        if tape.composite not in ELIGIBLE_COMPOSITES or tape.confidence not in ELIGIBLE_CONFIDENCE:
            return False, f"tape {tape.composite}/{tape.confidence} not eligible"
    except Exception as e:
        return False, f"tape error: {e}"

    # Gate: portfolio health (DD < 5%, posture >= 2, kill switch inactive)
    try:
        import tools.trader.journal as journal
        ks = journal.kill_switch_state()
        if ks.get("active"):
            return False, f"kill switch active: {ks.get('reason', '')}"
        ip = journal.get_intraday_posture()
        posture = ip.get("posture", 3)
        if posture < 2:
            return False, f"posture {posture} < 2"
    except Exception:
        pass

    try:
        import tools.trader.portfolio_health as ph
        state_file = VAULT_DIR / "portfolio-state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            dd = state.get("drawdown_pct", 0.0)
            if dd > 5.0:
                return False, f"DD {dd}% > 5%"
    except Exception:
        pass

    # Gate: dedup
    r = _redis()
    if r:
        dk = _dedup_key(t, signal_kind)
        if r.exists(dk):
            return False, "deduped"

    # Gate: daily budget
    if _daily_count(r) >= DAILY_BUDGET:
        return False, f"over_budget ({DAILY_BUDGET}/day)"

    return True, "all gates passed"


def trigger(ticker: str, signal_kind: str, context: dict, dry_run: bool = False) -> dict:
    """
    Execute the auto-trigger flow:
    1. Telegram first
    2. Dedup key set
    3. Budget increment
    4. Claude invocation
    5. Log
    """
    t = ticker.upper()

    try:
        from tools.trader.confluence_score import score as get_score
        cs = get_score(t)
        confluence = cs.get("score", 0)
    except Exception:
        confluence = 0

    # 1. Telegram first
    msg = (
        f"[AUTO-TRIGGER] {t}\n"
        f"Signal: {signal_kind}\n"
        f"Confluence: {confluence}\n"
        f"Context: {json.dumps(context, ensure_ascii=False)[:200]}\n"
        f"Action: proceeding to L4+L5"
    )
    if not dry_run:
        try:
            send_telegram(msg, subcommand="auto_trigger_detected")
        except Exception:
            pass

    # 2. Dedup
    r = _redis()
    if not dry_run and r:
        dk = _dedup_key(t, signal_kind)
        r.setex(dk, DEDUP_TTL_SEC, "1")
        _increment_daily(r)

    # 3. Build prompt
    context_str = json.dumps(context, ensure_ascii=False)
    prompt = (
        f"Auto-trigger fired for {t}. Signal: {signal_kind}. "
        f"Confluence: {confluence}. Context: {context_str}. "
        f"Re-read today's L1 posture and L0 state. "
        f"Verify tape + confluence evidence at this invocation time. "
        f"Decide: proceed with L4+L5, or abort. State the reason. "
        f"Telegram-first before any order."
    )

    outcome = "dry_run" if dry_run else "fired"
    if not dry_run:
        # 4. Invoke Claude
        settings_path = ".claude/settings.openclaude.json"
        cmd = [
            "claude", "--dangerously-skip-permissions", "--bare",
            "--settings", settings_path, "-p", prompt
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            # Retry without --settings
            cmd2 = ["claude", "--dangerously-skip-permissions", "--bare", "-p", prompt]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
            if result2.returncode != 0:
                outcome = "claude_error"

    # 5. Log
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ticker": t,
        "kind": signal_kind,
        "confluence": confluence,
        "outcome": outcome,
        "reason": "dry_run" if dry_run else "auto-trigger",
    }
    if not dry_run:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        with TRIGGER_LOG.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")

    return log_entry


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("signal_kind", nargs="?", default="ideal_markup")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    ok, reason = should_trigger(args.ticker, args.signal_kind)
    print(f"should_trigger: {ok} — {reason}")

    if ok or args.dry_run:
        result = trigger(args.ticker, args.signal_kind, {}, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
    else:
        codes = {"deduped": 1, "over_budget": 2}
        for k, c in codes.items():
            if k in reason:
                sys.exit(c)
        sys.exit(3)
