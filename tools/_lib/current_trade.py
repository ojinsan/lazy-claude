"""current_trade.json schema + load/save/snapshot.

See docs/superpowers/specs/2026-04-19-trading-agents-revamp-spec-1-core-design.md.
"""
from __future__ import annotations

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


@dataclass
class TraderStatus:
    regime: str = ""
    aggressiveness: str = ""
    sectors: list[str] = field(default_factory=list)
    narratives: list[Narrative] = field(default_factory=list)
    balance: Balance = field(default_factory=Balance)
    pnl: PnL = field(default_factory=PnL)
    holdings: list[Holding] = field(default_factory=list)


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


def load() -> CurrentTrade:
    if not os.path.exists(LIVE_PATH):
        return CurrentTrade()
    raise NotImplementedError("load() from existing file not implemented yet")
