"""Rebuild the spectator replay from a matched deal at each tournament table."""

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from experiments.europe_wait_comparison import PAIRS_PER_TABLE, TABLES
from ttr_europe.models import POINTS_BY_LENGTH
from ttr_europe.simulation import load_europe
from ttr_europe.strategies import Policy
from ttr_europe.tournament import play

HERE = Path(__file__).resolve().parent


def record(board, tickets, opponents, seed, seat, wait):
    lineup = [replace(Policy.named("finish"), wait=wait), *(Policy.named(n) for n in opponents)]
    lineup = lineup[-seat:] + lineup[:-seat]
    replay = {"seed": seed, "seat": seat, "policies": [p.name for p in lineup], "events": []}
    previous_done = []
    hands = []

    def observe(game, turn, move):
        nonlocal previous_done
        deck = game.deck
        supply = {"market": deck.market.copy(), "deck_available": bool(deck.pile or deck.discard)}
        if turn == 0:
            deck.recorded_picks = []
            replay["opening_supply"] = supply
            hands.extend(p.hand.copy() for p in game.players)
            replay["opening_hands"] = [dict(hand) for hand in hands]
            replay["initial"] = [[tickets.index(t) for t in p.tickets] for p in game.players]
            return
        actor = (turn - 1) % len(lineup)
        p = game.players[actor]
        kind, target = move
        event = {"kind": kind, "supply": supply}
        if target is not None:
            event["target"] = target
        if kind == "draw":
            event["picks"] = [asdict(pick) for pick in deck.recorded_picks]
            deck.recorded_picks.clear()
        if kind == "tickets":
            event["kept"] = tickets.index(p.tickets[-1])
        if kind in ("claim", "station", "tunnel_failed"):
            event["spent"] = dict(hands[actor] - p.hand)
        hands[actor] = p.hand.copy()
        event["hand_after"] = dict(+p.hand)
        event["hand"] = p.hand.total()
        # A new opponent track can complete a ticket through an existing station.
        done = [tickets.index(t) for t in game.ticket_result(game.players[seat])[0]]
        if done != previous_done:
            event["done"] = previous_done = done
        replay["events"].append(event)

    result = play(board, tickets, lineup, seed, observe=observe)
    replay["trigger"] = result.actions - len(lineup)
    replay["scores"] = [asdict(s) for s in result.scores]
    top = max(s.rank() for s in result.scores)
    replay["winners"] = [i for i, s in enumerate(result.scores) if s.rank() == top]
    return replay


def make_data(deal):
    board, tickets = load_europe()
    return {
        "cities": {c.city_id: c.name for c in board.cities.values()},
        "routes": {r.route_id: dict(a=r.city_a, b=r.city_b, length=r.length,
                                    points=POINTS_BY_LENGTH[r.length], color=r.color.value,
                                    tunnel=r.is_tunnel, ferry=r.ferry_locomotives_required)
                   for r in board.routes.values()},
        "tickets": [[t.source_city, t.target_city, t.points] for t in tickets],
        "tables": {table: {wait: record(board, tickets, opponents, first + deal, deal % 4, wait)
                           for wait in (18, 25)} for table, (opponents, first) in TABLES.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deal", type=int, default=0, help="Tournament deal index, 0–4095")
    parser.add_argument("--out", type=Path, default=HERE.parent / "docs" / "strategy-replay.html")
    parser.add_argument("--fragment-out", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 <= args.deal < PAIRS_PER_TABLE:
        parser.error(f"Choose a deal from 0 to {PAIRS_PER_TABLE - 1}")
    data = json.dumps(make_data(args.deal), ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
    fragment = (HERE / "replay-view.html").read_text(encoding="utf-8").replace("/*REPLAY_DATA*/null", data)
    style = (HERE / "replay-page.css").read_text(encoding="utf-8")
    args.out.write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        '<title>Europe · Strategy replay</title><style>' + style
                        + '</style><body>' + fragment + '</body></html>', encoding="utf-8")
    if args.fragment_out:
        args.fragment_out.write_text(fragment, encoding="utf-8")
    print(f"Wrote six replays to {args.out}")


if __name__ == "__main__":
    main()
