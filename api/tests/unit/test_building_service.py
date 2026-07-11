"""BuildingService 단위 테스트."""

import pytest

from app.service.buildingService import BuildingService
from tests.conftest import BUILDING_ID, FLOOR_NAME


@pytest.fixture
def service(building_repository) -> BuildingService:
    return BuildingService(building_repository)


def test_건물_목록_조회(service):
    buildings = service.get_all_buildings()

    assert len(buildings) == 1
    assert buildings[0]["id"] == BUILDING_ID
    assert buildings[0]["floors"] == [FLOOR_NAME]
    assert "footprint_local_m" not in buildings[0]


def test_건물_상세_조회(service):
    building = service.get_building(BUILDING_ID)

    assert building["id"] == BUILDING_ID
    assert building["area_m2"] == pytest.approx(16182.4, abs=1.0)
    assert len(building["footprint_local_m"]) >= 4


def test_없는_건물은_None(service):
    assert service.get_building("nonexistent") is None


def test_층_그래프_조회(service):
    graph = service.get_floor_graph(BUILDING_ID, FLOOR_NAME)

    assert len(graph["nodes"]) == 234
    assert len(graph["edges"]) == 282

    node_ids = {node["id"] for node in graph["nodes"]}
    for edge in graph["edges"]:
        assert edge["from"] in node_ids
        assert edge["to"] in node_ids
        assert edge["length_m"] >= 0


def test_층_지도_조회(service):
    floor_map = service.get_floor_map(BUILDING_ID, FLOOR_NAME)

    assert floor_map["floor"]["name"] == FLOOR_NAME
    assert len(floor_map["footprint_local_m"]) >= 4
    assert len(floor_map["stores"]) == 61
    assert len(floor_map["pois"]) == 47


def test_없는_층은_None(service):
    assert service.get_floor_graph(BUILDING_ID, "99F") is None
    assert service.get_floor_map(BUILDING_ID, "99F") is None


def test_매장_검색(service):
    results = service.search_stores(BUILDING_ID, "베네타")

    assert len(results) >= 1
    assert any("베네타" in store["name"] for store in results)
    assert all(store["entrance_node_id"] for store in results)


def test_매장_검색_빈_질의는_전체(service):
    assert len(service.search_stores(BUILDING_ID, "")) == 61


def test_없는_건물_매장_검색은_None(service):
    assert service.search_stores("nonexistent", "베네타") is None


def test_최단_경로_조회(service):
    graph = service.get_floor_graph(BUILDING_ID, FLOOR_NAME)
    edge = graph["edges"][0]

    path = service.get_shortest_path(
        BUILDING_ID,
        FLOOR_NAME,
        edge["from"],
        edge["to"],
    )

    assert path["path_found"] is True
    assert path["node_ids"][0] == edge["from"]
    assert path["node_ids"][-1] == edge["to"]
    assert len(path["edge_ids"]) >= 1
    assert path["total_distance_m"] >= 0
