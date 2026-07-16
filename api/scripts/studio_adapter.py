"""FloorGraph Studio 1F 익스포트를 ORM 적재용 표준 dict로 변환한다.

설계 근거: docs/floorgraph-studio-integration.md (§3 목표 구조, §6 결정 D1~D5)

변환 규칙:
  - floor(상단) → building 블록 합성. 건물명은 Studio 건물 ID의 정적 메타데이터로 보완하며,
    footprint/area는 좌표계 재투영 전이므로 None(D2).
  - nodes  → 그대로 사용(position.local_m/wgs84/source 구조가 이미 호환).
  - edges  → 그대로 사용(seed_navigation.edge_geometry_and_length가 geometry.local_m 처리).
  - stores → 폴리곤이 포함된 stores_1f.json을 seed 스키마로 reshape(D1/D4).
  - pois   → elevator/escalator 노드에서 자동 생성(지도 마커용).

실행 (api/ 디렉토리에서):
  python -m scripts.studio_adapter
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.database import SessionLocal
from scripts import seed_navigation

API_ROOT = Path(__file__).resolve().parents[1]
STUDIO_DIR = API_ROOT / "app" / "data" / "studio" / "thehyundai-seoul"
BUILDING_NAMES = {"thehyundai-seoul": "더현대 서울"}
FLOOR_CODE = "1f"

# 지도에 마커로 노출할 편의시설 노드 타입 → POI 로 승격(D-POI: 노드에서 자동 생성)
POI_NODE_TYPES = {"elevator", "escalator"}


def _building_name(building_id: str) -> str:
    """Studio 데이터에 없는 표시용 건물명을 ID 기반 메타데이터로 보완한다."""
    return BUILDING_NAMES.get(building_id, building_id)


def _scoped(floor_id: str, raw_id: str | None) -> str | None:
    """D6: 노드/엣지 ID를 층 스코프로 네임스페이싱한다(층 간 ID 재사용 충돌 방지)."""
    if raw_id is None:
        return None
    return f"{floor_id}:{raw_id}"


def _scope_nodes(floor_id: str, nodes: list[dict]) -> list[dict]:
    return [{**node, "id": _scoped(floor_id, node["id"])} for node in nodes]


def _scope_edges(floor_id: str, edges: list[dict]) -> list[dict]:
    return [
        {
            **edge,
            "id": _scoped(floor_id, edge["id"]),
            "from": _scoped(floor_id, edge["from"]),
            "to": _scoped(floor_id, edge["to"]),
        }
        for edge in edges
    ]


def _reshape_stores(floor_id: str) -> list[dict]:
    """폴리곤을 포함한 stores_1f.json을 seed용 store dict로 변환한다."""
    stores_path = STUDIO_DIR / f"stores_{FLOOR_CODE}.json"
    if not stores_path.exists():
        return []
    payload = json.loads(stores_path.read_text(encoding="utf-8"))
    reshaped: list[dict] = []
    for store in payload.get("stores", []):
        entrance = store.get("entrance_local_m")
        centroid = store.get("centroid_local_m") or entrance
        reshaped.append(
            {
                "id": store["id"],  # store id는 층별로 이미 유일(네임스페이싱 불필요)
                # 매칭 안 된 구조물 footprint는 name이 null → store id로 폴백(stores.name NOT NULL)
                "name": store.get("name") or store["id"],
                # seed_navigation는 store["centroid"]["local_m"] 구조를 기대한다.
                "centroid": {"local_m": centroid},
                "entrance_local_m": entrance,
                # entrance_node_id는 Node FK → 네임스페이싱한 노드 ID와 일치시켜야 한다.
                "entrance_node_id": _scoped(floor_id, store.get("entrance_node_id")),
                "polygon_local_m": store.get("polygon_local_m"),
            }
        )
    return reshaped


def _generate_pois(floor_id: str, nodes: list[dict]) -> list[dict]:
    """elevator/escalator 노드를 POI(지도 마커)로 승격한다(ID도 층 스코프)."""
    pois: list[dict] = []
    for node in nodes:
        if node.get("type") not in POI_NODE_TYPES:
            continue
        pois.append(
            {
                "id": _scoped(floor_id, f"poi_{node['id']}"),
                "type": node["type"],
                "name": node.get("name"),
                "position": {"local_m": node["position"]["local_m"]},
                "linked_node_id": _scoped(floor_id, node["id"]),
            }
        )
    return pois


def build_seed_dict() -> dict:
    """Studio 1F JSON과 stores_1f.json을 표준 seed dict로 조립한다."""
    studio = json.loads((STUDIO_DIR / f"{FLOOR_CODE}.json").read_text(encoding="utf-8"))
    building_id = studio["building_id"]
    floor = studio["floor"]
    floor_id = floor["id"]

    return {
        "building": {
            "id": building_id,
            "name": _building_name(building_id),
            "area_m2": None,  # D2: 좌표계 재투영 전까지 보류
            "perimeter_m": None,
            "footprint_local_m": None,
            "floor": {
                "id": floor_id,
                "name": floor["name"],
                "level": floor["level"],
            },
        },
        "nodes": _scope_nodes(floor_id, studio["nodes"]),  # D6
        "edges": _scope_edges(floor_id, studio["edges"]),  # D6
        "stores": _reshape_stores(floor_id),
        "pois": _generate_pois(floor_id, studio["nodes"]),
    }


def seed_studio(*, session=None) -> None:
    """Studio 1F를 하나의 트랜잭션으로 적재한다."""
    own_session = session or SessionLocal()
    try:
        seed_navigation.add_dataset(own_session, build_seed_dict())
        if session is None:
            own_session.commit()
    except Exception:
        if session is None:
            own_session.rollback()
        raise
    finally:
        if session is None:
            own_session.close()


def main() -> None:
    seed_studio()
    data = build_seed_dict()
    print(
        f"[1F] nodes={len(data['nodes'])} edges={len(data['edges'])} "
        f"stores={len(data['stores'])} pois={len(data['pois'])}"
    )
    print("Studio 데이터 적재 완료")


if __name__ == "__main__":
    main()
