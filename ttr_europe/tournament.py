"""Run a seeded table from the repository root with python -m ttr_europe.tournament."""

from __future__ import annotations

import argparse
import csv
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import mean

from .board_graph import BoardGraph
from .models import POINTS_BY_LENGTH
from .simulation import Game, Score, Ticket, load_europe, scores
from .strategies import NAMES, Bot, Move, Policy, choose_tickets


@dataclass
class PlayedGame:
    game: Game
    scores: list[Score]
    actions: int
    trigger: int
    checkpoint: list[Score] | None


def play(board: BoardGraph, tickets: list[Ticket], policies: list[Policy], seed: int,
         checkpoint_at: int | None = None, *,
         observe: Callable[[Game, int, Move], None] | None = None) -> PlayedGame:
    game = Game(board, tickets, len(policies), seed)
    bots = [Bot(policy) for policy in policies]
    for p, policy, offer in zip(game.players, policies, game.opening_offers):
        game.keep_tickets(p, offer, choose_tickets(policy, game, p, offer, True), opening=True)
    if observe:
        observe(game, 0, ("deal", None))

    final_action = None
    checkpoint = None
    for action in range(1, 2001):
        seat = (action - 1) % len(bots)
        player = game.players[seat]
        move = bots[seat].take_turn(game, player, final_action is not None)
        if observe:
            observe(game, action, move)
        if action == checkpoint_at:
            checkpoint = scores(game)
        if action == final_action:
            return PlayedGame(game, scores(game), action, trigger, checkpoint)
        if final_action is None and player.trains <= 2:
            trigger = seat
            final_action = action + len(bots)
    raise RuntimeError(f"No natural end after 2000 actions, seed {seed}, policies {policies}")


@dataclass
class Observation:
    seed: int
    seat: int
    actions: int
    rounds: float
    triggered: bool
    win: bool
    tie: bool
    points: int
    route_points: int
    kept: int
    completed: int
    stations: int
    opponent_points: float
    control_rounds: float | None = None
    control_cut_points: float | None = None
    control_end_points: float | None = None


def tournament(board: BoardGraph, tickets: list[Ticket], candidate: Policy, opponents: list[Policy],
               games: int, seed: int, clock_control: bool = False) -> list[Observation]:
    rows = []
    seats = len(opponents) + 1
    for i in range(games):
        seat = i % seats
        # Rotate the whole lineup, preserving relative opponent order at a mixed table.
        lineup = [candidate, *opponents]
        lineup = lineup[-seat:] + lineup[:-seat]
        result = play(board, tickets, lineup, seed + i)
        player = result.game.players[seat]
        score = result.scores[seat]
        ranks = [s.rank() for s in result.scores]
        top = max(ranks)
        first = score.rank() == top
        row = Observation(
            seed=seed + i, seat=seat, actions=result.actions, rounds=result.actions / seats,
            triggered=result.trigger == seat,
            win=first and ranks.count(top) == 1, tie=first and ranks.count(top) > 1,
            points=score.points, route_points=sum(POINTS_BY_LENGTH[r.length] for r in player.routes),
            kept=len(player.tickets), completed=score.completed, stations=len(player.stations),
            opponent_points=mean(s.points for j, s in enumerate(result.scores) if j != seat),
        )
        if clock_control:
            lineup[seat] = Policy.named("regular")
            control = play(board, tickets, lineup, seed + i, checkpoint_at=result.actions)
            cut = control.checkpoint or control.scores  # Control may already have ended.
            row.control_cut_points = mean(s.points for j, s in enumerate(cut) if j != seat)
            row.control_end_points = mean(s.points for j, s in enumerate(control.scores) if j != seat)
            row.control_rounds = control.actions / seats
        rows.append(row)
    return rows


def wilson(wins: int, n: int) -> tuple[float, float]:
    z = 1.96
    rate = wins / n
    scale = 1 + z * z / n
    mid = rate + z * z / (2 * n)
    half = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n**2))
    return max(0, (mid - half) / scale), min(1, (mid + half) / scale)


def summary(rows: list[Observation]) -> dict:
    n = len(rows)
    wins = sum(r.win for r in rows)
    low, high = wilson(wins, n)
    result = dict(games=n, wins=wins, ties=sum(r.tie for r in rows),
                  wins_without_tickets=sum(r.win and r.completed == 0 for r in rows),
                  win_pct=round(100 * wins / n, 1), low95=round(low * 100, 1),
                  high95=round(high * 100, 1))
    for field in ("points", "route_points", "completed", "kept", "stations", "rounds", "triggered",
                  "opponent_points", "control_rounds", "control_cut_points", "control_end_points"):
        if getattr(rows[0], field) is not None:
            result[field] = round(mean(getattr(r, field) for r in rows), 3)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evaluate one Europe policy against 1–4 opponents.")
    parser.add_argument("--candidate", choices=NAMES, default="hoarder")
    parser.add_argument("--opponents", nargs="+", choices=NAMES, default=["regular"] * 3)
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=10000)
    parser.add_argument("--wait", type=int, help="Candidate's initial draw-only turns")
    parser.add_argument("--face-up-loco", choices=("needed", "avoid", "always"), default="needed")
    parser.add_argument("--cheapest", action="store_true", help="Keep the lowest-value offered tickets")
    parser.add_argument("--no-stations", action="store_true", help="Disable candidate station building")
    parser.add_argument("--clock-control", action="store_true", help="Replay with a regular in the candidate seat")
    parser.add_argument("--csv", type=Path, help="Write per-game observations")
    args = parser.parse_args(argv)
    if not 1 <= len(args.opponents) <= 4 or args.games <= 0 or (args.wait is not None and args.wait < 0):
        parser.error("Supply 1–4 opponents, positive games and a nonnegative wait")
    policy = Policy.named(args.candidate)
    policy = replace(policy, wait=policy.wait if args.wait is None else args.wait,
                     face_up_loco=args.face_up_loco, stations=not args.no_stations, cheapest=args.cheapest)
    board, tickets = load_europe()
    rows = tournament(board, tickets, policy, [Policy.named(n) for n in args.opponents],
                      args.games, args.seed, args.clock_control)
    stats = summary(rows)
    print(f"{policy.name} vs {', '.join(args.opponents)} | {len(rows)} games | "
          f"seeds {args.seed}-{args.seed + args.games - 1}")
    print(f"Wait {policy.wait} turns | face-up locomotives {policy.face_up_loco} | "
          f"stations {'on' if policy.stations else 'off'}")
    print(f"Outright wins {stats['wins']}/{len(rows)} ({stats['win_pct']}%, "
          f"95% interval {stats['low95']}-{stats['high95']}%) | shared firsts {stats['ties']} | "
          f"wins with zero completed tickets {stats['wins_without_tickets']}")
    print(f"Mean score {stats['points']:.1f} | route points {stats['route_points']:.1f} | "
          f"tickets completed/kept {stats['completed']:.2f}/{stats['kept']:.2f}")
    print(f"Mean rounds {stats['rounds']:.1f} | triggered end {100 * stats['triggered']:.1f}% | "
          f"opponent score {stats['opponent_points']:.1f}")
    if args.clock_control:
        print(f"Regular replay: mean opponent score at cutoff {stats['control_cut_points']:.1f}, "
              f"at finish {stats['control_end_points']:.1f} after {stats['control_rounds']:.1f} rounds")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=asdict(rows[0]))
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)


if __name__ == "__main__":
    main()
