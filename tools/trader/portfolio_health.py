from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from api import get_cash_info, get_emitten_info, get_portfolio

WIB = ZoneInfo("Asia/Jakarta")
STATE_PATH = Path("/home/lazywork/workspace/vault/data/portfolio-state.json")
THEME_BUCKETS = {
    "energy": "Energy",
    "coal": "Energy",
    "oil": "Energy",
    "gas": "Energy",
    "bank": "Banking",
    "banking": "Banking",
    "finance": "Banking",
    "financial": "Banking",
    "property": "Property",
    "real estate": "Property",
    "construction": "Property",
    "nickel": "Nickel-EV",
    "mining": "Nickel-EV",
    "metal": "Nickel-EV",
    "ev": "Nickel-EV",
    "consumer": "Consumer",
    "retail": "Consumer",
    "staples": "Consumer",
    "discretionary": "Consumer",
}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"history": []}
    try:
        data = json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        return {"history": []}
    if not isinstance(data, dict):
        return {"history": []}
    data.setdefault("history", [])
    return data


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    # M2.5 dual-write
    try:
        import sys as _sys; _sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.fund_api import api as _api
        snap = {
            "date": state.get("date", ""),
            "equity": state.get("total_equity", 0),
            "cash": state.get("cash", 0),
            "deployed": state.get("deployed", 0),
            "utilization": state.get("utilization_pct", 0),
            "drawdown": state.get("drawdown_pct", 0),
            "hwm": state.get("high_water_mark", 0),
            "posture": state.get("posture", ""),
            "raw_json": json.dumps(state),
        }
        _api.post_portfolio_snapshot(snap)
        holdings = state.get("positions", [])
        if holdings:
            batch = [{"date": snap["date"], "ticker": h.get("ticker", ""), "shares": h.get("shares", 0),
                      "avg_cost": h.get("avg_cost", 0), "last_price": h.get("last_price", 0),
                      "market_value": h.get("market_value", 0), "unrealized_pnl": h.get("unrealized_pnl", 0),
                      "unrealized_pct": h.get("unrealized_pct", 0), "sector": h.get("sector", ""),
                      "action": h.get("action", ""), "thesis_status": h.get("thesis_status", "")}
                     for h in holdings]
            _api.post_holdings(batch)
    except Exception as _e:
        import logging; logging.getLogger(__name__).warning(f"fund_api dual-write failed: {_e}")


def compute_drawdown(equity_history: list[dict[str, Any]]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for row in equity_history:
        equity = float(row.get("equity", 0) or 0)
        if equity <= 0:
            continue
        peak = max(peak, equity)
        if peak <= 0:
            continue
        drawdown = ((peak - equity) / peak) * 100
        max_drawdown = max(max_drawdown, drawdown)
    return round(max_drawdown, 2)


def _today() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d")


def _month_prefix() -> str:
    return datetime.now(WIB).strftime("%Y-%m")


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _infer_bucket(symbol: str) -> str:
    info = get_emitten_info(symbol)
    if not isinstance(info, dict) or info.get("error"):
        return "Other"

    candidates = [
        str(info.get("sector") or ""),
        str(info.get("sub_sector") or ""),
        str(info.get("industry") or ""),
        str(info.get("subindustry") or ""),
    ]
    text = " ".join(candidates).lower()

    for key, bucket in THEME_BUCKETS.items():
        if key in text:
            return bucket
    return "Other"


def compute_exposure_breakdown() -> dict[str, Any]:
    portfolio = get_portfolio()
    positions = portfolio.get("positions", []) if isinstance(portfolio, dict) else []
    cash_info = get_cash_info()
    cash = _safe_float(cash_info.get("cash") or cash_info.get("trade_balance") or cash_info.get("trade_limit"))
    total_market_value = sum(_safe_float(pos.get("market_value")) for pos in positions)
    total_equity = cash + total_market_value

    ticker_rows: list[dict[str, Any]] = []
    sector_totals: dict[str, float] = {}

    for pos in positions:
        market_value = _safe_float(pos.get("market_value"))
        symbol = str(pos.get("symbol") or "").upper()
        bucket = _infer_bucket(symbol)
        exposure_pct = (market_value / total_equity * 100) if total_equity > 0 else 0.0
        ticker_rows.append(
            {
                "symbol": symbol,
                "sector_bucket": bucket,
                "market_value": market_value,
                "exposure_pct": round(exposure_pct, 2),
                "gain_pct": round(_safe_float(pos.get("gain_pct")), 2),
            }
        )
        sector_totals[bucket] = sector_totals.get(bucket, 0.0) + market_value

    sector_rows = []
    for bucket, value in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True):
        pct = (value / total_equity * 100) if total_equity > 0 else 0.0
        sector_rows.append({
            "sector_bucket": bucket,
            "market_value": round(value, 2),
            "exposure_pct": round(pct, 2),
        })

    return {
        "total_equity": round(total_equity, 2),
        "cash": round(cash, 2),
        "by_ticker": sorted(ticker_rows, key=lambda item: item["market_value"], reverse=True),
        "by_sector": sector_rows,
    }


