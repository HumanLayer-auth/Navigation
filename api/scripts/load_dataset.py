"""
가공된 실 데이터를 SQLite(navigation.db) 에 적재하는 ETL

1회성 스크립트. 실행할 때마다 테이블을 DROP 후 재생성한다 (멱등).
--append를 주면 기존 테이블/데이터를 지우지 않고 이 건물만 추가로 적재한다
(같은 DB에 건물을 여러 개 담을 때 사용, 예: thehyundai-seoul + test-center).

실행방법
python scripts/load_dataset.py
python scripts/load_dataset.py --db data/navigation.db
python scripts/load_dataset.py --vector-dir app/data/vector_maps
python scripts/load_dataset.py --json app/data/navigation_test_center_1f.json --append

"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from math import cos, hypot, radians
from pathlib import Path

# app.domain을 import하려면 api/ 루트가 sys.path에 있어야 한다
# (이 스크립트를 scripts/ 디렉터리에서 직접 실행할 때는 기본적으로 없음).
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.domain.georeference import GeoTransform, PointPair, fit_wgs84_transform  # noqa: E402

# 스크립트를 어느 디렉토리에서 실행해도 같은 입력/출력 경로를 사용한다.
DEFAULT_JSON = API_ROOT / "app" / "data" / "navigation_1f.json"
DEFAULT_VECTOR_DIR = API_ROOT / "app" / "data" / "vector_maps"
DEFAULT_DB = API_ROOT / "data" / "navigation.db"

# 개발용 데이터셋을 항상 같은 상태로 만들기 위해 기본적으로 DROP → CREATE를
# 실행한다. 자식 테이블부터 DROP해야 외래 키 관계가 있어도 안전하게 다시
# 생성할 수 있다. --append(APPEND_DDL만 실행)를 주면 DROP을 건너뛰어 기존에
# 적재된 다른 건물 데이터를 보존한 채로 새 건물만 추가할 수 있다.
DROP_DDL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS pois;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS map_features;
DROP TABLE IF EXISTS floor_vector_maps;
DROP TABLE IF EXISTS floors;
DROP TABLE IF EXISTS buildings;
"""

APPEND_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS buildings (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    area_m2           REAL,
    perimeter_m       REAL,
    footprint_local_m TEXT,             -- [{"x":..,"y":..}, ...] JSON
    -- local_m -> WGS84 affine 변환(축별 스케일이 다를 수 있음, 6-DOF).
    -- geo_lng_scale은 경도(lng)에 곱해서 등방(isotropic) 공간으로 만드는
    -- 보정값(=cos(기준위도)) — 위도/경도 1도의 실제 거리가 다르기 때문에
    -- 필요하다. apply()에서: u,v = a*x+b*y+tx, c*x+d*y+ty; lng = u/geo_lng_scale; lat = v.
    -- 노드/매장에 wgs84 대응점이 3개 미만이면(실측 앵커 없는 건물) 전부 NULL.
    -- georeference_svg_floor_map.py가 대응하는 SVG 도면을 찾으면 이 값을
    -- SVG 경유로 개선된 변환으로 덮어쓴다.
    geo_a             REAL,
    geo_b             REAL,
    geo_c             REAL,
    geo_d             REAL,
    geo_tx            REAL,
    geo_ty            REAL,
    geo_lng_scale     REAL,
    -- 사람이 정리한 SVG 도면의 건물 외곽선을 위 변환으로 옮긴 결과.
    -- georeference_svg_floor_map.py가 채운다. 없으면 footprint_local_m을 쓴다.
    footprint_wgs84_svg TEXT
);

CREATE TABLE IF NOT EXISTS floors (
    id          TEXT PRIMARY KEY,
    building_id TEXT NOT NULL REFERENCES buildings(id),
    name        TEXT NOT NULL,          -- 예: 1F
    level       INTEGER NOT NULL,       -- 정렬용 층 순번
    UNIQUE (building_id, name)
);

CREATE TABLE IF NOT EXISTS floor_vector_maps (
    floor_id          TEXT PRIMARY KEY REFERENCES floors(id),
    coordinate_system TEXT NOT NULL,    -- SVG viewBox 좌표계 메타데이터 JSON
    source            TEXT NOT NULL     -- 원본 파일/형식 추적용 JSON
);

