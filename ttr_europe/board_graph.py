from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .models import City, Route, RouteColor


@dataclass(frozen=True)
class BoardGraph:
    cities: dict[str, City]
    routes: dict[str, Route]
    adjacency: dict[str, list[str]]

    @classmethod
    def from_json(cls, path: str | Path) -> "BoardGraph":
        payload = json.loads(Path(path).read_text())

        cities = {
            city["city_id"]: City(city_id=city["city_id"], name=city["name"])
            for city in payload["cities"]
        }

        routes: dict[str, Route] = {}
        adjacency_raw: dict[str, list[str]] = defaultdict(list)

        for item in payload["routes"]:
            route = Route(
                route_id=item["route_id"],
                city_a=item["city_a"],
                city_b=item["city_b"],
                length=item["length"],
                color=RouteColor(item["color"]),
                is_tunnel=item.get("is_tunnel", False),
                ferry_locomotives_required=item.get("ferry_locomotives_required", 0),
                parallel_group=item.get("parallel_group"),
            )

            if route.city_a not in cities or route.city_b not in cities:
                raise ValueError(f"Route {route.route_id} references unknown cities")

            if route.route_id in routes:
                raise ValueError(f"Duplicate route id: {route.route_id}")

            routes[route.route_id] = route
            adjacency_raw[route.city_a].append(route.route_id)
            adjacency_raw[route.city_b].append(route.route_id)

        adjacency = {city_id: adjacency_raw.get(city_id, []) for city_id in cities}

        return cls(cities=cities, routes=routes, adjacency=adjacency)

    def neighbors(self, city_id: str) -> list[tuple[str, Route]]:
        result: list[tuple[str, Route]] = []
        for route_id in self.adjacency.get(city_id, []):
            route = self.routes[route_id]
            other = route.city_b if route.city_a == city_id else route.city_a
            result.append((other, route))
        return result
