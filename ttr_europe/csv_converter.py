from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

POINTS_BY_LENGTH = {1: 1, 2: 2, 3: 4, 4: 7, 6: 15, 8: 21}
LENGTH_BY_POINTS = {points: length for length, points in POINTS_BY_LENGTH.items()}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return slug.strip("_")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _load_cities(path: Path) -> tuple[list[dict], dict[str, str]]:
    rows: list[dict] = []
    name_to_id: dict[str, str] = {}

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for item in reader:
            name = item["City"].strip()
            city_id = _slugify(name)
            if city_id in name_to_id.values():
                raise ValueError(f"Duplicate city id after normalization: {city_id}")

            name_to_id[name] = city_id
            rows.append(
                {
                    "city_id": city_id,
                    "name": name,
                    "longitude": float(item["Longitude"]),
                    "latitude": float(item["Latitude"]),
                }
            )

    return rows, name_to_id


def _load_routes(path: Path, name_to_id: dict[str, str]) -> list[dict]:
    raw_routes: list[dict] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for item in reader:
            source_name = item["Source"].strip()
            target_name = item["Target"].strip()
            if source_name not in name_to_id or target_name not in name_to_id:
                raise ValueError(f"Route references unknown city: {source_name} -> {target_name}")

            city_a = name_to_id[source_name]
            city_b = name_to_id[target_name]
            route_base = f"{city_a}_{city_b}"

            raw_routes.append(
                {
                    "route_id": route_base,
                    "city_a": city_a,
                    "city_b": city_b,
                    "length": int(item["Carriages"]),
                    # CSV only provides whether a route requires a specific color.
                    # Keep gray for compatibility and preserve source detail in extra metadata.
                    "color": "gray",
                    "is_tunnel": _parse_bool(item["Tunnel"]),
                    "ferry_locomotives_required": int(item["Engine"]),
                    "requires_specific_color": _parse_bool(item["Colored"]),
                }
            )

    per_pair_count: dict[tuple[str, str], int] = defaultdict(int)
    for route in raw_routes:
        pair = tuple(sorted((route["city_a"], route["city_b"])))
        per_pair_count[pair] += 1

    route_id_count = Counter(route["route_id"] for route in raw_routes)
    route_id_seen: dict[str, int] = defaultdict(int)

    normalized_routes: list[dict] = []
    for route in raw_routes:
        base_id = route["route_id"]
        route_id_seen[base_id] += 1
        if route_id_count[base_id] > 1:
            route["route_id"] = f"{base_id}_{route_id_seen[base_id]}"

        pair = tuple(sorted((route["city_a"], route["city_b"])))
        if per_pair_count[pair] > 1:
            route["parallel_group"] = "_".join(pair)

        normalized_routes.append(route)

    return normalized_routes


def _load_destinations(path: Path, name_to_id: dict[str, str]) -> list[dict]:
    tickets: list[dict] = []
    used_ids: set[str] = set()

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for item in reader:
            source_name = item["Source"].strip()
            target_name = item["Target"].strip()
            if source_name not in name_to_id or target_name not in name_to_id:
                raise ValueError(
                    f"Destination ticket references unknown city: {source_name} -> {target_name}"
                )

            source_id = name_to_id[source_name]
            target_id = name_to_id[target_name]
            ticket_id_base = f"{source_id}_{target_id}"
            ticket_id = ticket_id_base
            suffix = 2
            while ticket_id in used_ids:
                ticket_id = f"{ticket_id_base}_{suffix}"
                suffix += 1
            used_ids.add(ticket_id)

            tickets.append(
                {
                    "ticket_id": ticket_id,
                    "source_city": source_id,
                    "target_city": target_id,
                    "points": int(item["Points"]),
                }
            )

    return tickets


def _build_destination_board_template(cities: list[dict], tickets: list[dict]) -> dict:
    city_name_by_id = {city["city_id"]: city["name"] for city in cities}
    used_city_ids = {
        city_id
        for ticket in tickets
        for city_id in (ticket["source_city"], ticket["target_city"])
    }

    template_cities = [
        {"city_id": city_id, "name": city_name_by_id.get(city_id, city_id.title())}
        for city_id in sorted(used_city_ids)
    ]

    template_routes: list[dict] = []
    for ticket in tickets:
        points = ticket["points"]
        inferred_length = LENGTH_BY_POINTS.get(points)
        route = {
            "route_id": ticket["ticket_id"],
            "city_a": ticket["source_city"],
            "city_b": ticket["target_city"],
            "length": inferred_length if inferred_length is not None else 0,
            "color": "gray",
            "ticket_points": points,
        }
        if inferred_length is None:
            route["needs_manual_length"] = True
        template_routes.append(route)

    return {"cities": template_cities, "routes": template_routes}


