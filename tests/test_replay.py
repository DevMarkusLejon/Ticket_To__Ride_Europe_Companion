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
