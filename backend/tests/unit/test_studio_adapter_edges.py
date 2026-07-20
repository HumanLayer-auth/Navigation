import pytest

from scripts.seed.studio_adapter import _scope_edges


def test_scope_edges_preserves_polyline_and_recomputes_length():
    edges = [{
        "id": "edge-1",
        "from": "a",
        "to": "b",
        "length_m": 999,
        "geometry": {
            "source": [{"x": 1, "y": 1}, {"x": 2, "y": 2}],
            "local_m": [{"x": 0, "y": 0}, {"x": 3, "y": 0}, {"x": 3, "y": 4}],
        },
    }]
    align = ((2, 0, 10), (0, 2, -5))

    result = _scope_edges("floor", edges, align)[0]

    assert result["id"] == "floor:edge-1"
    assert result["from"] == "floor:a"
    assert result["geometry_local_m"] == [
        {"x": 10, "y": -5},
        {"x": 16, "y": -5},
        {"x": 16, "y": 3},
    ]
    assert result["length_m"] == pytest.approx(14)
