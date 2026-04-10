#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

WORKSPACE = Path("/home/lazywork/.openclaw/workspace")
ENV_PATH = WORKSPACE / ".env.local"


def load_env() -> None:
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def client():
    import googlemaps

    load_env()
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise SystemExit(json.dumps({"ok": False, "error": "GOOGLE_MAPS_API_KEY not set in .env.local"}))
    return googlemaps.Client(key=key)


def parse_location(value: str) -> tuple[float, float]:
    lat, lng = value.split(",", 1)
    return float(lat.strip()), float(lng.strip())


def search_places(query: str, limit: int) -> dict:
    items = client().places(query=query).get("results", [])[:limit]
    return {"ok": True, "items": items}


def place_details(place_id: str) -> dict:
    item = client().place(place_id=place_id).get("result", {})
    return {"ok": True, "item": item}


def directions(origin: str, destination: str, mode: str) -> dict:
    routes = client().directions(origin=origin, destination=destination, mode=mode)
    return {"ok": True, "items": routes}


def nearby(location: str, place_type: str, radius: int, limit: int) -> dict:
    latlng = parse_location(location)
    items = client().places_nearby(location=latlng, radius=radius, type=place_type).get("results", [])[:limit]
    return {"ok": True, "items": items}


def geocode(address: str) -> dict:
    items = client().geocode(address)
    return {"ok": True, "items": items}


def reverse_geocode(lat: float, lng: float) -> dict:
    items = client().reverse_geocode((lat, lng))
    return {"ok": True, "items": items}


def distance_matrix(origins: str, destinations: str, mode: str) -> dict:
    o = [x.strip() for x in origins.split(",") if x.strip()]
    d = [x.strip() for x in destinations.split(",") if x.strip()]
    item = client().distance_matrix(origins=o, destinations=d, mode=mode)
    return {"ok": True, "item": item}


def trip_plan(stops: str, mode: str) -> dict:
    pts = [x.strip() for x in stops.split(",") if x.strip()]
    if len(pts) < 2:
        raise SystemExit(json.dumps({"ok": False, "error": "trip-plan requires at least 2 stops"}))
    origin = pts[0]
    destination = pts[-1]
    waypoints = pts[1:-1]
    routes = client().directions(origin=origin, destination=destination, mode=mode, waypoints=waypoints, optimize_waypoints=True)
    return {"ok": True, "items": routes}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Google Maps Platform CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("search")
    x.add_argument("--query", required=True)
    x.add_argument("--limit", type=int, default=10)

    x = sub.add_parser("place")
    x.add_argument("--place-id", required=True)

    x = sub.add_parser("directions")
    x.add_argument("--origin", required=True)
    x.add_argument("--destination", required=True)
    x.add_argument("--mode", default="driving", choices=["driving", "walking", "transit", "bicycling"])

    x = sub.add_parser("nearby")
    x.add_argument("--location", required=True, help="lat,lng")
    x.add_argument("--type", required=True, dest="place_type")
    x.add_argument("--radius", type=int, default=1000)
    x.add_argument("--limit", type=int, default=10)

    x = sub.add_parser("geocode")
    x.add_argument("--address", required=True)

    x = sub.add_parser("reverse-geocode")
    x.add_argument("--lat", required=True, type=float)
    x.add_argument("--lng", required=True, type=float)

    x = sub.add_parser("distance-matrix")
    x.add_argument("--origins", required=True)
    x.add_argument("--destinations", required=True)
    x.add_argument("--mode", default="driving", choices=["driving", "walking", "transit", "bicycling"])

    x = sub.add_parser("trip-plan")
    x.add_argument("--stops", required=True)
    x.add_argument("--mode", default="driving", choices=["driving", "walking", "transit", "bicycling"])

    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "search":
        result = search_places(args.query, args.limit)
    elif args.cmd == "place":
        result = place_details(args.place_id)
    elif args.cmd == "directions":
        result = directions(args.origin, args.destination, args.mode)
    elif args.cmd == "nearby":
        result = nearby(args.location, args.place_type, args.radius, args.limit)
    elif args.cmd == "geocode":
        result = geocode(args.address)
    elif args.cmd == "reverse-geocode":
        result = reverse_geocode(args.lat, args.lng)
    elif args.cmd == "distance-matrix":
        result = distance_matrix(args.origins, args.destinations, args.mode)
    else:
        result = trip_plan(args.stops, args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
