#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import api

DEFAULT_UNIVERSE = {"scope": "IHSG", "scopeID": "", "name": ""}


def get_templates() -> dict:
    return api._stockbit_get("/screener/templates")


def get_favorites() -> dict:
    return api._stockbit_get("/screener/favorites")


def get_universe() -> dict:
    return api._stockbit_get("/screener/universe")


def get_presets() -> dict:
    return api._stockbit_get("/screener/preset")


def get_metrics() -> dict:
    return api._stockbit_get("/screener/metric")


def get_template(template_id: int, result_type: str = "TEMPLATE_TYPE_CUSTOM") -> dict:
    return api._stockbit_get(f"/screener/templates/{template_id}", {"type": result_type})


def build_basic_rule(item1: int, item1name: str, operator: str, item2: str | int | float) -> dict[str, Any]:
    return {
        "type": "basic",
        "item1": item1,
        "item1name": item1name,
        "operator": operator,
        "item2": str(item2),
        "multiplier": "",
    }


def build_compare_rule(
    item1: int,
    item1name: str,
    operator: str,
    multiplier: str | int | float,
    item2: int,
    item2name: str,
) -> dict[str, Any]:
    return {
        "type": "compare",
        "item1": item1,
        "item1name": item1name,
        "operator": operator,
        "multiplier": str(multiplier),
        "item2": item2,
        "item2name": item2name,
    }


def build_sequence(filters: list[dict[str, Any]]) -> str:
    seen: list[int] = []
    for rule in filters:
        left = int(rule["item1"])
        if left not in seen:
            seen.append(left)
        if rule.get("type") != "basic":
            right = int(rule["item2"])
            if right not in seen:
                seen.append(right)
    return ",".join(str(item) for item in seen)


def build_payload(
    *,
    filters: list[dict[str, Any]],
    name: str,
    description: str = "",
    save: bool = False,
    universe: dict[str, Any] | None = None,
    page: int = 1,
    ordercol: int = 2,
    ordertype: str = "asc",
    screenerid: str = "0",
    result_type: str = "TEMPLATE_TYPE_CUSTOM",
) -> dict[str, Any]:
    if universe is None:
        universe = DEFAULT_UNIVERSE
    return {
        "name": name,
        "description": description,
        "save": "1" if save else "0",
        "ordertype": ordertype,
        "ordercol": ordercol,
        "page": page,
        "universe": json.dumps(universe),
        "filters": json.dumps(filters),
        "sequence": build_sequence(filters),
        "screenerid": screenerid,
        "type": result_type,
    }


def post_screener(payload: dict[str, Any]) -> dict:
    return api._stockbit_post("/screener/templates", payload)


def search_metrics(keyword: str) -> list[dict[str, Any]]:
    data = get_metrics().get("data", [])
    needle = keyword.lower()
    out: list[dict[str, Any]] = []
    for group in data:
        for child in group.get("child", []):
            name = child.get("fitem_name", "")
            if needle in name.lower():
                out.append({
                    "fitem_id": child.get("fitem_id"),
                    "fitem_name": name,
                    "group": group.get("fitem_name"),
                })
    return out


def load_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text())


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Stockbit screener API helper")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("templates")
    sub.add_parser("favorites")
    sub.add_parser("universe")
    sub.add_parser("preset")

    metrics_parser = sub.add_parser("metrics")
    metrics_parser.add_argument("--search", default="")

    tpl_parser = sub.add_parser("get-template")
    tpl_parser.add_argument("--id", type=int, required=True)
    tpl_parser.add_argument("--type", default="TEMPLATE_TYPE_CUSTOM")

    for name in ["payload", "run"]:
        run_parser = sub.add_parser(name)
        run_parser.add_argument("--filters-file", required=True)
        run_parser.add_argument("--name", required=True)
        run_parser.add_argument("--description", default="")
        run_parser.add_argument("--save", action="store_true")
        run_parser.add_argument("--page", type=int, default=1)
        run_parser.add_argument("--ordercol", type=int, default=2)
        run_parser.add_argument("--ordertype", choices=["asc", "desc"], default="asc")
        run_parser.add_argument("--screenerid", default="0")
        run_parser.add_argument("--type", default="TEMPLATE_TYPE_CUSTOM")
        run_parser.add_argument("--universe-file")

    args = parser.parse_args()

    if args.command == "templates":
        print_json(get_templates())
        return
    if args.command == "favorites":
        print_json(get_favorites())
        return
    if args.command == "universe":
        print_json(get_universe())
        return
    if args.command == "preset":
        print_json(get_presets())
        return
    if args.command == "metrics":
        if args.search:
            print_json(search_metrics(args.search))
        else:
            print_json(get_metrics())
        return
    if args.command == "get-template":
        print_json(get_template(args.id, args.type))
        return

    filters = load_json_file(args.filters_file)
    universe = load_json_file(args.universe_file) if args.universe_file else DEFAULT_UNIVERSE
    payload = build_payload(
        filters=filters,
        name=args.name,
        description=args.description,
        save=args.save,
        universe=universe,
        page=args.page,
        ordercol=args.ordercol,
        ordertype=args.ordertype,
        screenerid=args.screenerid,
        result_type=args.type,
    )
    if args.command == "payload":
        print_json(payload)
        return
    print_json(post_screener(payload))


if __name__ == "__main__":
    main()
