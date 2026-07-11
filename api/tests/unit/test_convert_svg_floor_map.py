"""SVG path를 x/y 벡터 JSON으로 변환하는 로직의 단위 테스트."""

import pytest

from scripts.convert_svg_floor_map import (
    parse_path_points,
    parse_path_subpaths,
    polygon_centroid,
)


def test_M_L_H_V_Z_path를_xy_좌표로_변환한다():
    points = parse_path_points("M 10 20 H 30 V 40 L 10 40 Z")

    assert points == [
        {"x": 10.0, "y": 20.0},
        {"x": 30.0, "y": 20.0},
        {"x": 30.0, "y": 40.0},
        {"x": 10.0, "y": 40.0},
    ]


def test_사각형_면적중심을_계산한다():
    centroid = polygon_centroid(
        [
            {"x": 0.0, "y": 0.0},
            {"x": 4.0, "y": 0.0},
            {"x": 4.0, "y": 2.0},
            {"x": 0.0, "y": 2.0},
        ]
    )

    assert centroid["x"] == pytest.approx(2.0)
    assert centroid["y"] == pytest.approx(1.0)


def test_곡선_path는_조용히_왜곡하지_않고_거부한다():
    with pytest.raises(ValueError, match="지원하지 않는"):
        parse_path_points("M 0 0 C 1 1 2 2 3 3")


def test_여러_M_명령은_서로_끊어진_subpath로_보존한다():
    subpaths = parse_path_subpaths("M 0 0 H 10 M 20 0 H 30")

    assert subpaths == [
        [{"x": 0.0, "y": 0.0}, {"x": 10.0, "y": 0.0}],
        [{"x": 20.0, "y": 0.0}, {"x": 30.0, "y": 0.0}],
    ]
