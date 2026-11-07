# Can a ticketless Hoarder win on the Europe board?

**Yes. Against three Regulars, the Hoarder won 8 of 80 games outright and completed zero tickets in 7 of those wins.** It triggered the final round in all 80. Hoard and Finish won 37 of 80 against the same three opponents and completed an average of 1.99 of its two tickets. These are results for the bots described below. [All 37 matchups and score breakdowns](../experiments/europe_pilot_results.csv)

## Reproduce the experiment

From the repository root, run the following commands with Python 3.12. No downloaded data or third-party simulation libraries are needed. The tests use pytest.

```bash
python -m pytest -q
python -m ttr_europe.tournament --candidate hoarder --games 80 --seed 10000 --clock-control --csv hoarder.csv
python -m experiments.europe_pilot --out pilot.csv
```

For a short replay, use `--games 3 --seed 10016` with the Hoarder command. In the third game the candidate plays in seat 3, counting clockwise from the starting player. It scores 93 points, 94 of them from routes, despite failing both tickets. The game ends after 143 individual turns.

## Four-player results

Each cell shows outright wins out of 80 with a 95% Wilson interval for the win probability, rounded to whole percentages. The mixed table has one Adaptive, one Long-route player, and one Hoarder. Among the six policies, Hoard and Finish had the highest observed win count against Regulars and Fast Builders and tied Fast Builder at the mixed table. The intervals quantify deal-to-deal uncertainty under these policies. Several comparisons are close enough that a fresh batch could change their order.

| Candidate | Three Regulars | Three Fast Builders | Mixed table |
|---|---:|---:|---:|
| Regular | 20/80 (17–35%) | 18/80 (15–33%) | 40/80 (39–61%) |
| Hoarder, 21 turns | 8/80 (5–19%) | 11/80 (8–23%) | 19/80 (16–34%) |
| Long-route player | 2/80 (1–9%) | 2/80 (1–9%) | 9/80 (6–20%) |
| Fast Builder | 22/80 (19–38%) | 25/80 (22–42%) | 50/80 (52–72%) |
| Adaptive | 4/80 (2–12%) | 14/80 (11–27%) | 11/80 (8–23%) |
| Hoard and Finish, 25 turns | 37/80 (36–57%) | 28/80 (26–46%) | 50/80 (52–72%) |

### What changed when the game ended early?

With a Hoarder, the three Regulars averaged **87.5 points** over **37.1 rounds**. Replacing it with a fourth Regular on the same deals extended the average to **44.8 rounds** and raised those same three seats to **105.3 points**.

In each four-Regular replay we also scored the table after exactly as many individual turns as its paired Hoarder game, or at its own finish if earlier. The three opponents averaged **78.2 points at that cutoff**. Letting the same regular-player game continue was worth 27.1 points per opponent on average. The 9.3-point difference between 78.2 at the cutoff and 87.5 against an actual Hoarder shows that changing the fourth player's moves also mattered. This control measures the effect of extra turns along the replay's trajectory. It cannot identify how much of a human Hoarder's advantage comes from the clock.

| Candidate against three Regulars | Mean total | Mean route points | Mean tickets completed / kept | Mean rounds |
|---|---:|---:|---:|---:|
| Regular | 108.0 | 56.5 | 5.16 / 5.35 | 44.8 |
| Hoarder | 85.7 | 85.7 | 0.05 / 2 | 37.1 |
| Fast Builder | 102.6 | 72.0 | 2.00 / 2 | 40.9 |
| Hoard and Finish | 109.0 | 78.7 | 1.99 / 2 | 39.5 |

### Wait time, stations and locomotives

Training compared waits of 12, 18, 21, and 25 personal turns against regular and mixed tables. The rule selected the wait with the most wins at its weaker table, then the highest combined wins, then the shorter wait. It selected **25**, the upper edge of the tested range. On held-out deals against Regulars, waiting 18 won 34/80 and waiting 25 won 37/80. That small gap leaves the best duration open.

On those same evaluation deals, the 25-turn bot won 37/80 when avoiding face-up locomotives, 37/80 when targeting them for ferries, and 36/80 when always taking one if offered. Disabling its stations yielded 42/80. Keeping its two lowest-value tickets yielded 38/80. These switches changed only the candidate. The result file includes intervals for each setting. No setting was retuned after seeing the evaluation results.

| Seats, all opponents Regular | Hoarder wins | Hoard and Finish wins | Games per cell |
|---|---:|---:|---:|
| 2 | 31 (52%) | 46 (77%) | 60 |
| 3 | 16 (27%) | 33 (55%) | 60 |
| 4 | 8 (10%) | 37 (46%) | 80 |
| 5 | 6 (10%) | 18 (30%) | 60 |

## Policies and measurement

| Policy | Opening tickets and play |
|---|---|
| Regular | Starts building toward tickets as soon as it can. May keep additional opening tickets if their marginal cost is low. Draws another offer after finishing everything while it has at least 15 trains and all players have at least 9. |
| Hoarder | Keeps the two lowest point liabilities. Draws for 21 personal turns, then pursues long affordable routes anywhere on the board. Tickets can complete incidentally. |
| Hoard and Finish | Selects two tickets jointly using their points and estimated cost of the union of their paths. Draws for the specified wait, builds toward them, then races for long routes. |
| Fast Builder | Uses the same two-ticket selection and building logic with a zero-turn wait. |
| Long-route player | Uses the Hoarder's ticket and route choices with a five-turn wait. |
| Adaptive | Plays like a Regular while opponents have small hands. On a turn when another hand contains at least 14 cards, it switches to long routes and forgoes optional ticket draws. It can switch back. |

