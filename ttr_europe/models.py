from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RouteColor(str, Enum):
    BLACK = "black"
    BLUE = "blue"
    GREEN = "green"
    RED = "red"
    WHITE = "white"
    ORANGE = "orange"
    PINK = "pink"
    YELLOW = "yellow"
    GRAY = "gray"


@dataclass(frozen=True)
class City:
    city_id: str
    name: str


@dataclass(frozen=True)
class Route:
    route_id: str
    city_a: str
    city_b: str
    length: int
    color: RouteColor
    is_tunnel: bool = False
    ferry_locomotives_required: int = 0
    parallel_group: str | None = None

    @property
    def has_ferry(self) -> bool:
        return self.ferry_locomotives_required > 0
