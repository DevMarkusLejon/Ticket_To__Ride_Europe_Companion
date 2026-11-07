# Does waiting 25 turns beat waiting 18?

For the simulated Hoard and Finish player, **25 turns won more often against three Regulars, 18 won more often against three Fast Builders, and the mixed table showed no clear advantage**. Each comparison used 4,096 fresh deals played twice, for 24,576 four-player games. The candidate kept the same two opening tickets and played from the same seat in each pair.

| Opponents | 18-turn outright wins | 25-turn outright wins | Difference, 25 minus 18 | Simultaneous 95% interval |
|---|---:|---:|---:|---:|
| Three Regulars | 1,533 (37.4%) | 2,170 (53.0%) | +15.6 pp | +13.2 to +17.9 pp |
| Three Fast Builders | 1,290 (31.5%) | 1,166 (28.5%) | −3.0 pp | −5.1 to −1.0 pp |
| Adaptive, Long-route player, Hoarder | 2,458 (60.0%) | 2,461 (60.1%) | +0.1 pp | −2.3 to +2.4 pp |

Against Regulars, 1,147 deals produced a win only with the longer wait and 510 produced a win only with the shorter wait. Against Fast Builders those counts reversed direction, 567 to 691. At the mixed table they were 814 to 811. The near-identical mixed win rates hide a change of outcome on 1,625 deals.

Ticket completion helps explain where the shorter wait mattered. Against Fast Builders, the chance of finishing both tickets fell from 95.1% to 87.2% with the longer wait, and the candidate's mean score fell from 97.1 to 94.8. Against Regulars, both waits finished both tickets in over 95% of games, and the longer wait raised the mean score from 103.9 to 108.4. At the mixed table the longer wait finished both tickets less often (70.3% versus 89.6%) yet scored slightly more on average (89.6 versus 88.4).

## How to reproduce it

Run from the repository root with Python 3.12.10. The script prints the win counts and intervals and writes one row per matched pair. [Comparison script](../experiments/europe_wait_comparison.py) · [Per-deal results](../experiments/europe_wait_pairs.csv)

```bash
python -m experiments.europe_wait_comparison --workers 8 --out wait_pairs.csv
```

The comparisons use the [pilot simulator and policies](europe-tournament.md). Only the candidate's initial draw-only period changes. Seeds were 200000–204095 for Regulars, 210000–214095 for Fast Builders, and 220000–224095 for the mixed table. Each wait played 1,024 games in each seat per table. Opponents stayed in the pilot's relative order. Shared first places after all tiebreaks were excluded from outright wins. For 18 and 25 turns respectively, there were 1 and 0 such ties against Regulars, 14 and 7 against Fast Builders, and 4 and 2 at the mixed table.

For each deal, subtract the 18-turn win indicator from the 25-turn win indicator. The reported difference averages these values equally over the four seats. The standard error comes from the sample variance of the paired differences within each seat. Normal intervals use a two-sided Bonferroni correction across the three tables for approximately 95% simultaneous coverage. These intervals describe uncertainty across random deals for the specified bots. The tournament tests two waits and gives no estimate of how often human opponents would play like these tables.
