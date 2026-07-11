"""SVG 변환 JSON 보완 로직의 단위 테스트."""

import json

import pytest

from scripts.load_dataset import _edge_row, _find_vector_dataset, _node_row


# 원본 좌표와 위경도가 없어도 노드 행을 생성할 수 있는지 검증한다.
def test_노드의_원본좌표와_위경도는_선택값이다():
    row = _node_row(
        {
            "id": "A",
            "type": "corridor",
            "position": {"local_m": {"x": 1.0, "y": 2.0}},
        },
        "floor-1",
    )

    assert row == (
        "A",
        "floor-1",
        "corridor",
        None,
        1.0,
        2.0,
        None,
        None,
        None,
        None,
    )


# 간선 경로선이 생략되면 양 끝 노드 좌표로 보완하는지 검증한다.
def test_간선_경로선이_없으면_노드_좌표로_보완한다():
    row = _edge_row(
        {"id": "AB", "from": "A", "to": "B"},
        "floor-1",
        {
            "A": {"x": 0.0, "y": 0.0},
            "B": {"x": 3.0, "y": 4.0},
        },
    )

    assert row[4] == pytest.approx(5.0)
    assert json.loads(row[6]) == [
        {"x": 0.0, "y": 0.0},
        {"x": 3.0, "y": 4.0},
    ]


# 간선 거리가 생략되면 경로선의 구간별 길이 합을 계산하는지 검증한다.
def test_간선_거리가_없으면_경로선_전체_길이를_계산한다():
    row = _edge_row(
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
        "floor-1",
        {},
    )

    assert row[4] == pytest.approx(8.0)


# 양방향 여부가 생략되면 참으로 저장되는지 검증한다.
def test_양방향_여부의_기본값은_참이다():
    row = _edge_row(
        {"id": "AB", "from": "A", "to": "B", "length_m": 1.0},
        "floor-1",
        {"A": {"x": 0.0, "y": 0.0}, "B": {"x": 1.0, "y": 0.0}},
    )

    assert row[5] == 1


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

    result = _find_vector_dataset(
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
        _find_vector_dataset(
            tmp_path,
            building_id="building-1",
            floor_id="floor-1",
        )
