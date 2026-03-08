from pathlib import Path

from ttr_europe.map_renderer import render_board_svg


def test_render_board_svg_outputs_svg(tmp_path: Path) -> None:
    board_path = Path("data/europe_board_from_csv.json")
    out_path = tmp_path / "board.svg"

    render_board_svg(board_json_path=board_path, output_svg_path=out_path)

    assert out_path.exists()
    contents = out_path.read_text(encoding="utf-8")
    assert "<svg" in contents
    assert 'id="routes"' in contents
    assert "Paris" in contents
