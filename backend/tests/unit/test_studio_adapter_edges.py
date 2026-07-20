import pytest

from scripts.seed.studio_adapter import _scope_edges


def test_scope_edges_preserves_polyline_and_recomputes_length():
    edges = [{
        "id": "edge-1",
        "from": "a",
        "to": "b",
        "length_m": 999,  # Studio가 준 값은 버리고 geometry로 다시 잰다
        "geometry": {
            "source": [{"x": 1, "y": 1}, {"x": 2, "y": 2}],
            "local_m": [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 4}],
        },
    }]

    result = _scope_edges("floor", edges)[0]

    assert result["id"] == "floor:edge-1"
    assert result["from"] == "floor:a"
    # 꺾인 복도의 중간점까지 모두 보존된다(양 끝점만 남기면 경로·길이가 유실된다).
    assert result["geometry_local_m"] == [
        {"x": 0, "y": 0},
        {"x": 3, "y": 0},
        {"x": 3, "y": 4},
    ]
    assert result["length_m"] == pytest.approx(7)
