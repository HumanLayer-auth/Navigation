"""가공 JSON이 실제 SQLite 지도 그래프로 적재되는 전체 흐름 테스트."""

import json


# 가공 JSON이 실제 데이터베이스의 건물·노드·간선으로 적재되는지 검증한다.
def test_가공데이터에서_데이터베이스_지도그래프까지_적재된다(db_connection):
    building_count = db_connection.execute(
        "SELECT COUNT(*) FROM buildings"
    ).fetchone()[0]
    node = db_connection.execute(
        "SELECT source_x, source_y, x_m, y_m FROM nodes LIMIT 1"
    ).fetchone()
    edge = db_connection.execute(
        "SELECT geometry FROM edges WHERE geometry IS NOT NULL LIMIT 1"
    ).fetchone()
    vector_map = db_connection.execute(
        "SELECT coordinate_system FROM floor_vector_maps LIMIT 1"
    ).fetchone()
    vector_feature_count = db_connection.execute(
        "SELECT COUNT(*) FROM map_features"
    ).fetchone()[0]

    geometry = json.loads(edge["geometry"])
    assert building_count == 1
    assert node["source_x"] is not None
    assert node["x_m"] is not None
    assert len(geometry) >= 2
    assert json.loads(vector_map["coordinate_system"])["id"] == "svg_viewbox_px"
    assert vector_feature_count == 78
