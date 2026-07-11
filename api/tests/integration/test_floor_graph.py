"""층 지도와 길찾기 그래프 HTTP API 통합 테스트."""

from tests.conftest import BUILDING_ID, FLOOR_NAME


def test_층_지도_조회(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}")

    assert response.status_code == 200
    body = response.json()
    assert body["floor"]["name"] == FLOOR_NAME
    assert len(body["stores"]) == 61
    assert len(body["pois"]) == 47


def test_없는_층_404(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/floors/99F")

    assert response.status_code == 404
    assert response.json()["detail"] == "Floor not found"


def test_층_그래프_조회(api_client):
    response = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}/graph"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 234
    assert len(body["edges"]) == 282
