# Ticket_To__Ride_Europe_Companion

Python route planning and seeded strategy tournaments for classic **Ticket to Ride: Europe**.

## Run the strategy experiment

From the repository root, using Python 3.10 or newer, play 20 four-player games with a Hoarder against three Regulars.

```bash
python -m ttr_europe.tournament --candidate hoarder --games 20 --seed 10000
```

The [pilot results and board audit](docs/europe-tournament.md) cover six policies, alternate seats, game length, ticketless wins, and the rule assumptions.

The [18-turn versus 25-turn tournament](docs/europe-wait-comparison.md) compares the two waits on 12,288 matched deals across three opponent tables.

## What this implements

- **BoardGraph** (immutable): cities, routes, and adjacency lists loaded from JSON.
- **GameState** (mutable): claimed route ownership overlay for path calculations.
- **Algorithms**:
  - Dijkstra shortest path with pluggable cost functions.
  - Default build cost (`route.length`).
  - Risk-adjusted cost (adds tunnel/ferry premiums).

This architecture supports route planning, blocking-aware pathing, and simulation workflows.

## Data model

Each route captures:

- `route_id`
- `city_a` / `city_b`
- `length`
- `color`
- `is_tunnel`
- `ferry_locomotives_required`
- `parallel_group` (for double-routes)

Sample board file: `data/europe_sample_board.json`.

## Quick start

```python
from ttr_europe import BoardGraph, GameState, shortest_path, risk_adjusted_cost

board = BoardGraph.from_json("data/europe_sample_board.json")
state = GameState(board=board)

# Opponent claims a route.
state.claim_route("bruxelles_amsterdam", player_id="opponent")

path, cost = shortest_path(
    state,
    start_city="paris",
    target_city="amsterdam",
    player_id="me",
)
print(path, cost)

path_risk, cost_risk = shortest_path(
    state,
    start_city="paris",
    target_city="zurich",
    player_id="me",
    cost_fn=risk_adjusted_cost,
)
print(path_risk, cost_risk)
```

## Test

```bash
python -m pytest -q
```

## Run as CLI

You can now run route queries directly:

```bash
python -m ttr_europe --start paris --target amsterdam
```

Include train-color breakdown for the shortest path:

```bash
python -m ttr_europe --start paris --target amsterdam --breakdown
```

Example with blocked route and risk-adjusted cost:

```bash
python -m ttr_europe \
  --start paris \
  --target zurich \
  --player me \
  --claim bruxelles_amsterdam:opponent \
  --cost risk
```

## Convert CSV data to JSON

To convert `cities.csv`, `routes.csv`, and `destinations.csv` into JSON files:

```bash
python -m ttr_europe.csv_converter
```

This writes:

- `data/europe_board_from_csv.json` (compatible with `BoardGraph.from_json`)
- `data/europe_destination_tickets_from_csv.json`
- `data/europe_sample_board_from_destinations.json` (sample-board-format template)
- `data/europe_sample_board_from_routes.json` (sample-board-format template from `routes.csv`)

Use `europe_board_from_csv.json` for the full board and `europe_destination_tickets_from_csv.json` for the deck. Each row of `routes.csv` specifies the color and cost of one physical track. Double tracks have two rows. `destinations.csv` identifies the six long tickets explicitly.

`europe_sample_board_from_destinations.json` is a legacy conversion example. It treats ticket endpoints as edges and maps points to lengths, which produces fictitious routes. The tournament loads the two audited files above. The converter still accepts older route CSVs with a `Colored` flag and marks their unknown colors in the routes-based sample.

## Render board map

You can render the coordinate-based board JSON as an SVG map:

```bash
python -m ttr_europe.map_renderer --board data/europe_board_from_csv.json --out data/europe_board_map.svg
```

Open `data/europe_board_map.svg` in your browser.
