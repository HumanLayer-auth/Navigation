"""매장 검색 HTTP API 통합 테스트."""

from tests.conftest import BUILDING_ID


def test_매장_검색(api_client):
    response = api_client.get(
        f"/buildings/{BUILDING_ID}/stores",
        params={"q": "베네타"},
    )

    assert response.status_code == 200
    stores = response.json()
    assert len(stores) >= 1
    assert any("베네타" in store["name"] for store in stores)


def test_매장_검색_전체(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/stores")

    assert response.status_code == 200
    assert len(response.json()) == 61
