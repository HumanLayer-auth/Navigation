"""층 지도와 길찾기 그래프 HTTP API 통합 테스트."""

from tests.conftest import BUILDING_ID, FLOOR_NAME


# 층 지도 API가 층 정보와 매장·관심 지점을 반환하는지 검증한다.
def test_층_지도를_조회한다(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}")

    assert response.status_code == 200
    body = response.json()
    assert body["floor"]["name"] == FLOOR_NAME
    assert len(body["stores"]) == 59
    assert len(body["pois"]) == 13


# 층 지도 응답에 Studio 그래프와 매장 폴리곤이 포함되는지 검증한다.
def test_층_지도에_Studio_그래프와_매장_폴리곤을_응답한다(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}")

    assert response.status_code == 200
    body = response.json()
    assert body["navigation_coordinate_system"] == "local_m"
    assert len(body["navigation_graph"]["nodes"]) == 167
    assert len(body["navigation_graph"]["edges"]) == 294
    assert sum(store["polygon_local_m"] is not None for store in body["stores"]) == 57
    assert sum(store["polygon_wgs84"] is not None for store in body["stores"]) == 57


# 존재하지 않는 층 요청이 찾을 수 없음 응답으로 변환되는지 검증한다.
def test_없는_층은_찾을수없음_응답을_반환한다(api_client):
    response = api_client.get(f"/buildings/{BUILDING_ID}/floors/99F")

    assert response.status_code == 404
    assert response.json()["detail"] == "Floor not found"


# 층 그래프 API가 저장된 노드와 간선을 반환하는지 검증한다.
def test_층_그래프를_조회한다(api_client):
    response = api_client.get(
        f"/buildings/{BUILDING_ID}/floors/{FLOOR_NAME}/graph"
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 167
    assert len(body["edges"]) == 294
