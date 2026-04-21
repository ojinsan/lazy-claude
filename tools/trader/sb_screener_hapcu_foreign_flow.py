#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api

SCREENER_NAME = "Hapcu Foreign Flow"
UNIVERSE = {"scope": "IHSG", "scopeID": "", "name": ""}

METRICS = {
    "current_pe_ratio_annualised": {"id": 12148, "name": "Current PE Ratio (Annualised)"},
    "net_foreign_buy_sell": {"id": 3194, "name": "Net Foreign Buy / Sell"},
    "net_foreign_buy_sell_ma10": {"id": 13539, "name": "Net Foreign Buy / Sell MA10"},
    "net_foreign_buy_streak": {"id": 13561, "name": "Net Foreign Buy Streak"},
    "foreign_flow": {"id": 3218, "name": "Foreign Flow"},
    "foreign_flow_ma20": {"id": 13521, "name": "Foreign Flow MA 20"},
    "net_foreign_sell_streak": {"id": 13562, "name": "Net Foreign Sell Streak"},
    "one_day_volume_change": {"id": 13650, "name": "1 Day Volume Change"},
    "near_52_week_high": {"id": 13412, "name": "Near 52 Week High"},
}


def basic(metric_key: str, operator: str, value: str) -> dict:
    metric = METRICS[metric_key]
    return {
        "type": "basic",
        "item1": metric["id"],
        "item1name": metric["name"],
        "operator": operator,
        "item2": value,
        "multiplier": "",
    }


def compare(left_key: str, operator: str, multiplier: str, right_key: str) -> dict:
    left = METRICS[left_key]
    right = METRICS[right_key]
    return {
        "type": "compare",
        "item1": left["id"],
        "item1name": left["name"],
        "operator": operator,
        "multiplier": multiplier,
        "item2": right["id"],
        "item2name": right["name"],
    }


def build_filters() -> list[dict]:
    return [
        basic("current_pe_ratio_annualised", "<", "40"),
        basic("net_foreign_buy_sell", ">", "1000000000"),
        basic("net_foreign_buy_sell_ma10", ">", "1000000000"),
        basic("net_foreign_buy_streak", ">=", "2"),
        compare("foreign_flow", ">", "1", "foreign_flow_ma20"),
        compare("net_foreign_buy_streak", ">", "2", "net_foreign_sell_streak"),
        basic("one_day_volume_change", ">", "1"),
        basic("near_52_week_high", ">", "0.7"),
    ]


def build_sequence(filters: list[dict]) -> str:
    seen: list[int] = []
    for rule in filters:
        left = int(rule["item1"])
        if left not in seen:
            seen.append(left)
        if rule["type"] != "basic":
            right = int(rule["item2"])
            if right not in seen:
                seen.append(right)
    return ",".join(str(item) for item in seen)


def build_payload(name: str, description: str, save: bool, page: int, ordercol: int, ordertype: str) -> dict:
    filters = build_filters()
    return {
        "name": name,
        "description": description,
        "save": "1" if save else "0",
        "ordertype": ordertype,
        "ordercol": ordercol,
        "page": page,
        "universe": json.dumps(UNIVERSE),
        "filters": json.dumps(filters),
        "sequence": build_sequence(filters),
        "screenerid": "0",
        "type": "TEMPLATE_TYPE_CUSTOM",
    }


def post_screener(name: str, description: str, save: bool, page: int, ordercol: int, ordertype: str) -> dict:
    payload = build_payload(name=name, description=description, save=save, page=page, ordercol=ordercol, ordertype=ordertype)
    return api._stockbit_post("/screener/templates", payload)


def summarize(response: dict) -> dict:
    data = response.get("data", {}) if isinstance(response, dict) else {}
    calcs = data.get("calcs", []) if isinstance(data, dict) else []
    return {
        "count": len(calcs),
        "symbols": [item.get("company", {}).get("symbol") for item in calcs[:20] if item.get("company", {}).get("symbol")],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or save Hapcu foreign-flow Stockbit screener")
    parser.add_argument("--save", action="store_true", help="Save screener to Stockbit")
    parser.add_argument("--name", default=SCREENER_NAME, help="Screener name when saving")
    parser.add_argument("--description", default="", help="Screener description")
    parser.add_argument("--page", type=int, default=1, help="Result page")
    parser.add_argument("--ordercol", type=int, default=2, help="Sort column index")
    parser.add_argument("--ordertype", choices=["asc", "desc"], default="asc", help="Sort direction")
    parser.add_argument("--payload", action="store_true", help="Print payload only")
    parser.add_argument("--raw", action="store_true", help="Print raw Stockbit response")
    args = parser.parse_args()

    payload = build_payload(
        name=args.name,
        description=args.description,
        save=args.save,
        page=args.page,
        ordercol=args.ordercol,
        ordertype=args.ordertype,
    )
    if args.payload:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    response = post_screener(
        name=args.name,
        description=args.description,
        save=args.save,
        page=args.page,
        ordercol=args.ordercol,
        ordertype=args.ordertype,
    )
    if args.raw:
        print(json.dumps(response, indent=2, ensure_ascii=False))
        return

    output = {
        "name": args.name,
        "saved": args.save,
        "summary": summarize(response),
        "message": response.get("message", ""),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
