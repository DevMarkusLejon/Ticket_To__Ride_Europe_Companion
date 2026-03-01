from __future__ import annotations

from dataclasses import dataclass, field

from .board_graph import BoardGraph


@dataclass
class GameState:
    board: BoardGraph
    route_owner: dict[str, str] = field(default_factory=dict)

    def claim_route(self, route_id: str, player_id: str) -> None:
        if route_id not in self.board.routes:
            raise KeyError(f"Unknown route id: {route_id}")
        if route_id in self.route_owner:
            raise ValueError(f"Route {route_id} already claimed")
        self.route_owner[route_id] = player_id

    def is_available(self, route_id: str, player_id: str | None = None) -> bool:
        owner = self.route_owner.get(route_id)
        if owner is None:
            return True
        return player_id is not None and owner == player_id
