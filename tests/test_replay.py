import csv
from collections import Counter

from experiments.replay import HERE, make_data


def test_replay_matches_published_pairs_from_a_rotated_seat():
    data = make_data(7)
    with (HERE / "europe_wait_pairs.csv").open() as f:
        rows = {(r["table"], int(r["seed"])): r for r in csv.DictReader(f)}
    for table, pair in data["tables"].items():
        assert pair[18]["initial"] == pair[25]["initial"]
        for wait, game in pair.items():
            row = rows[table, game["seed"]]
            seat = game["seat"]
            assert seat == int(row["seat"]) == 3
            assert len(game["events"]) == int(row[f"actions_{wait}"])
            assert game["scores"][seat]["points"] == int(row[f"points_{wait}"])
            assert (game["winners"] == [seat]) == bool(int(row[f"win_{wait}"]))
            kept = [set(tickets) for tickets in game["initial"]]
            completed = [[] for _ in kept]
            trains = [45] * 4
            hands = [Counter(cards) for cards in game["opening_hands"]]
            assert all(hand.total() == 4 for hand in hands)
            for turn, event in enumerate(game["events"], 1):
                hand = hands[(turn - 1) % 4]
                hand.update(pick["card"] for pick in event.get("picks", []))
                hand.subtract(event.get("spent", {}))
                assert hand == Counter(event["hand_after"])
                assert hand.total() == event["hand"]
                if event["kind"] == "tunnel_failed":
                    assert not event["spent"]
                if event["kind"] == "claim":
                    trains[(turn - 1) % 4] -= data["routes"][event["target"]]["length"]
                if turn < game["trigger"]:
                    assert min(trains) > 2
                if turn == game["trigger"]:
                    assert trains[(turn - 1) % 4] <= 2
                if event["kind"] == "tickets":
                    kept[(turn - 1) % 4].add(event["kept"])
                completed = event.get("completed_by_seat", completed)
                assert all(set(done) <= held for done, held in zip(completed, kept, strict=True))
            assert [len(done) for done in completed] == [s["completed"] for s in game["scores"]]
            assert len(completed[seat]) == int(row[f"completed_{wait}"])


def test_ticket_plans_use_tracks_available_before_the_move():
    data = make_data(0)
    for pair in data["tables"].values():
        for game in pair.values():
            plans = [{} for _ in game["initial"]]
            held = [set(tickets) for tickets in game["initial"]]
            owners = {}
            for index, event in enumerate(game["events"]):
                seat = index % 4
                if "plan" in event:
                    plans[seat] = event["plan"]
                plan = plans[seat]
                if game["policies"][seat] in ("hoarder", "long"):
                    assert plan["mode"] in ("waiting", "long_routes")
                for ticket, path in plan.get("paths", {}).items():
                    assert ticket in held[seat]
                    city, destination, _ = data["tickets"][ticket]
                    for track in path:
                        route = data["routes"][track]
                        assert city in (route["a"], route["b"])
                        assert track not in owners or owners[track] == seat or track in plan["borrowed"]
                        city = route["b"] if city == route["a"] else route["a"]
                    assert city == destination
                if event["kind"] == "claim":
                    owners[event["target"]] = seat
                if event["kind"] == "tickets":
                    held[seat].add(event["kept"])

    # P3's last decision still uses the coastal track when P1 takes it on move 141.
    events = data["tables"]["regular"][25]["events"]
    blocked = events[140]
    assert blocked["kind"] == "claim" and blocked["target"] == "marseille_barcelona"
    previous = next(e["plan"] for e in reversed(events[2:140:4]) if "plan" in e)
    assert previous["paths"][27][0] == blocked["target"]
    assert events[142]["plan"]["paths"][27][:3] == [
        "pamplona_barcelona", "paris_pamplona_2", "paris_marseille",
    ]
