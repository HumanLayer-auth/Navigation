"""서버 상태와 건물 HTTP API 통합 테스트."""

from tests.conftest import BUILDING_ID, FLOOR_NAME


def test_헬스체크(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_건물_목록_조회(api_client):
    response = api_client.get("/buildings")

    assert response.status_code == 200
    buildings = response.json()
    assert isinstance(buildings, list)
    assert buildings[0]["id"] == BUILDING_ID
    assert buildings[0]["floors"] == [FLOOR_NAME]


def test_건물_단건_조회(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == BUILDING_ID
    assert body["area_m2"] > 16000
    assert len(body["footprint_local_m"]) >= 4


def test_없는_건물_404(api_client):
    response = api_client.get("/buildings/nonexistent")

    assert response.status_code == 404
    assert response.json()["detail"] == "Building not found"
