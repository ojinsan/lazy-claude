"""current_trade.json schema + load/save/snapshot.

See docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-1-core-design.md.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal, Optional

SCHEMA_VERSION = "1.0.0"
WORKSPACE = Path(__file__).resolve().parents[2]
LIVE_PATH = str(WORKSPACE / "runtime" / "current_trade.json")
HISTORY_DIR = str(WORKSPACE / "runtime" / "history")

Mode = Literal["buy_at_price", "sell_at_price", "wait_bid_offer"]
Status = Literal["ok", "error", "pending", "skipped"]


@dataclass
class CurrentPlan:
    mode: Mode
    price: Optional[float] = None


@dataclass
class ListItem:
    ticker: str
    confidence: int
    current_plan: Optional[CurrentPlan] = None
    details: str = ""


@dataclass
class Lists:
    filtered: list[ListItem] = field(default_factory=list)
    watchlist: list[ListItem] = field(default_factory=list)
    superlist: list[ListItem] = field(default_factory=list)
    exitlist: list[ListItem] = field(default_factory=list)


@dataclass
class Narrative:
    ticker: str
    content: str
    source: str
    confidence: int


@dataclass
class Balance:
    cash: float = 0.0
    buying_power: float = 0.0


@dataclass
class PnL:
    realized: float = 0.0
    unrealized: float = 0.0
    mtd: float = 0.0
    ytd: float = 0.0


@dataclass
class Holding:
    ticker: str
    lot: int
    avg_price: float
    current_price: float
    pnl_pct: float
    details: str = ""


@dataclass
class TraderStatus:
    regime: str = ""
    aggressiveness: str = ""
    sectors: list[str] = field(default_factory=list)
    narratives: list[Narrative] = field(default_factory=list)
    balance: Balance = field(default_factory=Balance)
    pnl: PnL = field(default_factory=PnL)
    holdings: list[Holding] = field(default_factory=list)
    intraday_notch: int = 0


@dataclass
class LayerRun:
    last_run: Optional[str] = None
    status: Status = "pending"
    note: Optional[str] = None


def _empty_layer_runs() -> dict[str, LayerRun]:
    return {name: LayerRun() for name in ("l0", "l1", "l2", "l3", "l4", "l5")}


@dataclass
class CurrentTrade:
    schema_version: str = SCHEMA_VERSION
    version: int = 0
    updated_at: Optional[str] = None
    lists: Lists = field(default_factory=Lists)
    trader_status: TraderStatus = field(default_factory=TraderStatus)
    layer_runs: dict[str, LayerRun] = field(default_factory=_empty_layer_runs)


def _parse_list_item(d: dict[str, Any]) -> ListItem:
    plan = None
    raw_plan = d.get("current_plan")
    if raw_plan is not None:
        plan = CurrentPlan(mode=raw_plan["mode"], price=raw_plan.get("price"))
    return ListItem(
        ticker=d["ticker"],
        confidence=int(d["confidence"]),
        current_plan=plan,
        details=d.get("details", ""),
    )


def _parse_trader_status(d: dict[str, Any]) -> TraderStatus:
    return TraderStatus(
        regime=d.get("regime", ""),
        aggressiveness=d.get("aggressiveness", ""),
        sectors=list(d.get("sectors", [])),
        narratives=[Narrative(**n) for n in d.get("narratives", [])],
        balance=Balance(**d.get("balance", {})),
        pnl=PnL(**d.get("pnl", {})),
        holdings=[Holding(**h) for h in d.get("holdings", [])],
        intraday_notch=int(d.get("intraday_notch", 0)),
    )


def load() -> CurrentTrade:
    if not os.path.exists(LIVE_PATH):
        return CurrentTrade()
    with open(LIVE_PATH) as f:
        data = json.load(f)
    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ValueError(f"schema_version mismatch: file={sv!r} expected={SCHEMA_VERSION!r}")
    lists = Lists(
        filtered=[_parse_list_item(x) for x in data["lists"].get("filtered", [])],
        watchlist=[_parse_list_item(x) for x in data["lists"].get("watchlist", [])],
        superlist=[_parse_list_item(x) for x in data["lists"].get("superlist", [])],
        exitlist=[_parse_list_item(x) for x in data["lists"].get("exitlist", [])],
    )
    layer_runs = {
        name: LayerRun(**data["layer_runs"].get(name, {}))
        for name in ("l0", "l1", "l2", "l3", "l4", "l5")
    }
    return CurrentTrade(
        schema_version=sv,
        version=int(data.get("version", 0)),
        updated_at=data.get("updated_at"),
        lists=lists,
        trader_status=_parse_trader_status(data.get("trader_status", {})),
        layer_runs=layer_runs,
    )


def _now_wib_iso() -> str:
    tz = _dt.timezone(_dt.timedelta(hours=7))
    return _dt.datetime.now(tz).replace(microsecond=0).isoformat()


def _serialize(ct: CurrentTrade) -> dict[str, Any]:
    return asdict(ct)


def _write_live(ct: CurrentTrade) -> None:
    os.makedirs(os.path.dirname(LIVE_PATH), exist_ok=True)
    tmp = LIVE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_serialize(ct), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, LIVE_PATH)


def _write_snapshot(ct: CurrentTrade, layer: str) -> None:
    tz = _dt.timezone(_dt.timedelta(hours=7))
    now = _dt.datetime.now(tz)
    day_dir = os.path.join(HISTORY_DIR, now.strftime("%Y-%m-%d"))
    os.makedirs(day_dir, exist_ok=True)
    name = f"{layer}-{now.strftime('%H%M')}.json"
    path = os.path.join(day_dir, name)
    with open(path, "w") as f:
        json.dump(_serialize(ct), f, indent=2)


def snapshot(ct: CurrentTrade, label: str) -> None:
    _write_snapshot(ct, label)


def save(ct: CurrentTrade, layer: str, status: Status, note: Optional[str] = None) -> None:
    if layer not in ct.layer_runs:
        raise ValueError(f"unknown layer: {layer!r}")
    ct.version += 1
    now = _now_wib_iso()
    ct.updated_at = now
    ct.layer_runs[layer] = LayerRun(last_run=now, status=status, note=note)
    _write_live(ct)
    _write_snapshot(ct, layer)
