from pathlib import Path

import pytest

from ttr_europe import BoardGraph, GameState, risk_adjusted_cost, shortest_path, trains_by_color
from ttr_europe.__main__ import main as cli_main


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


def test_cli_main_returns_success(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_main(
        [
            "--board",
            str(BOARD_PATH),
            "--start",
            "paris",
            "--target",
            "amsterdam",
            "--player",
            "me",
            "--claim",
            "bruxelles_amsterdam:opponent",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "paris_frankfurt -> frankfurt_amsterdam" in captured.out


def test_trains_by_color_breakdown_for_shortest_path() -> None:
    board = BoardGraph.from_json(BOARD_PATH)
    state = GameState(board=board)

    # Force the red Paris-Bruxelles segment to make the color split deterministic.
    state.claim_route("paris_bruxelles_2", player_id="opponent")

    route_ids, cost = shortest_path(
        state=state,
        start_city="paris",
        target_city="amsterdam",
        player_id="me",
    )

    assert route_ids == ["paris_bruxelles_1", "bruxelles_amsterdam"]
    assert cost == 3.0
    assert trains_by_color(state, route_ids) == {"black": 1, "red": 2}


def test_cli_main_can_print_train_breakdown(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_main(
        [
            "--board",
            str(BOARD_PATH),
            "--start",
            "paris",
            "--target",
            "amsterdam",
            "--player",
            "me",
            "--claim",
            "paris_bruxelles_2:opponent",
            "--breakdown",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "train_breakdown:" in captured.out
    assert "black: 1" in captured.out
    assert "red: 2" in captured.out
    assert "total_trains: 3" in captured.out