Ticket players rank an opening group by ticket points minus 1.6 times estimated construction cost. A tunnel adds 0.75 to that estimated cost and each required locomotive adds 0.8. Actual claims always use the rules. The planner uses Dijkstra paths, reuses owned track at zero cost and favors overlap between pending tickets. It pursues affordable planned routes in descending length. It builds a station when borrowing a single opposing track immediately finishes a pending ticket. Final scoring considers every consistent assignment of one track per station across all tickets. Bots do not plan multi-station rescues in advance.

Draws favor visible needed colors, then sets the player already holds. A wild remains a legal blind draw under every setting. The default bot takes a face-up wild preferentially when its target routes call for more ferry locomotives. When supply allows, the Hoarder draws throughout its wait. A final turn or an empty supply can force it to build earlier. Long-route play favors the longest affordable route, then an ordinary track over a tunnel, then fewer mandatory wilds. Ties use board order. After a failed tunnel, a bot waits for a larger payment budget before retrying that track. The bots see their own offers and cards, public track claims, station locations, train counts, the market and opponents' hand sizes. They do not inspect future draws or opponents' ticket identities.

**Sampling.** The pilot records 2,456 candidate games across 37 matchups plus 80 paired clock-control replays. Tuning used seeds 2000–2031. Four-player evaluation and one-setting-at-a-time comparisons used 10000–10079. Other player counts used 11000–11059. Each matchup rotates the whole lineup one seat per seed, so each bot spends equal time in each starting position. Reusing seeds pairs the starting deals across policies. Counts from different settings are correlated.

**Scoring.** A round in the CSV is total actions divided by the number of seats. Everyone gets one final turn after the trigger, including the triggering player. Winners are ranked by final score, completed tickets, unused stations, then possession of the European Express bonus. Any remaining shared first is recorded under `ties` and excluded from `wins`. The longest trail can revisit a city but can use each owned track only once. Tied longest trails each earn ten points. Borrowed tracks only count toward tickets. The CSV's `triggered` column is the fraction of games where the candidate triggered the end.

**Supply edge case.** With fewer than three non-wilds available, a full legal five-card display can be impossible. When every possible replacement would again show three wilds, the simulator leaves the market empty and permits blind draws. It refills the display when cards return. A 2,000-action guard raises an error on a stalled game. It never awards a win at the cap.

## Board and rule audit

The starting checkout passed 8 tests. Its route CSV had 90 city pairs, omitted parallel lanes, and stored only a colored/neutral flag. The converter assigned gray to every track. The classic board has **47 cities and 101 tracks** across 90 pairs, including 11 doubles. There are 18 tunnel tracks, 13 ferry tracks, 37 neutral tracks, and eight of each printed color. We transcribed color and parallel-lane information from the board and checked lengths and special markings. The six-car ferry joins Palermo to Smyrna and requires two locomotives. Berlin to Danzig needs four trains. Zürich to Marseille is a pink tunnel. The project retains its historical spellings in city IDs. [Classic board reference, page 1](https://www.thechalkface.net/resources/ticket_to_ride.pdf) · [Board photograph](https://github.com/leonsi7/ticket-to-ride-europe/blob/03c8f35ae4a80abf4caab4a9ec7737a15c37b150/map.jpg)

The deck has **40 regular and six long tickets**. The card photograph puts Stockholm–Wien at 11 points, correcting the CSV's 10. The simulator deals one long and three regular tickets, removes rejected opening tickets from play, and returns rejected later tickets to the bottom of the regular deck. No route length comes from ticket points. The referenced upstream data project lists no license at the inspected revision. Its images served as inspection references. The experiment uses the existing local data with factual corrections and does not vendor upstream code or artwork. [Ticket photograph](https://github.com/leonsi7/ticket-to-ride-europe/blob/03c8f35ae4a80abf4caab4a9ec7737a15c37b150/destinations.jpg) · [Upstream tree](https://github.com/leonsi7/ticket-to-ride-europe/tree/03c8f35ae4a80abf4caab4a9ec7737a15c37b150)

The rules implementation targets the classic Europe edition. The handoff's linked PDF is a third-party rules summary. The original Days of Wonder rulebook supplies the tunnel treatment for all-wild payments, the starting-ticket discard rule, station assignment, final-turn order, and the Europe tiebreaks. Deterministic tests cover those cases, train and card conservation, and replay consistency. The path CLI still uses its original sample by default. [Classic rulebook](https://ia904604.us.archive.org/21/items/ticket-to-ride-europe-rules/TicketToRideEurope-rules.pdf) · [Rulebook text](https://nastola.bg/wp-content/uploads/2020/06/Ticker-to-ride-Europe-%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0-%D0%BD%D0%B0-%D0%B0%D0%BD%D0%B3%D0%BB%D0%B8%D0%B9%D1%81%D0%BA%D0%B8.pdf)

## Outside comparison and next measurement

The original video's four-player US Hoarder won 83% against its Regulars. A separate Europe result already exists in the Leiden thesis. Its Table 8 reports 79 wins in 100 for HoardCards at 74.67 mean points. The opponents averaged 37.87–47.59. Our Hoarder scored 85.7 against three Regulars averaging 87.5 and won 8 of 80. The thesis uses a combined ticket deck and different opponents. Those differences prevent a direct replication claim. [Video at the strategy definitions](https://www.youtube.com/watch?v=E05MAjOyEaI&t=94s) · [Leiden thesis, sections 3 and 6.2](https://theses.liacs.nl/pdf/2021-2022-OunmaaM.pdf)

The next measurement worth collecting is a small set of real four-player classic Europe games with scores and ticket completion recorded both near round 37 and at the finish. Final scores alone cannot validate the opponents' pace. The present pilot establishes what these bots do on this board. Human win probabilities and the best wait remain open.