CREATE TABLE IF NOT EXISTS map_features (
    id            TEXT NOT NULL,
    floor_id      TEXT NOT NULL REFERENCES floor_vector_maps(floor_id),
    kind          TEXT NOT NULL,        -- footprint|store|amenity|wall|gate
    name          TEXT,
    category      TEXT,
    geometry_type TEXT NOT NULL,        -- Polygon|LineString
    coordinates   TEXT NOT NULL,        -- [{"x":..,"y":..}, ...] JSON
    centroid_x    REAL,
    centroid_y    REAL,
    PRIMARY KEY (floor_id, id)
);
CREATE INDEX IF NOT EXISTS idx_map_features_floor ON map_features(floor_id);
CREATE INDEX IF NOT EXISTS idx_map_features_kind  ON map_features(kind);

CREATE TABLE IF NOT EXISTS nodes (
    id       TEXT PRIMARY KEY,
    floor_id TEXT NOT NULL REFERENCES floors(id),
    type     TEXT NOT NULL,             -- corridor|junction|store_entrance|escalator|elevator|dead_end
    name     TEXT,
    x_m      REAL NOT NULL,             -- local_m 좌표 (top-left, y아래)
    y_m      REAL NOT NULL,
    lat      REAL,                      -- WGS84 (provisional, 외부 지도 연동용)
    lng      REAL,
    source_x REAL,                      -- 도면 원본 좌표 (재보정 대비 보존)
    source_y REAL
);

CREATE INDEX IF NOT EXISTS idx_nodes_floor ON nodes(floor_id);
CREATE INDEX IF NOT EXISTS idx_nodes_type  ON nodes(type);

CREATE TABLE IF NOT EXISTS edges (
    id            TEXT PRIMARY KEY,
    floor_id      TEXT NOT NULL REFERENCES floors(id),
    from_node_id  TEXT NOT NULL REFERENCES nodes(id),
    to_node_id    TEXT NOT NULL REFERENCES nodes(id),
    length_m      REAL NOT NULL,
    bidirectional INTEGER NOT NULL DEFAULT 1,
    geometry      TEXT                  -- local_m polyline JSON
);
CREATE INDEX IF NOT EXISTS idx_edges_floor ON edges(floor_id);
CREATE INDEX IF NOT EXISTS idx_edges_from  ON edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_edges_to    ON edges(to_node_id);

CREATE TABLE IF NOT EXISTS stores (
    id               TEXT PRIMARY KEY,
    floor_id         TEXT NOT NULL REFERENCES floors(id),
    name             TEXT NOT NULL,
    centroid_x_m     REAL NOT NULL,
    centroid_y_m     REAL NOT NULL,
    centroid_lat     REAL,              -- WGS84 (provisional, 원본에 있으면 보존)
    centroid_lng     REAL,
    entrance_x_m     REAL,
    entrance_y_m     REAL,
    entrance_node_id TEXT REFERENCES nodes(id),
    polygon          TEXT,              -- local_m Polygon JSON
    -- 사람이 정리한 SVG 도면에서 이름이 매칭된 매장의 폴리곤을 실좌표로
    -- 옮긴 결과. georeference_svg_floor_map.py가 채운다. 없으면(SVG에
    -- 대응 매장이 없음) polygon(local_m)을 건물 geo_transform으로 근사한다.
    svg_polygon_wgs84 TEXT
);
CREATE INDEX IF NOT EXISTS idx_stores_floor ON stores(floor_id);
CREATE INDEX IF NOT EXISTS idx_stores_name  ON stores(name);

