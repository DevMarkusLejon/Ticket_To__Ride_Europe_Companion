from pathlib import Path

import pytest

from ttr_europe import BoardGraph, GameState, risk_adjusted_cost, shortest_path


BOARD_PATH = Path("data/europe_sample_board.json")


def test_loads_multigraph_and_neighbors() -> None:
    board = BoardGraph.from_json(BOARD_PATH)
    assert len(board.cities) == 5
    assert len(board.routes) == 6

    paris_neighbors = [route.route_id for _, route in board.neighbors("paris")]
    assert "paris_bruxelles_1" in paris_neighbors
    assert "paris_bruxelles_2" in paris_neighbors


def test_shortest_path_respects_claimed_routes() -> None:
    board = BoardGraph.from_json(BOARD_PATH)
    state = GameState(board=board)

    # Opponent blocks the direct low-cost route option from Bruxelles to Amsterdam.
    state.claim_route("bruxelles_amsterdam", player_id="opponent")

    route_ids, cost = shortest_path(
        state,
        start_city="paris",
        target_city="amsterdam",
        player_id="me",
    )

    assert route_ids == ["paris_frankfurt", "frankfurt_amsterdam"]
    assert cost == 5.0


def test_risk_adjusted_cost_penalizes_tunnels_and_ferries() -> None:
    board = BoardGraph.from_json(BOARD_PATH)
    state = GameState(board=board)

    route_ids, cost = shortest_path(
        state,
        start_city="paris",
        target_city="zurich",
        player_id="me",
        cost_fn=risk_adjusted_cost,
    )

    assert route_ids == ["paris_frankfurt", "frankfurt_zurich"]
    assert cost == pytest.approx(6.55)