def _build_sample_board_from_routes(cities: list[dict], routes: list[dict]) -> dict:
    sample_cities = [{"city_id": city["city_id"], "name": city["name"]} for city in cities]

    sample_routes: list[dict] = []
    for route in routes:
        sample_route = {
            "route_id": route["route_id"],
            "city_a": route["city_a"],
            "city_b": route["city_b"],
            "length": route["length"],
            # Placeholder to keep the JSON loadable; fill this manually for colored routes.
            "color": "gray",
            "is_tunnel": route["is_tunnel"],
            "ferry_locomotives_required": route["ferry_locomotives_required"],
        }
        if route.get("parallel_group") is not None:
            sample_route["parallel_group"] = route["parallel_group"]
        if route.get("requires_specific_color"):
            sample_route["needs_manual_color"] = True
        sample_routes.append(sample_route)

    return {"cities": sample_cities, "routes": sample_routes}


def convert_csvs(
    *,
    cities_csv_path: str | Path,
    routes_csv_path: str | Path,
    destinations_csv_path: str | Path,
    board_json_path: str | Path,
    destinations_json_path: str | Path | None = None,
    destination_board_template_json_path: str | Path | None = None,
    routes_sample_board_json_path: str | Path | None = None,
) -> None:
    cities_path = Path(cities_csv_path)
    routes_path = Path(routes_csv_path)
    destinations_path = Path(destinations_csv_path)
    board_path = Path(board_json_path)

    cities, name_to_id = _load_cities(cities_path)
    routes = _load_routes(routes_path, name_to_id)
    tickets = _load_destinations(destinations_path, name_to_id)

    board_payload = {"cities": cities, "routes": routes}
    board_path.parent.mkdir(parents=True, exist_ok=True)
    board_path.write_text(json.dumps(board_payload, indent=2), encoding="utf-8")

    if destinations_json_path is not None:
        tickets_path = Path(destinations_json_path)
        tickets_path.parent.mkdir(parents=True, exist_ok=True)
        tickets_path.write_text(
            json.dumps({"destination_tickets": tickets}, indent=2),
            encoding="utf-8",
        )

    if destination_board_template_json_path is not None:
        board_template_path = Path(destination_board_template_json_path)
        board_template = _build_destination_board_template(cities, tickets)
        board_template_path.parent.mkdir(parents=True, exist_ok=True)
        board_template_path.write_text(
            json.dumps(board_template, indent=2),
            encoding="utf-8",
        )

    if routes_sample_board_json_path is not None:
        routes_template_path = Path(routes_sample_board_json_path)
        routes_sample_board = _build_sample_board_from_routes(cities, routes)
        routes_template_path.parent.mkdir(parents=True, exist_ok=True)
        routes_template_path.write_text(
            json.dumps(routes_sample_board, indent=2),
            encoding="utf-8",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ttr_europe.csv_converter",
        description="Convert Ticket to Ride Europe CSV datasets into JSON files.",
    )
    parser.add_argument("--cities-csv", default="cities.csv", help="Path to cities CSV.")
    parser.add_argument("--routes-csv", default="routes.csv", help="Path to routes CSV.")
    parser.add_argument(
        "--destinations-csv",
        default="destinations.csv",
        help="Path to destination tickets CSV.",
    )
    parser.add_argument(
        "--board-json",
        default="data/europe_board_from_csv.json",
        help="Output path for board JSON.",
    )
    parser.add_argument(
        "--destinations-json",
        default="data/europe_destination_tickets_from_csv.json",
        help="Output path for destination tickets JSON.",
    )
    parser.add_argument(
        "--destination-board-template-json",
        default="data/europe_sample_board_from_destinations.json",
        help="Output path for sample-board-format template built from destination tickets.",
    )
    parser.add_argument(
        "--routes-sample-board-json",
        default="data/europe_sample_board_from_routes.json",
        help="Output path for sample-board-format template built from routes CSV.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    convert_csvs(
        cities_csv_path=args.cities_csv,
        routes_csv_path=args.routes_csv,
        destinations_csv_path=args.destinations_csv,
        board_json_path=args.board_json,
        destinations_json_path=args.destinations_json,
        destination_board_template_json_path=args.destination_board_template_json,
        routes_sample_board_json_path=args.routes_sample_board_json,
    )
    print(f"Converted board data written to: {args.board_json}")
    print(f"Converted destination tickets written to: {args.destinations_json}")
    print(
        "Destination-board template written to: "
        f"{args.destination_board_template_json}"
    )
    print(f"Routes sample-board template written to: {args.routes_sample_board_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
