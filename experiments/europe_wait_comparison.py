"""Compare two Hoard and Finish waits on matched deals from the three pilot tables."""

import argparse
import csv
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from math import sqrt
from pathlib import Path
from statistics import NormalDist, mean, variance

from experiments.europe_pilot import FAST, MIXED, REGULAR
from ttr_europe.simulation import load_europe
from ttr_europe.strategies import Policy
from ttr_europe.tournament import tournament

PAIRS_PER_TABLE = 4096
BATCH_SIZE = 64  # A multiple of four keeps seat rotation continuous across batches.
TABLES = {
    "regular": (REGULAR, 200000),
    "fast": (FAST, 210000),
    "mixed": (MIXED, 220000),
}


def play_batch(job):
    name, seed = job
    board, tickets = load_europe()
    opponents = [Policy.named(n) for n in TABLES[name][0]]
    policy = Policy.named("finish")
    early = tournament(board, tickets, replace(policy, wait=18), opponents, BATCH_SIZE, seed)
    late = tournament(board, tickets, replace(policy, wait=25), opponents, BATCH_SIZE, seed)
    rows = []
    for a, b in zip(early, late, strict=True):
        if (a.seed, a.seat) != (b.seed, b.seat):
            raise ValueError("Mismatched deals or seats")
        row = dict(table=name, seed=a.seed, seat=a.seat)
        for wait, game in ((18, a), (25, b)):
            row.update({
                f"win_{wait}": int(game.win), f"tie_{wait}": int(game.tie),
                f"points_{wait}": game.points, f"completed_{wait}": game.completed,
                f"actions_{wait}": game.actions,
            })
        rows.append(row)
    return rows


def summarize(rows):
    """Estimate the paired difference with a fixed, equal share for each seat."""
    by_seat = defaultdict(list)
    for row in rows:
        by_seat[row["seat"]].append(row["win_25"] - row["win_18"])
    strata = list(by_seat.values())
    difference = mean(mean(group) for group in strata)
    se = sqrt(sum(variance(group) / len(group) for group in strata)) / len(strata)
    z = NormalDist().inv_cdf(1 - 0.05 / (2 * len(TABLES)))
    delta = [value for group in strata for value in group]
    return {
        "pairs": len(rows),
        "wins_18": sum(r["win_18"] for r in rows),
        "wins_25": sum(r["win_25"] for r in rows),
        "only_18": delta.count(-1),
        "only_25": delta.count(1),
        "difference_pp": round(100 * difference, 3),
        "lower_pp": round(100 * (difference - z * se), 3),
        "upper_pp": round(100 * (difference + z * se), 3),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Paired deal CSV")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    jobs = [(name, start + offset) for offset in range(0, PAIRS_PER_TABLE, BATCH_SIZE)
            for name, (_, start) in TABLES.items()]
    rows = []
    with ProcessPoolExecutor(args.workers) as pool:
        for i, batch in enumerate(pool.map(play_batch, jobs), start=1):
            rows.extend(batch)
            if i % 24 == 0:
                print(f"{len(rows):,} of {len(jobs)*BATCH_SIZE:,} pairs complete", flush=True)
    rows.sort(key=lambda r: (r["table"], r["seed"]))
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    for name in TABLES:
        print(name, summarize([r for r in rows if r["table"] == name]))


if __name__ == "__main__":
    main()
