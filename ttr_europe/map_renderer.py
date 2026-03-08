from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_board(path: Path) -> tuple[list[dict], list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["cities"], payload["routes"]


def _project(
    lon: float,
    lat: float,
    *,
    min_lon: float,
    max_lon: float,
    min_lat: float,
    max_lat: float,
    width: int,
    height: int,
    padding: int,
) -> tuple[float, float]:
    usable_w = width - (2 * padding)
    usable_h = height - (2 * padding)

    x_ratio = (lon - min_lon) / (max_lon - min_lon) if max_lon != min_lon else 0.5
    y_ratio = (lat - min_lat) / (max_lat - min_lat) if max_lat != min_lat else 0.5

    x = padding + (x_ratio * usable_w)
    # Flip y so north is up.
    y = height - padding - (y_ratio * usable_h)
    return x, y


def render_board_svg(
    *,
    board_json_path: str | Path,
    output_svg_path: str | Path,
    width: int = 1400,
    height: int = 900,
    padding: int = 50,
) -> None:
    board_path = Path(board_json_path)
    cities, routes = _load_board(board_path)

    city_coords: dict[str, tuple[float, float]] = {}
    lons: list[float] = []
    lats: list[float] = []
    for city in cities:
        if "longitude" not in city or "latitude" not in city:
            raise ValueError(
                "Board JSON must include city longitude/latitude to render a map."
            )
        lon = float(city["longitude"])
        lat = float(city["latitude"])
        city_coords[city["city_id"]] = (lon, lat)
        lons.append(lon)
        lats.append(lat)

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    projected: dict[str, tuple[float, float]] = {}
    for city in cities:
        lon, lat = city_coords[city["city_id"]]
        projected[city["city_id"]] = _project(
            lon,
            lat,
            min_lon=min_lon,
            max_lon=max_lon,
            min_lat=min_lat,
            max_lat=max_lat,
            width=width,
            height=height,
            padding=padding,
        )

    route_lines: list[str] = []
    for route in routes:
        ax, ay = projected[route["city_a"]]
        bx, by = projected[route["city_b"]]
        route_lines.append(
            (
                f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" '
                'stroke="#3b3f44" stroke-width="2" stroke-opacity="0.75" />'
            )
        )

    city_points: list[str] = []
    city_labels: list[str] = []
    for city in cities:
        x, y = projected[city["city_id"]]
        city_points.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="#f4f1de" stroke="#111" stroke-width="1.1" />'
        )
        city_labels.append(
            (
                f'<text x="{x + 6:.2f}" y="{y - 6:.2f}" font-size="11" '
                'font-family="Verdana, Arial, sans-serif" fill="#111">'
                f'{city["name"]}</text>'
            )
        )

    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="#dceaf4" />',
            '<g id="routes">',
            *route_lines,
            "</g>",
            '<g id="cities">',
            *city_points,
            "</g>",
            '<g id="labels">',
            *city_labels,
            "</g>",
            "</svg>",
        ]
    )

    output_path = Path(output_svg_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ttr_europe.map_renderer",
        description="Render a Ticket to Ride board JSON with coordinates as an SVG map.",
    )
    parser.add_argument(
        "--board",
        default="data/europe_board_from_csv.json",
        help="Path to board JSON that includes city longitude/latitude.",
    )
    parser.add_argument(
        "--out",
        default="data/europe_board_map.svg",
        help="Output SVG path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    render_board_svg(board_json_path=args.board, output_svg_path=args.out)
    print(f"Map written to: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
