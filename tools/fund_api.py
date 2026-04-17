"""
Thin HTTP client for the fund-manager Go backend.

Usage:
    from tools.fund_api import api
    api.post_portfolio_snapshot({...})
    api.get_holdings(date='2026-04-17')

On network error: logs a warning, returns None. Never raises.
All writes are idempotent (upsert / create-or-update).
"""
import os
import logging
import requests

log = logging.getLogger(__name__)

BASE = os.environ.get("FUND_API_URL", "http://127.0.0.1:8787/api/v1")
TIMEOUT = 5


class FundAPI:
    def _post(self, path: str, body: dict) -> dict | None:
        try:
            r = requests.post(f"{BASE}{path}", json=body, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"fund_api POST {path} failed: {e}")
            return None

    def _put(self, path: str, body: dict) -> dict | None:
        try:
            r = requests.put(f"{BASE}{path}", json=body, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"fund_api PUT {path} failed: {e}")
            return None

    def _get(self, path: str, **params) -> dict | None:
        try:
            r = requests.get(f"{BASE}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"fund_api GET {path} failed: {e}")
            return None

    def _delete(self, path: str) -> bool:
        try:
            r = requests.delete(f"{BASE}{path}", timeout=TIMEOUT)
            return r.status_code in (200, 204)
        except Exception as e:
            log.warning(f"fund_api DELETE {path} failed: {e}")
            return False

    # ─── Portfolio ────────────────────────────────────────────────────────────

    def post_portfolio_snapshot(self, data: dict) -> dict | None:
        """Keys: date, equity, cash, deployed, utilization, drawdown, hwm, posture, raw_json."""
        return self._post("/portfolio/snapshot", data)

    def get_portfolio_snapshots(self, from_date=None, to_date=None, limit=60) -> list:
        r = self._get("/portfolio/snapshot", from_=from_date, to=to_date, limit=limit)
        return (r or {}).get("items", [])

    def post_holdings(self, batch: list[dict]) -> dict | None:
        """batch: list of holding dicts. Keys: date, ticker, shares, avg_cost, ..."""
        return self._post("/portfolio/holdings", batch)

    def get_holdings(self, date=None, ticker=None) -> list:
        r = self._get("/portfolio/holdings", date=date, ticker=ticker)
        return (r or {}).get("items", [])

    def get_portfolio_current(self) -> dict:
        return self._get("/portfolio/current") or {}

    def post_transaction(self, data: dict) -> dict | None:
        """Keys: ts, ticker, side, shares, price, value, order_id, thesis, conviction, layer_origin."""
        return self._post("/transactions", data)

    def put_transaction(self, tx_id: int, pnl: float, pnl_pct: float) -> dict | None:
        return self._put(f"/transactions/{tx_id}", {"pnl": pnl, "pnl_pct": pnl_pct})

    def get_transactions(self, ticker=None, days=None, side=None, limit=100) -> list:
        r = self._get("/transactions", ticker=ticker, days=days, side=side, limit=limit)
        return (r or {}).get("items", [])

    # ─── Watchlist ────────────────────────────────────────────────────────────

    def post_watchlist(self, data: dict) -> dict | None:
        """Keys: ticker, first_added, status, conviction, themes, notes, updated_at."""
        return self._post("/watchlist", data)

    def post_watchlist_batch(self, batch: list[dict]) -> None:
        for item in batch:
            self.post_watchlist(item)

    def get_watchlist(self, status=None) -> list:
        r = self._get("/watchlist", status=status)
        return (r or {}).get("items", [])

    def archive_watchlist(self, ticker: str) -> bool:
        return self._delete(f"/watchlist/{ticker}")

    # ─── Thesis ───────────────────────────────────────────────────────────────

    def post_thesis(self, data: dict) -> dict | None:
        return self._post("/thesis", data)

    def put_thesis(self, ticker: str, data: dict) -> dict | None:
        return self._put(f"/thesis/{ticker}", data)

    def get_thesis(self, ticker: str) -> dict | None:
        return self._get(f"/thesis/{ticker}")

    def get_all_thesis(self, status=None) -> list:
        r = self._get("/thesis", status=status)
        return (r or {}).get("items", [])

    def post_thesis_review(self, ticker: str, review_date: str, layer: str, note: str) -> dict | None:
        return self._post(f"/thesis/{ticker}/review", {"ticker": ticker, "review_date": review_date, "layer": layer, "note": note})

    def get_thesis_reviews(self, ticker: str) -> list:
        r = self._get(f"/thesis/{ticker}/review")
        return (r or {}).get("items", [])

    # ─── Themes ───────────────────────────────────────────────────────────────

    def post_theme(self, data: dict) -> dict | None:
        return self._post("/themes", data)

    def get_themes(self, status=None) -> list:
        r = self._get("/themes", status=status)
        return (r or {}).get("items", [])

    # ─── Trade Plans ──────────────────────────────────────────────────────────

    def post_tradeplan(self, data: dict) -> dict | None:
        """Keys: plan_date, ticker, mode, setup_type, thesis, entry_low/high, stop, target_1/2, ..."""
        return self._post("/tradeplans", data)

    def put_tradeplan_status(self, plan_id: int, status: str) -> dict | None:
        return self._put(f"/tradeplans/{plan_id}", {"status": status})

    def get_tradeplans(self, plan_date=None, ticker=None, status=None, level=None, limit=50) -> list:
        r = self._get("/tradeplans", plan_date=plan_date, ticker=ticker, status=status, level=level, limit=limit)
        return (r or {}).get("items", [])

    # ─── Signals ──────────────────────────────────────────────────────────────

    def post_signal(self, data: dict) -> dict | None:
        """Keys: ts, ticker, layer, kind, severity, price, payload_json."""
        return self._post("/signals", data)

    def get_signals(self, ticker=None, layer=None, kind=None, since=None, limit=100) -> list:
        r = self._get("/signals", ticker=ticker, layer=layer, kind=kind, since=since, limit=limit)
        return (r or {}).get("items", [])

    def post_layer_output(self, data: dict) -> dict | None:
        return self._post("/layer-outputs", data)

    def get_layer_outputs(self, run_date=None, layer=None, severity=None, limit=100) -> list:
        r = self._get("/layer-outputs", run_date=run_date, layer=layer, severity=severity, limit=limit)
        return (r or {}).get("items", [])

    def get_daily_note(self, date: str) -> dict | None:
        return self._get(f"/daily-notes/{date}")

    def put_daily_note(self, date: str, body_md: str) -> dict | None:
        return self._put(f"/daily-notes/{date}", {"body_md": body_md})

    # ─── Learning ─────────────────────────────────────────────────────────────

    def post_lesson(self, data: dict) -> dict | None:
        return self._post("/lessons", data)

    def get_lessons(self, category=None, severity=None, pattern_tag=None, days=None, limit=100) -> list:
        r = self._get("/lessons", category=category, severity=severity, pattern_tag=pattern_tag, days=days, limit=limit)
        return (r or {}).get("items", [])

    def post_calibration(self, data: dict) -> dict | None:
        return self._post("/calibration", data)

    def post_performance_daily(self, data: dict) -> dict | None:
        return self._post("/performance/daily", data)

    def get_performance_daily(self, from_date=None, to_date=None) -> list:
        r = self._get("/performance/daily", **{"from": from_date, "to": to_date})
        return (r or {}).get("items", [])

    def get_performance_summary(self) -> dict:
        return self._get("/performance/summary") or {}

    def post_evaluation(self, data: dict) -> dict | None:
        return self._post("/evaluations", data)

    def get_evaluations(self, period=None, period_key=None) -> list:
        r = self._get("/evaluations", period=period, period_key=period_key)
        return (r or {}).get("items", [])

    # ─── Charts ───────────────────────────────────────────────────────────────

    def post_chart(self, data: dict) -> dict | None:
        return self._post("/charts", data)

    def get_charts(self, ticker=None, kind=None, since=None, limit=50) -> list:
        r = self._get("/charts", ticker=ticker, kind=kind, since=since, limit=limit)
        return (r or {}).get("items", [])

    # ─── M3 Strategy signals ─────────────────────────────────────────────────

    def post_tape_state(self, data: dict) -> dict | None:
        """Keys: ts, ticker, composite, confidence, wall_fate, payload_json."""
        return self._post("/tape-states", data)

    def get_tape_history(self, ticker=None, composite=None, since=None, limit=100) -> list:
        r = self._get("/tape-states", ticker=ticker, composite=composite, since=since, limit=limit)
        return (r or {}).get("items", [])

    def post_confluence(self, data: dict) -> dict | None:
        """Keys: ts, ticker, score, bucket, components_json."""
        return self._post("/confluence", data)

    def get_confluence_latest(self) -> list:
        r = self._get("/confluence/latest")
        return (r or {}).get("items", [])

    def post_auto_trigger_log(self, data: dict) -> dict | None:
        return self._post("/auto-triggers", data)

    def get_konglo_group(self, ticker: str) -> list:
        r = self._get(f"/konglo/tickers/{ticker}")
        return (r or {}).get("items", [])

    def post_konglo_group(self, data: dict) -> dict | None:
        return self._post("/konglo/groups", data)

    # ─── Cache ────────────────────────────────────────────────────────────────

    def get_price(self, ticker: str) -> dict | None:
        return self._get(f"/cache/price/{ticker}")

    def post_price(self, ticker: str, data: dict) -> dict | None:
        return self._post(f"/cache/price/{ticker}", data)

    # ─── Kill Switch & Regime ─────────────────────────────────────────────────

    def get_kill_switch(self) -> dict:
        return self._get("/kill-switch") or {"active": False}

    def put_kill_switch(self, active: bool, reason: str = "") -> dict | None:
        return self._put("/kill-switch", {"active": active, "reason": reason})

    def put_regime_intraday(self, posture: int, reason: str = "") -> dict | None:
        return self._put("/regime/intraday", {"posture": posture, "reason": reason})

    def put_holding_action(self, ticker: str, action: str) -> None:
        pass


api = FundAPI()
