from __future__ import annotations

from dataclasses import dataclass, field

from .board_graph import BoardGraph


@dataclass
class GameState:
    board: BoardGraph
    route_owner: dict[str, str] = field(default_factory=dict)
    player_count: int | None = None

    def claim_route(self, route_id: str, player_id: str) -> None:
        if route_id not in self.board.routes:
            raise KeyError(f"Unknown route id: {route_id}")
        if route_id in self.route_owner:
            raise ValueError(f"Route {route_id} already claimed")
        if not self.is_claimable(route_id, player_id):
            raise ValueError(f"Parallel route for {route_id} is closed")
        self.route_owner[route_id] = player_id

    def is_claimable(self, route_id: str, player_id: str | None) -> bool:
        if route_id in self.route_owner:
            return False
        if self.player_count is None:
            return True
        route = self.board.routes[route_id]
        if route.parallel_group:
            for sibling in self.board.adjacency[route.city_a]:
                owner = self.route_owner.get(sibling)
                if owner is not None and self.board.routes[sibling].parallel_group == route.parallel_group:
                    if self.player_count < 4 or owner == player_id:
                        return False
        return True

    def is_available(self, route_id: str, player_id: str | None = None) -> bool:
        owner = self.route_owner.get(route_id)
        if owner is None:
            return self.is_claimable(route_id, player_id)
        return player_id is not None and owner == player_id