def compute_concentration_flags() -> list[str]:
    breakdown = compute_exposure_breakdown()
    flags: list[str] = []

    for row in breakdown["by_ticker"]:
        if row["exposure_pct"] > 20:
            flags.append(f"single_position>{20}%:{row['symbol']}={row['exposure_pct']:.2f}%")

    for row in breakdown["by_sector"]:
        if row["exposure_pct"] > 50:
            flags.append(f"sector>{50}%:{row['sector_bucket']}={row['exposure_pct']:.2f}%")

    deployed = breakdown["total_equity"] - breakdown["cash"]
    if breakdown["total_equity"] > 0:
        deployed_pct = deployed / breakdown["total_equity"] * 100
        if deployed_pct > 80:
            flags.append(f"deployed_exposure>{80}%={deployed_pct:.2f}%")

    return flags


def compute_portfolio_state() -> dict[str, Any]:
    portfolio = get_portfolio()
    positions = portfolio.get("positions", []) if isinstance(portfolio, dict) else []
    cash_info = get_cash_info()
    state = load_state()
    history = list(state.get("history", []))

    cash = _safe_float(cash_info.get("cash") or cash_info.get("trade_balance") or cash_info.get("trade_limit"))
    total_market_value = sum(_safe_float(pos.get("market_value")) for pos in positions)
    total_equity = cash + total_market_value
    utilization = (total_market_value / total_equity * 100) if total_equity > 0 else 0.0

    today = _today()
    month_prefix = _month_prefix()
    month_rows = [row for row in history if str(row.get("date", "")).startswith(month_prefix)]
    month_start_equity = _safe_float(month_rows[0].get("equity")) if month_rows else total_equity
    mtd_return = ((total_equity - month_start_equity) / month_start_equity * 100) if month_start_equity > 0 else 0.0

    if history:
        high_water_mark = max(_safe_float(row.get("equity")) for row in history)
    else:
        high_water_mark = total_equity
    high_water_mark = max(high_water_mark, total_equity)
    current_drawdown = ((high_water_mark - total_equity) / high_water_mark * 100) if high_water_mark > 0 else 0.0

    breakdown = compute_exposure_breakdown()
    position_rows = breakdown["by_ticker"]
    top_exposure = position_rows[0]["symbol"] if position_rows else None

    current_row = {
        "date": today,
        "equity": round(total_equity, 2),
        "cash": round(cash, 2),
        "deployed": round(total_market_value, 2),
        "utilization_pct": round(utilization, 2),
        "drawdown_pct": round(current_drawdown, 2),
        "top_exposure": top_exposure,
    }

    history = [row for row in history if row.get("date") != today]
    history.append(current_row)
    save_state({"history": history})

    return {
        "date": today,
        "equity": round(total_equity, 2),
        "cash": round(cash, 2),
        "deployed": round(total_market_value, 2),
        "positions": len(positions),
        "utilization_pct": round(utilization, 2),
        "mtd_return_pct": round(mtd_return, 2),
        "drawdown_pct": round(current_drawdown, 2),
        "max_drawdown_pct": compute_drawdown(history),
        "high_water_mark": round(high_water_mark, 2),
        "top_exposure": top_exposure,
        "exposure": breakdown,
        "flags": compute_concentration_flags(),
        "history": history,
    }
