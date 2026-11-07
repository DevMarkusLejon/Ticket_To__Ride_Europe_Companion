"""Rules used by the classic Europe strategy tournament."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from random import Random

from .board_graph import BoardGraph
from .game_state import GameState
from .models import POINTS_BY_LENGTH, Route, RouteColor

COLORS = tuple(c.value for c in RouteColor if c != RouteColor.GRAY)
LOCO = "locomotive"
DATA = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class Ticket:
    source_city: str
    target_city: str
    points: int
    type: str


def load_europe() -> tuple[BoardGraph, list[Ticket]]:
    board = BoardGraph.from_json(DATA / "europe_board_from_csv.json")
    rows = json.loads((DATA / "europe_destination_tickets_from_csv.json").read_text(encoding="utf-8"))
    tickets = [
        Ticket(row["source_city"], row["target_city"], row["points"], row["type"])
        for row in rows["destination_tickets"]
    ]
    return board, tickets


class TrainDeck:
    def __init__(self, rng: Random):
        self.rng = rng
        self.pile = list(COLORS) * 12 + [LOCO] * 14
        self.rng.shuffle(self.pile)
        self.discard: list[str] = []
        self.market: list[str] = []

    def take(self, count: int) -> list[str]:
        cards = []
        for _ in range(count):
            if not self.pile:
                self.pile, self.discard = self.discard, []
                self.rng.shuffle(self.pile)
            if not self.pile:
                break
            cards.append(self.pile.pop())
        return cards

    def fill_market(self) -> None:
        self.market.extend(self.take(5 - len(self.market)))
        while self.market.count(LOCO) >= 3:
            self.discard.extend(self.market)
            self.market.clear()
            # Hoarding can make a legal five-card display mathematically impossible.
            available = self.pile + self.discard
            if sum(c != LOCO for c in available) < min(5, len(available)) - 2:
                return
            self.market.extend(self.take(5))

    def draw(self, hand: Counter[str], preference: list[str]) -> bool:
        for draw_number in range(2):
            visible = [c for c in self.market if draw_number == 0 or c != LOCO]
            card = next((c for c in preference if c in visible), None)
            if card is None and not (self.pile or self.discard) and visible:
                card = visible[0]
            if card is None:
                blind = self.take(1)
                if not blind:
                    return draw_number > 0
                hand[blind[0]] += 1
            else:
                self.market.remove(card)
                hand[card] += 1
                self.fill_market()
                if card == LOCO:
                    break
        return True


@dataclass
class Player:
    id: str
    hand: Counter[str] = field(default_factory=Counter)
    tickets: list[Ticket] = field(default_factory=list)
    stations: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    trains: int = 45

    def payment(self, cost: int, color: str = "gray", ferries: int = 0) -> list[str]:
        if color == "gray":
            color = max(COLORS, key=self.hand.__getitem__)
        colored = min(self.hand[color], cost - ferries)
        wild = cost - colored
        if self.hand[LOCO] < wild:
            return []
        return [color] * colored + [LOCO] * wild


class Game:
    def __init__(self, board: BoardGraph, tickets: list[Ticket], seats: int, seed: int):
        if not 2 <= seats <= 5:
            raise ValueError("Europe requires two to five players")
        rng = Random(seed)
        self.state = GameState(board, player_count=seats)
        self.deck = TrainDeck(rng)
        self.players = [Player(str(seat)) for seat in range(seats)]
        self.tickets = [t for t in tickets if t.type == "regular"]
        longs = [t for t in tickets if t.type == "long"]
        rng.shuffle(self.tickets)
        rng.shuffle(longs)
        self.opening_offers: list[list[Ticket]] = []
        for p in self.players:
            p.hand.update(self.deck.take(4))
            self.opening_offers.append([longs.pop()] + [self.tickets.pop() for _ in range(3)])
        self.deck.fill_market()

    def keep_tickets(self, player: Player, offer: list[Ticket], kept: list[Ticket], *, opening: bool) -> None:
        minimum = 2 if opening else 1
        if len(set(kept)) != len(kept) or len(kept) < minimum or not set(kept) <= set(offer):
            raise ValueError("Invalid ticket selection")
        player.tickets.extend(kept)
        if not opening:
            self.tickets[:0] = [t for t in offer if t not in kept]

    def draw_tickets(self) -> list[Ticket]:
        return [self.tickets.pop() for _ in range(min(3, len(self.tickets)))]

    def claim(self, player: Player, route: Route, cards: list[str] | None = None,
              max_tunnel_extra: int = 3) -> bool:
        route = self.state.board.routes[route.route_id]
        if player.trains < route.length or not self.state.is_claimable(route.route_id, player.id):
            raise ValueError(f"Unavailable route {route.route_id}")
        if cards is None:
            cards = player.payment(route.length, route.color.value, route.ferry_locomotives_required)
        colored = set(cards) - {LOCO}
        if (len(cards) != route.length or not Counter(cards) <= player.hand
                or len(colored) > 1 or not colored <= set(COLORS)
                or (route.color != RouteColor.GRAY and colored - {route.color.value})
                or cards.count(LOCO) < route.ferry_locomotives_required):
            raise ValueError(f"Cannot pay for {route.route_id}")
        if route.is_tunnel:
            reveal = self.deck.take(3)
            self.deck.discard.extend(reveal)
            color = next(iter(colored), LOCO)
            extra = sum(card in (color, LOCO) for card in reveal)
            remaining = player.hand - Counter(cards)
            matching = min(remaining[color], extra) if color != LOCO else 0
            if extra > max_tunnel_extra or remaining[LOCO] < extra - matching:
                self.deck.fill_market()
                return False
            cards = cards + [color] * matching + [LOCO] * (extra - matching)
        self.state.claim_route(route.route_id, player.id)
        player.hand.subtract(cards)
        self.deck.discard.extend(cards)
        player.trains -= route.length
        player.routes.append(route)
        self.deck.fill_market()
        return True

    def station(self, player: Player, city: str) -> None:
        cost = len(player.stations) + 1
        if city not in self.state.board.cities or any(city in p.stations for p in self.players):
            raise ValueError(f"Unavailable station city {city}")
        cards = player.payment(cost)
        if cost > 3 or not cards:
            raise ValueError("Cannot build station")
        player.stations.append(city)
        player.hand.subtract(cards)
        self.deck.discard.extend(cards)
        self.deck.fill_market()

    def loans(self, player: Player, city: str) -> list[Route]:
        return [route for _, route in self.state.board.neighbors(city)
                if self.state.route_owner.get(route.route_id) not in (None, player.id)]

    def ticket_result(self, player: Player) -> tuple[list[Ticket], tuple[Route, ...]]:
        options = [self.loans(player, city) or [None] for city in player.stations]
        best = (-1, -1)
        for choices in product(*options):
            loans = tuple(r for r in choices if r is not None)
            network = components(player.routes + list(loans))
            done = [t for t in player.tickets if network.get(t.source_city, t.source_city)
                    == network.get(t.target_city, t.target_city)]
            rank = (sum(t.points for t in done), len(done))
            if rank > best:
                best, completed, borrowed = rank, done, loans
        return completed, borrowed


def components(routes: list[Route]) -> dict[str, str]:
    neighbors: dict[str, list[str]] = defaultdict(list)
    for r in routes:
        neighbors[r.city_a].append(r.city_b)
        neighbors[r.city_b].append(r.city_a)
    labels = {}
    for start in neighbors:
        if start in labels:
            continue
        stack = [start]
        labels[start] = start
        while stack:
            for city in neighbors[stack.pop()]:
                if city not in labels:
                    labels[city] = start
                    stack.append(city)
    return labels


def longest_trail(routes: list[Route]) -> int:
    neighbors: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for i, r in enumerate(routes):
        neighbors[r.city_a].append((r.city_b, 1 << i, r.length))
        neighbors[r.city_b].append((r.city_a, 1 << i, r.length))

    def length(city: str, used: int) -> int:
        return max((n + length(other, used | bit) for other, bit, n in neighbors[city]
                    if not used & bit), default=0)

    return max((length(city, 0) for city in neighbors), default=0)


@dataclass(frozen=True)
class Score:
    points: int
    completed: int
    unused_stations: int
    express: bool

    def rank(self) -> tuple[int, int, int, bool]:
        return self.points, self.completed, self.unused_stations, self.express


def scores(game: Game) -> list[Score]:
    trails = [longest_trail(p.routes) for p in game.players]
    result = []
    for p, trail in zip(game.players, trails):
        done, _ = game.ticket_result(p)
        ticket_points = 2 * sum(t.points for t in done) - sum(t.points for t in p.tickets)
        express = trail > 0 and trail == max(trails)
        unused = 3 - len(p.stations)
        points = sum(POINTS_BY_LENGTH[r.length] for r in p.routes)
        result.append(Score(points + ticket_points + 4 * unused + 10 * express,
                            len(done), unused, express))
    return result
