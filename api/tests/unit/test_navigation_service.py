"""소형 인메모리 시드 그래프로 검증하는 NavigationService 단위 테스트."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.models import Building, Edge, Floor, Node
from app.models.base import Base
from app.services.navigation_service import NavigationService

BUILDING_ID = "test-building"
FLOOR_ID = "test-building-1f"
FLOOR_NAME = "1F"


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Building(id=BUILDING_ID, name="테스트 건물"))
    session.add(
        Floor(id=FLOOR_ID, building_id=BUILDING_ID, name=FLOOR_NAME, level=1)
    )
    session.add_all(
        [
            Node(id="A", floor_id=FLOOR_ID, type="corridor", x_m=0.0, y_m=0.0),
            Node(id="B", floor_id=FLOOR_ID, type="junction", x_m=1.0, y_m=0.0),
            Node(id="C", floor_id=FLOOR_ID, type="corridor", x_m=2.0, y_m=0.0),
            Node(id="D", floor_id=FLOOR_ID, type="dead_end", x_m=9.0, y_m=9.0),
        ]
    )
    session.add_all(
        [
            Edge(
                id="AB",
                floor_id=FLOOR_ID,
                from_node_id="A",
                to_node_id="B",
                length_m=1.0,
                bidirectional=True,
                geometry=[
                    {"x": 0.0, "y": 0.0},
                    {"x": 0.5, "y": 0.2},
                    {"x": 1.0, "y": 0.0},
                ],
            ),
            # geometry가 없는 간선은 노드 좌표로 보완돼야 한다.
            Edge(
                id="BC",
                floor_id=FLOOR_ID,
                from_node_id="B",
                to_node_id="C",
                length_m=1.0,
                bidirectional=True,
                geometry=None,
            ),
        ]
    )
    session.commit()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def service(session) -> NavigationService:
    return NavigationService(session)


# 정방향 최단 경로의 간선 좌표가 저장 순서대로 반환되는지 검증한다.
def test_최단경로의_경로선을_정방향으로_반환한다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "A", "B")

    assert result["path_points"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 0.5, "y": 0.2},
        {"x": 1.0, "y": 0.0},
    ]


# 양방향 간선을 역방향으로 이동할 때 좌표 순서가 반전되는지 검증한다.
def test_역방향_이동은_경로선_순서를_뒤집는다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "B", "A")

    assert result["path_points"] == [
        {"x": 1.0, "y": 0.0},
        {"x": 0.5, "y": 0.2},
        {"x": 0.0, "y": 0.0},
    ]


# 간선 경로선이 없을 때 양 끝 노드 좌표로 보완하는지 검증한다.
def test_경로선이_없으면_노드_좌표를_사용한다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "B", "C")

    assert result["path_points"] == [
        {"x": 1.0, "y": 0.0},
        {"x": 2.0, "y": 0.0},
    ]


# 여러 간선 연결 시 공통 접점 좌표가 중복되지 않는지 검증한다.
def test_여러_간선의_중복_접점은_한번만_포함한다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "A", "C")

    assert result["path_points"] == [
        {"x": 0.0, "y": 0.0},
        {"x": 0.5, "y": 0.2},
        {"x": 1.0, "y": 0.0},
        {"x": 2.0, "y": 0.0},
    ]


# 출발지와 목적지가 같을 때 단일 좌표와 거리 0을 반환하는지 검증한다.
def test_출발지와_목적지가_같으면_좌표_하나를_반환한다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "A", "A")

    assert result["path_points"] == [{"x": 0.0, "y": 0.0}]
    assert result["total_distance_m"] == 0.0


# 목적지까지 연결된 간선이 없을 때 경로 발견 값이 거짓인지 검증한다.
def test_연결되지_않은_목적지는_경로발견값이_거짓이다(service):
    result = service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "A", "D")

    assert result["path_found"] is False


# 존재하지 않는 노드 식별자가 값 오류로 처리되는지 검증한다.
def test_존재하지_않는_노드는_값오류다(service):
    with pytest.raises(ValueError, match="존재하지 않습니다"):
        service.get_shortest_path(BUILDING_ID, FLOOR_NAME, "missing", "A")


# 존재하지 않는 층 요청이 결과 없음으로 처리되는지 검증한다.
def test_없는_층은_결과없음을_반환한다(service):
    assert service.get_shortest_path(BUILDING_ID, "99F", "A", "B") is None
