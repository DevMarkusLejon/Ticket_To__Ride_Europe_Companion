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
