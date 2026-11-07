import json
from pathlib import Path

from ttr_europe import BoardGraph
from ttr_europe.csv_converter import convert_csvs


def test_convert_csvs_creates_loadable_board_and_tickets(tmp_path: Path) -> None:
    board_out = tmp_path / "board.json"
    tickets_out = tmp_path / "tickets.json"
    destination_board_template_out = tmp_path / "destination_board_template.json"
    routes_sample_board_out = tmp_path / "routes_sample_board.json"

    convert_csvs(
        cities_csv_path=Path("cities.csv"),
        routes_csv_path=Path("routes.csv"),
        destinations_csv_path=Path("destinations.csv"),
        board_json_path=board_out,
        destinations_json_path=tickets_out,
        destination_board_template_json_path=destination_board_template_out,
        routes_sample_board_json_path=routes_sample_board_out,
    )

    board = BoardGraph.from_json(board_out)
    assert len(board.cities) == 47
    assert len(board.routes) == 101
    assert tickets_out.exists()
    assert destination_board_template_out.exists()

    template = json.loads(destination_board_template_out.read_text(encoding="utf-8"))
    assert len(template["cities"]) == 47
    assert len(template["routes"]) == 46

    route_by_id = {route["route_id"]: route for route in template["routes"]}
    assert route_by_id["cadiz_stockholm"]["ticket_points"] == 21
    assert route_by_id["cadiz_stockholm"]["length"] == 8
    assert route_by_id["lisboa_danzic"]["ticket_points"] == 20
    assert route_by_id["lisboa_danzic"]["length"] == 0
    assert route_by_id["lisboa_danzic"]["needs_manual_length"] is True

    routes_sample_board = json.loads(routes_sample_board_out.read_text(encoding="utf-8"))
    assert len(routes_sample_board["cities"]) == 47
    assert len(routes_sample_board["routes"]) == 101
    first_route = routes_sample_board["routes"][0]
    assert "needs_manual_color" not in first_route
    assert first_route["color"] == "blue"

    for generated, checked_in in [
        (board_out, "europe_board_from_csv.json"),
        (tickets_out, "europe_destination_tickets_from_csv.json"),
        (routes_sample_board_out, "europe_sample_board_from_routes.json"),
    ]:
        assert json.loads(generated.read_text()) == json.loads((Path("data") / checked_in).read_text())


def test_older_csv_preserves_unknown_colors_and_route_ids(tmp_path):
    routes = tmp_path / "routes.csv"
    routes.write_text("Source,Target,Carriages,Colored,Tunnel,Engine\n"
                      "Madrid,Pamplona,3,true,true,0\n"
                      "Madrid,Pamplona,3,true,true,0\n")
    sample = tmp_path / "sample.json"
    convert_csvs(cities_csv_path="cities.csv", routes_csv_path=routes, destinations_csv_path="destinations.csv",
                 board_json_path=tmp_path / "board.json", routes_sample_board_json_path=sample)
    tracks = json.loads(sample.read_text())["routes"]
    assert [r["route_id"] for r in tracks] == ["madrid_pamplona_1", "madrid_pamplona_2"]
    assert all(r["needs_manual_color"] for r in tracks)