CREATE TABLE IF NOT EXISTS pois (
    id             TEXT PRIMARY KEY,
    floor_id       TEXT NOT NULL REFERENCES floors(id),
    type           TEXT NOT NULL,
    name           TEXT,
    x_m            REAL NOT NULL,
    y_m            REAL NOT NULL,
    linked_node_id TEXT REFERENCES nodes(id)
);
CREATE INDEX IF NOT EXISTS idx_pois_floor ON pois(floor_id);
CREATE INDEX IF NOT EXISTS idx_pois_type  ON pois(type);
"""


def _node_row(node: dict, floor_id: str) -> tuple:
    """SVG 변환 JSON의 노드를 SQLite 컬럼 순서로 펼친다."""
    position = node["position"]
    local_m = position["local_m"]
    wgs84 = position.get("wgs84") or {}
    source = position.get("source") or {}
    return (
        node["id"],
        floor_id,
        node["type"],
        node.get("name"),
        local_m["x"],
        local_m["y"],
        wgs84.get("lat"),
        wgs84.get("lng"),
        source.get("x"),
        source.get("y"),
    )


def _edge_row(
    edge: dict,
    floor_id: str,
    node_points: dict[str, dict[str, float]],
) -> tuple:
    """간선 geometry와 거리가 없으면 양 끝 노드의 local_m 좌표로 보완한다."""
    geometry = edge.get("geometry_local_m") or [
        dict(node_points[edge["from"]]),
        dict(node_points[edge["to"]]),
    ]
    length_m = edge.get("length_m")
    if length_m is None:
        length_m = sum(
            hypot(
                current["x"] - previous["x"],
                current["y"] - previous["y"],
            )
            for previous, current in zip(geometry, geometry[1:])
        )

    return (
        edge["id"],
        floor_id,
        edge["from"],
        edge["to"],
        length_m,
        1 if edge.get("bidirectional", True) else 0,
        json.dumps(geometry, ensure_ascii=False),
    )


def _collect_geo_pairs(data: dict) -> list[PointPair]:
    """노드/매장 centroid 중 wgs84가 채워진 항목만 골라 대응점 목록을 만든다.

    PointPair(u=lng, v=lat)로 만든다 — GeoTransform.apply()가 반환하는
    (lat, lng) 순서와 헷갈리지 않도록 u/v는 항상 (lng, lat) 순서로 고정한다.
    """
    pairs: list[PointPair] = []

    for node in data["nodes"]:
        position = node["position"]
        wgs84 = position.get("wgs84")
        if not wgs84 or wgs84.get("lat") is None or wgs84.get("lng") is None:
            continue
        local_m = position["local_m"]
        pairs.append(
            PointPair(x=local_m["x"], y=local_m["y"], u=wgs84["lng"], v=wgs84["lat"])
        )

    for store in data["stores"]:
        centroid = store["centroid"]
        wgs84 = centroid.get("wgs84")
        if not wgs84 or wgs84.get("lat") is None or wgs84.get("lng") is None:
            continue
        local_m = centroid["local_m"]
        pairs.append(
            PointPair(x=local_m["x"], y=local_m["y"], u=wgs84["lng"], v=wgs84["lat"])
        )

    return pairs


# test-center처럼 실측 wgs84 앵커가 전혀 없는 합성 건물을 임의로 배치할 기준점
# (서울시청 — client의 GPS 실패 fallback 위치(outdoor_map_screen.dart의
# _fallbackLocation)와 맞춰서, 데모 앱에서 우연히라도 같은 동네에 보이게 한다).
# 실측 좌표가 아니라 "지도에 뭔가 보이게" 하기 위한 자리끼움일 뿐이다.
_SYNTHETIC_ANCHOR_LAT = 37.5665
_SYNTHETIC_ANCHOR_LNG = 126.9780
_METERS_PER_DEGREE_LAT = 111_320.0


def _synthetic_geo_pairs(anchor_lat: float, anchor_lng: float) -> list[PointPair]:
    """실측 앵커가 없는 건물을 위해 local_m 1m = 실좌표 1m로 매핑하는 가상
    대응점 3개를 만든다. anchor에 local_m (0,0)을 두고 평면 근사(equirectangular)로
    변환하므로 지구 곡률에 의한 오차는 무시할 만큼 작다(수백 m 이내 건물 규모).
    """
    lng_scale = cos(radians(anchor_lat))

    def to_wgs84(x_m: float, y_m: float) -> tuple[float, float]:
        lat = anchor_lat + y_m / _METERS_PER_DEGREE_LAT
        lng = anchor_lng + x_m / (_METERS_PER_DEGREE_LAT * lng_scale)
        return lat, lng

    pairs = []
    for x_m, y_m in ((0.0, 0.0), (100.0, 0.0), (0.0, 100.0)):
        lat, lng = to_wgs84(x_m, y_m)
        pairs.append(PointPair(x=x_m, y=y_m, u=lng, v=lat))
    return pairs


def _fit_building_geo_transform(data: dict) -> GeoTransform:
    """실측 wgs84 대응점이 3개 이상이면 건물의 local_m -> wgs84 변환을 피팅한다.

    이 변환은 기본값이다 — thehyundai-seoul처럼 대응하는 SVG 도면이 있는
    건물은 ``georeference_svg_floor_map.py``가 이 값을 SVG 경유로 개선된
    변환으로 덮어쓴다(1차 구현 이후 발견된 문제 참고: 매장 centroid만 실측
    보정하고 외곽선/POI는 이 변환 그대로 쓰면 서로 어긋나 보인다).

    test-center처럼 실좌표 앵커가 없는 합성 건물은 ``_synthetic_geo_pairs``로
    임의의 실좌표에 1m=1m로 배치한다 — None을 반환해서 지도에 아무것도 못
    그리게 두는 대신, 위치는 가짜지만 형태/크기는 정확한 지도를 보여준다.
    """
    pairs = _collect_geo_pairs(data)
    if len(pairs) < 3:
        pairs = _synthetic_geo_pairs(_SYNTHETIC_ANCHOR_LAT, _SYNTHETIC_ANCHOR_LNG)
    return fit_wgs84_transform(pairs)


def _find_vector_dataset(
    vector_path: Path,
    *,
    building_id: str,
    floor_id: str,
) -> dict:
    """파일 또는 디렉터리에서 현재 건물/층에 해당하는 벡터 JSON 하나를 찾는다."""
    vector_path = Path(vector_path)
    if vector_path.is_file():
        candidates = [vector_path]
    elif vector_path.is_dir():
        candidates = sorted(vector_path.rglob("*.json"))
    else:
        raise FileNotFoundError(f"벡터 데이터 경로가 없습니다: {vector_path}")

    matches: list[tuple[Path, dict]] = []
    for candidate in candidates:
        with open(candidate, encoding="utf-8") as vector_file:
            vector_data = json.load(vector_file)
        if (
            vector_data.get("building_id") == building_id
            and vector_data.get("floor_id") == floor_id
        ):
            matches.append((candidate, vector_data))

    if not matches:
        raise FileNotFoundError(
            f"{building_id}/{floor_id} 벡터 JSON을 {vector_path}에서 찾지 못했습니다."
        )
    if len(matches) > 1:
        paths = ", ".join(str(path) for path, _ in matches)
        raise ValueError(f"동일한 건물/층 벡터 JSON이 여러 개입니다: {paths}")
    return matches[0][1]

def load_navigation_db(
    json_path: Path = DEFAULT_JSON,
    db_path: Path = DEFAULT_DB,
    vector_path: Path | None = DEFAULT_VECTOR_DIR,
    *,
    append: bool = False,
) -> dict[str, int]:
    """navigation JSON을 읽어 SQLite로 적재하고 테이블별 건수를 반환한다."""
    # 원본 JSON 전체를 Python dict/list 구조로 읽는다.
    with open(json_path, encoding = "utf-8") as f:
        data = json.load(f)

    # 현재 데이터셋은 건물 하나와 그 안의 단일 층을 기준으로 구성돼 있다.
    building = data["building"]
    floor = building["floor"]
    building_id = building["id"]
    floor_id = floor["id"]
    node_points = {
        node["id"]: node["position"]["local_m"]
        for node in data["nodes"]
    }
    # 이미 계산된 local_m<->wgs84 대응점(노드/매장 centroid)으로 건물 하나에
    # 적용할 similarity 변환을 미리 피팅해둔다. 실좌표 대응점이 없으면 None.
    geo_transform = _fit_building_geo_transform(data)

    # 출력 폴더가 아직 없어도 DB 파일을 생성할 수 있게 준비한다.
    db_path = Path(db_path)
    db_path.parent.mkdir(parents = True, exist_ok = True) # data/ 폴더 없으면 생성

    conn = sqlite3.connect(db_path)
    try:
        # append가 아니면 기존 테이블을 전부 지우고 새로 만든다(단일 건물 기준 멱등).
        # append면 DROP을 건너뛰어 이미 적재된 다른 건물 데이터를 보존한다.
        if not append:
            conn.executescript(DROP_DDL)
        conn.executescript(APPEND_DDL)

        # --- 건물/층: 각각 한 건씩 INSERT ---
        conn.execute(
            "INSERT INTO buildings"
            " (id, name, area_m2, perimeter_m, footprint_local_m,"
            " geo_a, geo_b, geo_c, geo_d, geo_tx, geo_ty, geo_lng_scale)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                building_id,
                building["name"],
                building["area_m2"],
                building["perimeter_m"],
                # 폴리곤 리스트는 JSON 문자열로 직렬화해서 TEXT 칼럼에 저장합니다.
                json.dumps(building["footprint_local_m"], ensure_ascii = False),
                geo_transform.a,
                geo_transform.b,
                geo_transform.c,
                geo_transform.d,
                geo_transform.tx,
                geo_transform.ty,
                geo_transform.lng_scale,
            ),
        )
        conn.execute(
            "INSERT INTO floors (id, building_id, name, level) VALUES (?, ?, ?, ?)",
            (floor_id, building_id, floor["name"], floor["level"]),
        )

        # --- 그래프/지도 데이터: 목록을 executemany로 일괄 INSERT ---
        # 대량 Insert는 한 건씩 execute하는 것보다 DB 호출 횟수가 적다.
        conn.executemany(
            "INSERT INTO nodes (id, floor_id, type, name, x_m, y_m, lat, lng, source_x, source_y)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [_node_row(node, floor_id) for node in data["nodes"]],
        )
        conn.executemany(
            # Edge는 Node ID를 참조하고 geometry는 JSON 문자열로 저장한다.
            "INSERT INTO edges (id, floor_id, from_node_id, to_node_id, length_m, bidirectional, geometry)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                _edge_row(edge, floor_id, node_points)
                for edge in data["edges"]
            ],
        )
        conn.executemany(
            # Store 폴리곤과 선택적 입구 좌표를 평면 컬럼으로 적재한다.
            "INSERT INTO stores (id, floor_id, name, centroid_x_m, centroid_y_m,"
            " centroid_lat, centroid_lng, entrance_x_m, entrance_y_m, entrance_node_id, polygon)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    s["id"],
                    floor_id,
                    s["name"],
                    s["centroid"]["local_m"]["x"],
                    s["centroid"]["local_m"]["y"],
                    # 원본에 이미 계산된 실측 wgs84가 있으면 버리지 않고 보존한다
                    # (공식으로 다시 계산하면 건물 전체 평균 오차를 그대로 물려받음).
                    (s["centroid"].get("wgs84") or {}).get("lat"),
                    (s["centroid"].get("wgs84") or {}).get("lng"),
                    # entrance가 없는 매장 대비 — None이면 NULL로 들어간다
                    s["entrance_local_m"]["x"] if s["entrance_local_m"] else None,
                    s["entrance_local_m"]["y"] if s["entrance_local_m"] else None,
                    s["entrance_node_id"],
                    json.dumps(s["polygon_local_m"]) if s["polygon_local_m"] else None,
                )
                for s in data["stores"]
            ],
        )
        conn.executemany(
            # POI 위치는 Node와 별개로 표시하되 linked_node_id로 길찾기에 연결할 수 있다.
            "INSERT INTO pois (id, floor_id, type, name, x_m, y_m, linked_node_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    p["id"],
                    floor_id,
                    p["type"],
                    p.get("name"),
                    p["position"]["local_m"]["x"],
                    p["position"]["local_m"]["y"],
                    p.get("linked_node_id"),
                )
                for p in data["pois"]
            ],
        )

        if vector_path is not None:
            vector_data = _find_vector_dataset(
                vector_path,
                building_id=building_id,
                floor_id=floor_id,
            )

            conn.execute(
                "INSERT INTO floor_vector_maps (floor_id, coordinate_system, source)"
                " VALUES (?, ?, ?)",
                (
                    floor_id,
                    json.dumps(vector_data["coordinate_system"], ensure_ascii=False),
                    json.dumps(vector_data["source"], ensure_ascii=False),
                ),
            )
            conn.executemany(
                "INSERT INTO map_features (id, floor_id, kind, name, category,"
                " geometry_type, coordinates, centroid_x, centroid_y)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        feature["id"],
                        floor_id,
                        feature["kind"],
                        feature.get("name"),
                        feature.get("category"),
                        feature["geometry"]["type"],
                        json.dumps(
                            feature["geometry"]["coordinates"],
                            ensure_ascii=False,
                        ),
                        (feature.get("centroid") or {}).get("x"),
                        (feature.get("centroid") or {}).get("y"),
                    )
                    for feature in vector_data["features"]
                ],
            )
        # 모든 테이블 INSERT가 성공한 경우에만 한 번에 영구 반영한다.
        conn.commit() # 자동으로 transaction 마무리

        # 적재 결과 요약은 CLI 출력과 테스트의 데이터 건수 검증에 함께 사용한다.
        counts = {
            table: conn.execute(f"select count(*) from {table}").fetchone()[0]
            for table in (
                "buildings",
                "floors",
                "floor_vector_maps",
                "map_features",
                "nodes",
                "edges",
                "stores",
                "pois",
            )
        }
        return counts
    
    finally:
        # 중간 INSERT에서 예외가 발생해도 파일 핸들을 반드시 반환한다.
        conn.close() # 예외가 나도 커넥션은 반드시 닫는다.

if __name__ == "__main__":
    # 모듈 import 때는 실행하지 않고 직접 호출했을 때만 CLI 인자를 처리한다.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--vector-dir",
        type=Path,
        default=DEFAULT_VECTOR_DIR,
        help="건물/층별 벡터 JSON 디렉터리 또는 단일 JSON 파일",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--append",
        action="store_true",
        help="기존 테이블을 DROP하지 않고 이 건물만 추가로 적재한다",
    )
    args = parser.parse_args()

    result = load_navigation_db(
        args.json, args.db, args.vector_dir, append=args.append
    )
    print(f"적재 완료 : {args.db}")
    for table, count in result.items():
        print(f" {table}: {count}")
