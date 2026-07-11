"""최단 경로 HTTP API 통합 테스트."""

from tests.conftest import BUILDING_ID, FLOOR_NAME


def _first_edge(api_client) -> dict:
    graph = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}/graph"
    ).json()
    return graph["edges"][0]


def test_최단_경로_조회(api_client):
    edge = _first_edge(api_client)

    response = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}/route",
        params={
            "start_node_id": edge["from"],
            "end_node_id": edge["to"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path_found"] is True
    assert body["node_ids"][0] == edge["from"]
    assert body["node_ids"][-1] == edge["to"]
    assert len(body["edge_ids"]) >= 1
    assert body["total_distance_m"] >= 0


def test_존재하지_않는_출발_노드_400(api_client):
    edge = _first_edge(api_client)

    response = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}/route",
        params={
            "start_node_id": "nonexistent",
            "end_node_id": edge["to"],
        },
    )

    assert response.status_code == 400
    assert "존재하지 않습니다" in response.json()["detail"]


def test_존재하지_않는_층_404(api_client):
    response = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/99F/route",
        params={"start_node_id": "start", "end_node_id": "end"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Floor not found"
