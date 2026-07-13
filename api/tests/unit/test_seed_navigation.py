"""시드 스크립트의 입력 보완·벡터 JSON 탐색 로직 단위 테스트."""

import json

import pytest

from scripts.seed_navigation import edge_geometry_and_length, find_vector_dataset


# 간선 경로선이 생략되면 양 끝 노드 좌표로 보완하는지 검증한다.
def test_간선_경로선이_없으면_노드_좌표로_보완한다():
    geometry, length_m = edge_geometry_and_length(
        {"id": "AB", "from": "A", "to": "B"},
        {
            "A": {"x": 0.0, "y": 0.0},
            "B": {"x": 3.0, "y": 4.0},
        },
    )

    assert length_m == pytest.approx(5.0)
    assert geometry == [
        {"x": 0.0, "y": 0.0},
        {"x": 3.0, "y": 4.0},
    ]


# 간선 거리가 생략되면 경로선의 구간별 길이 합을 계산하는지 검증한다.
def test_간선_거리가_없으면_경로선_전체_길이를_계산한다():
    _, length_m = edge_geometry_and_length(
        {
            "id": "AB",
            "from": "A",
            "to": "B",
            "geometry_local_m": [
                {"x": 0.0, "y": 0.0},
                {"x": 3.0, "y": 4.0},
                {"x": 6.0, "y": 4.0},
            ],
        },
        {},
    )

    assert length_m == pytest.approx(8.0)


def test_벡터_디렉터리에서_건물과_층이_일치하는_JSON을_찾는다(tmp_path):
    other = tmp_path / "other-building" / "1f.json"
    target = tmp_path / "thehyundai-seoul" / "1f.json"
    other.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    other.write_text(
        json.dumps({"building_id": "other", "floor_id": "floor-1"}),
        encoding="utf-8",
    )
    target.write_text(
        json.dumps(
            {"building_id": "thehyundai-seoul", "floor_id": "floor-1"}
        ),
        encoding="utf-8",
    )

    result = find_vector_dataset(
        tmp_path,
        building_id="thehyundai-seoul",
        floor_id="floor-1",
    )

    assert result["building_id"] == "thehyundai-seoul"


def test_동일한_건물과_층_JSON이_중복되면_거부한다(tmp_path):
    payload = json.dumps({"building_id": "building-1", "floor_id": "floor-1"})
    (tmp_path / "a.json").write_text(payload, encoding="utf-8")
    (tmp_path / "b.json").write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="여러 개"):
        find_vector_dataset(
            tmp_path,
            building_id="building-1",
            floor_id="floor-1",
        )
