"""Reproduce the pilot table with python -m experiments.europe_pilot --out pilot.csv."""

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from ttr_europe.simulation import load_europe
from ttr_europe.strategies import Policy
from ttr_europe.tournament import summary, tournament

REGULAR = ("regular",) * 3
FAST = ("fast",) * 3
MIXED = ("adaptive", "long", "hoarder")
WAITS = (12, 18, 21, 25)


def evaluate(job):
    phase, policy, table, games, seed, clock = job
    board, tickets = load_europe()
    rows = tournament(board, tickets, policy, [Policy.named(n) for n in table], games, seed, clock)
    return dict(phase=phase, candidate=policy.name, wait=policy.wait, opponents="/".join(table),
                face_up_loco=policy.face_up_loco, stations_enabled=policy.stations,
                cheapest=policy.cheapest, first_seed=seed, **summary(rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    finish = Policy.named("finish")
    tune = [("tuning", replace(finish, wait=w), table, 32, 2000, False)
            for w in WAITS for table in (REGULAR, MIXED)]
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(evaluate, tune))

        def training_rank(wait):
            wins = [r["wins"] for r in results if r["wait"] == wait]
            return min(wins), sum(wins), -wait

        tuned = replace(finish, wait=max(WAITS, key=training_rank))
        evaluation = []
        policies = [Policy.named(n) for n in ("regular", "hoarder", "long", "fast", "adaptive")]
        for table in (REGULAR, FAST, MIXED):
            for policy in [*policies, tuned]:
                clock = table == REGULAR and policy.name == "hoarder"
                evaluation.append(("evaluation", policy, table, 80, 10000, clock))
        variations = [replace(tuned, face_up_loco="avoid"), replace(tuned, face_up_loco="always"),
                      replace(tuned, stations=False), replace(tuned, cheapest=True)]
        if tuned.wait != 18:
            variations.append(finish)
        evaluation.extend(("sensitivity", p, REGULAR, 80, 10000, False) for p in variations)
        for seats in (2, 3, 5):
            for p in (Policy.named("hoarder"), tuned):
                evaluation.append(("player_count", p, ("regular",) * (seats - 1), 60, 11000, False))
        results.extend(pool.map(evaluate, evaluation))

    fields = list(dict.fromkeys(key for row in results for key in row))
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"Wrote {len(results)} matchups to {args.out}. Selected wait: {tuned.wait}.")


if __name__ == "__main__":
    main()
