from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Callable

from .game_state import GameState
from .models import Route

CostFn = Callable[[Route], float]


def default_build_cost(route: Route) -> float:
    return float(route.length)


def risk_adjusted_cost(route: Route) -> float:
    tunnel_premium = 0.75 if route.is_tunnel else 0.0
    ferry_premium = route.ferry_locomotives_required * 0.8
    return route.length + tunnel_premium + ferry_premium


def shortest_path(
    state: GameState,
    start_city: str,
    target_city: str,
    player_id: str,
    cost_fn: CostFn = default_build_cost,
) -> tuple[list[str], float]:
    if start_city == target_city:
        return [start_city], 0.0

    frontier: list[tuple[float, str]] = [(0.0, start_city)]
    best_cost: dict[str, float] = {start_city: 0.0}
    predecessor: dict[str, tuple[str, str]] = {}

    while frontier:
        current_cost, city = heapq.heappop(frontier)
        if city == target_city:
            break

        if current_cost > best_cost.get(city, float("inf")):
            continue

        for neighbor, route in state.board.neighbors(city):
            if not state.is_available(route.route_id, player_id=player_id):
                continue

            candidate = current_cost + cost_fn(route)
            if candidate < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = candidate
                predecessor[neighbor] = (city, route.route_id)
                heapq.heappush(frontier, (candidate, neighbor))

    if target_city not in predecessor and target_city != start_city:
        raise ValueError(f"No available path from {start_city} to {target_city}")

    route_path: list[str] = []
    city_cursor = target_city
    while city_cursor != start_city:
        prev_city, route_id = predecessor[city_cursor]
        route_path.append(route_id)
        city_cursor = prev_city

    route_path.reverse()
    return route_path, best_cost[target_city]


def trains_by_color(state: GameState, route_ids: list[str]) -> dict[str, int]:
    breakdown: dict[str, int] = defaultdict(int)
    for route_id in route_ids:
        route = state.board.routes[route_id]
        breakdown[route.color.value] += route.length
    return dict(sorted(breakdown.items()))
