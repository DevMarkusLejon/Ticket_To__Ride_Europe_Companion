"""Deterministic baseline policies. Only public state and the acting hand are used."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import fsum

from .algorithms import risk_adjusted_cost, shortest_path
from .game_state import GameState
from .models import Route
from .simulation import COLORS, LOCO, Game, Player, Ticket, components

NAMES = ("regular", "hoarder", "finish", "fast", "long", "adaptive")
Move = tuple[str, str | None]


@dataclass(frozen=True)
class Policy:
    name: str
    wait: int
    face_up_loco: str = "needed"
    stations: bool = True
    cheapest: bool = False

    @classmethod
    def named(cls, name: str) -> Policy:
        if name not in NAMES:
            raise ValueError(f"Unknown policy {name}")
        return cls(name, {"hoarder": 21, "finish": 18, "long": 5}.get(name, 0))


def path_to_ticket(game: Game, player: Player, ticket: Ticket,
                   borrowed: tuple[Route, ...] = (), planned: tuple[Route, ...] = (), *,
                   include_claimed: bool = False) -> list[Route] | None:
    state = game.state
    if borrowed:
        owners = dict(state.route_owner)
        owners.update((route.route_id, player.id) for route in borrowed)
        state = GameState(state.board, owners, state.player_count)
    planned_ids = {route.route_id for route in planned}

    def cost(route: Route) -> float:
        if state.route_owner.get(route.route_id) == player.id:
            return 0
        if route.route_id in planned_ids:
            return 0.1
        return risk_adjusted_cost(route)

    try:
        path, _ = shortest_path(state, ticket.source_city, ticket.target_city, player.id, cost)
    except ValueError:
        return None
    return [state.board.routes[r] for r in path if include_claimed or r not in state.route_owner]


def choose_tickets(policy: Policy, game: Game, player: Player, offer: list[Ticket],
                   opening: bool) -> list[Ticket]:
    if policy.cheapest or policy.name in ("hoarder", "long"):
        return sorted(offer, key=lambda t: t.points)[:2 if opening else 1]
    _, borrowed = game.ticket_result(player)
    paths = {t: path_to_ticket(game, player, t, borrowed) for t in offer}

    def value(group: tuple[Ticket, ...]) -> float:
        if any(paths[t] is None for t in group):
            return float("-inf")
        tracks = {r for t in group for r in paths[t]}
        return sum(t.points for t in group) - 1.6 * fsum(risk_adjusted_cost(r) for r in tracks)

    if not opening:
        return [max(offer, key=lambda t: value((t,)))]
    pair = max(combinations(offer, 2), key=value)
    kept = list(pair)
    if policy.name in ("regular", "adaptive"):
        for t in offer:
            if t not in kept and value((*kept, t)) >= value(tuple(kept)) - 2:
                kept.append(t)
    return kept


class Bot:
    def __init__(self, policy: Policy):
        self.policy = policy
        self.turns = 0
        self.plan_key = None
        self.targets: list[Route] = []
        self.ticket_paths: dict[Ticket, list[Route]] = {}
        self.borrowed: tuple[Route, ...] = ()
        self.plan_mode = "opening"
        self.station_city: str | None = None
        self.all_done = False
        self.failed_tunnels: dict[str, int] = {}

    def claim(self, game: Game, p: Player, route: Route) -> Move:
        if not game.claim(p, route):
            self.failed_tunnels[route.route_id] = self.tunnel_budget(p, route)
            return "tunnel_failed", route.route_id
        return "claim", route.route_id

    @staticmethod
    def tunnel_budget(p: Player, route: Route) -> int:
        colored = max(p.hand[c] for c in COLORS) if route.color.value == "gray" else p.hand[route.color.value]
        return colored + p.hand[LOCO]

    def plan(self, game: Game, p: Player) -> None:
        key = (len(game.state.route_owner), tuple(len(q.stations) for q in game.players), len(p.tickets))
        if key == self.plan_key:
            return
        self.plan_key = key
        done, borrowed = game.ticket_result(p)
        self.borrowed = borrowed
        pending = [t for t in p.tickets if t not in done]
        self.all_done = not pending
        self.station_city = None
        if self.policy.stations and len(p.stations) < 3 and pending:
            network = components(p.routes + list(borrowed))
            def area(city: str) -> str:
                return network.get(city, city)
            gaps = {frozenset((area(t.source_city), area(t.target_city))) for t in pending}
            occupied = {city for q in game.players for city in q.stations}
            for rid, owner in game.state.route_owner.items():
                route = game.state.board.routes[rid]
                if owner != p.id and frozenset((area(route.city_a), area(route.city_b))) in gaps:
                    city = next((c for c in (route.city_a, route.city_b) if c not in occupied), None)
                    if city:
                        self.station_city = city
                        break
        self.targets = []
        self.ticket_paths = {}
        for ticket in sorted(pending, key=lambda t: -t.points):
            path = path_to_ticket(game, p, ticket, borrowed, tuple(self.targets), include_claimed=True)
            if path is None:
                continue
            missing = [r for r in path if r.route_id not in game.state.route_owner]
            if missing and sum(r.length for r in missing) <= p.trains:
                self.ticket_paths[ticket] = path
                self.targets.extend(r for r in missing if r not in self.targets)

    def draw(self, game: Game, p: Player, targets: list[Route]) -> bool:
        colors = sorted(COLORS, key=lambda c: (-int(p.hand[c] < 8), -p.hand[c]))
        demand = [r.color.value for r in targets if r.color.value != "gray"
                  and p.hand[r.color.value] < r.length]
        preferred = list(dict.fromkeys(demand + colors))
        need_wild = any(r.ferry_locomotives_required > p.hand[LOCO] for r in targets)
        if self.policy.face_up_loco == "always" or (self.policy.face_up_loco == "needed" and need_wild):
            preferred.insert(0, LOCO)
        return game.deck.draw(p.hand, preferred)

    def take_turn(self, game: Game, p: Player, final: bool) -> Move:
        self.turns += 1
        if self.turns <= self.policy.wait and not final and self.draw(game, p, []):
            self.plan_mode = "waiting"
            return "draw", None
        rush = self.policy.name == "adaptive" and any(
            q.hand.total() >= 14 for q in game.players if q is not p)
        pursuing = self.policy.name not in ("hoarder", "long") and not rush
        targets = []
        self.plan_mode = "rush" if rush else "long_routes"
        if pursuing:
            self.plan_mode = "tickets"
            self.plan(game, p)
            if self.station_city and p.payment(len(p.stations) + 1):
                game.station(p, self.station_city)
                return "station", self.station_city
            if (self.all_done and self.policy.name in ("regular", "adaptive") and not final
                    and p.trains >= 15 and min(q.trains for q in game.players) >= 9 and game.tickets):
                offer = game.draw_tickets()
                game.keep_tickets(p, offer, choose_tickets(self.policy, game, p, offer, False), opening=False)
                return "tickets", None
            targets = self.targets

        def affordable(r: Route) -> bool:
            previous = self.failed_tunnels.get(r.route_id)
            if previous is not None and self.tunnel_budget(p, r) <= previous:
                return False
            return bool(p.payment(r.length, r.color.value, r.ferry_locomotives_required))

        def claim_priority(r: Route) -> tuple:
            # Prefer high route points, then avoid tunnel risk and scarce wilds.
            return (r.length, not r.is_tunnel, -r.ferry_locomotives_required)

        playable = [r for r in targets if affordable(r)]
        if playable:
            return self.claim(game, p, max(playable, key=claim_priority))
        if targets and not final and self.draw(game, p, targets):
            return "draw", None
        available = [r for r in game.state.board.routes.values()
                     if r.length <= p.trains and game.state.is_claimable(r.route_id, p.id)]
        best = max((r for r in available if affordable(r)), key=claim_priority, default=None)
        if best and (final or best.length >= min(4, p.trains) or p.hand.total() >= 12):
            return self.claim(game, p, best)
        if self.draw(game, p, sorted(available, key=claim_priority, reverse=True)[:3]):
            return "draw", None
        if best:
            return self.claim(game, p, best)
        if game.tickets:
            offer = game.draw_tickets()
            game.keep_tickets(p, offer, choose_tickets(self.policy, game, p, offer, False), opening=False)
            return "tickets", None
        if self.policy.stations and len(p.stations) < 3 and p.payment(len(p.stations) + 1):
            occupied = {city for q in game.players for city in q.stations}
            game.station(p, next(city for city in game.state.board.cities if city not in occupied))
            return "station", p.stations[-1]
        return "pass", None
