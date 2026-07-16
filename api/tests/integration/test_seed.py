"""시드한 지도 데이터를 ORM과 API가 사용할 수 있는지 검증한다.

SQL 문자열 저장 여부가 아니라, 시드 후 핵심 관계(층-노드-간선-매장 폴리곤)가
유효한지를 확인한다.
"""

from sqlalchemy import select

from app.models import Building, Edge, Floor, Node, Store
from tests.conftest import BUILDING_ID, FLOOR_NAME


# 시드된 건물·층·그래프가 ORM으로 조회되고 관계가 유효한지 검증한다.
def test_시드데이터가_ORM_지도그래프로_조회된다(db_session):
    building = db_session.get(Building, BUILDING_ID)
    assert building is not None

    floor = db_session.scalars(
        select(Floor).where(
            Floor.building_id == BUILDING_ID,
            Floor.name == FLOOR_NAME,
        )
    ).one()

    nodes = db_session.scalars(select(Node).where(Node.floor_id == floor.id)).all()
    edges = db_session.scalars(select(Edge).where(Edge.floor_id == floor.id)).all()
    node_ids = {node.id for node in nodes}

    # 빈 목록에서는 all(...)이 True가 되므로 존재 여부를 먼저 확인한다.
    assert nodes and all(node.floor_id == floor.id for node in nodes)
    assert edges and all(
        edge.floor_id == floor.id
        and edge.from_node_id in node_ids
        and edge.to_node_id in node_ids
        for edge in edges
    )
    assert any(len(edge.geometry) >= 2 for edge in edges)


# stores_1f.json의 매장 경계가 Store.polygon에 보존되는지 검증한다.
def test_시드데이터에_매장_폴리곤이_있다(db_session):
    floor = db_session.scalars(
        select(Floor).where(
            Floor.building_id == BUILDING_ID,
            Floor.name == FLOOR_NAME,
        )
    ).one()

    stores = db_session.scalars(select(Store).where(Store.floor_id == floor.id)).all()
    assert len(stores) == 59
    assert sum(store.polygon is not None for store in stores) == 57
