from __future__ import annotations

import argparse
import sys

from . import BoardGraph, GameState, risk_adjusted_cost, shortest_path, trains_by_color


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ttr_europe",
        description="Find shortest route paths on a Ticket to Ride: Europe board model.",
    )
    parser.add_argument(
        "--board",
        default="data/europe_sample_board.json",
        help="Path to board JSON file (default: data/europe_sample_board.json).",
    )
    parser.add_argument("--start", required=True, help="Start city id.")
    parser.add_argument("--target", required=True, help="Target city id.")
    parser.add_argument("--player", default="me", help="Current player id.")
    parser.add_argument(
        "--cost",
        choices=("build", "risk"),
        default="build",
        help="Cost model to use: build (route length) or risk (tunnel/ferry premiums).",
    )
    parser.add_argument(
        "--claim",
        action="append",
        default=[],
        metavar="ROUTE_ID:PLAYER_ID",
        help="Pre-claim a route, repeatable (e.g. --claim bruxelles_amsterdam:opponent).",
    )
    parser.add_argument(
        "--breakdown",
        action="store_true",
        help="Print train-count breakdown by color for the selected shortest path.",
    )
    return parser


def parse_claim(claim_arg: str) -> tuple[str, str]:
    route_id, sep, player_id = claim_arg.partition(":")
    if not sep or not route_id or not player_id:
        raise ValueError(f"Invalid --claim value '{claim_arg}'. Expected ROUTE_ID:PLAYER_ID.")
    return route_id, player_id


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        board = BoardGraph.from_json(args.board)
        state = GameState(board=board)

        for claim_arg in args.claim:
            route_id, player_id = parse_claim(claim_arg)
            state.claim_route(route_id, player_id=player_id)

        cost_fn = risk_adjusted_cost if args.cost == "risk" else None
        route_ids, cost = shortest_path(
            state=state,
            start_city=args.start,
            target_city=args.target,
            player_id=args.player,
            **({"cost_fn": cost_fn} if cost_fn is not None else {}),
        )
    except Exception as exc:  # pragma: no cover - thin CLI wrapper
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("route_ids:", " -> ".join(route_ids) if route_ids else "(none)")
    print("cost:", cost)
    if args.breakdown:
        breakdown = trains_by_color(state, route_ids)
        total_trains = sum(breakdown.values())
        print("train_breakdown:")
        for color, trains in breakdown.items():
            print(f"  {color}: {trains}")
        print("total_trains:", total_trains)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
