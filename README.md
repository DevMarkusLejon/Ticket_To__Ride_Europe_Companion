# Ticket_To__Ride_Europe_Companion

Python graph tooling for modeling **Ticket to Ride: Europe** routes as an undirected weighted multigraph.

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

In `europe_sample_board_from_destinations.json`, route `length` is inferred from
ticket `points` using:

- 1 -> 1
- 2 -> 2
- 4 -> 3
- 7 -> 4
- 15 -> 6
- 21 -> 8

Routes with ticket points outside this mapping are emitted with `length: 0` and
`needs_manual_length: true` so you can fill them manually.

In `europe_sample_board_from_routes.json`, routes that came from `Colored=true` are
marked with `needs_manual_color: true` so you can fill color values.

## Render board map

You can render the coordinate-based board JSON as an SVG map:

```bash
python -m ttr_europe.map_renderer --board data/europe_board_from_csv.json --out data/europe_board_map.svg
```

Open `data/europe_board_map.svg` in your browser.
