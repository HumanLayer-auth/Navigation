"""B2 원본 벡터 맵을 Studio graph/stores 초안으로 변환한다.

원본은 매장 폴리곤과 화면 픽셀만 제공한다. 따라서 이 도구는 흰 통로를 규칙 격자로
근사하고, 0.1m/px 임시 scale을 쓴다. 이는 production 지오리퍼런스가 아니다.
"""

from __future__ import annotations

import json
from heapq import heappop, heappush
from math import hypot
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "backend/resources/studio/thehyundai-seoul/studio_b2f"
INPUT = OUT / "source_b2.json"
FLOOR_ID = "FL-thehyundai-seoul-b2-draft"
SCALE = 0.1  # provisional: physical measurement is not available in the source artifact
# 흰 공간을 모두 점으로 채우지 않는다. Studio에서 사람이 다듬기 좋은 복도 골격만
# 남기기 위한 간격이며, 매장/시설 입구는 별도 노드로 연결한다.
STEP = 80

# 원본 이미지에서 판독한 상호와 connected-component 영역의 대응. 나머지 영역은
# 이름을 추정하지 않고 review 대상 ID로 남긴다.
NAMES = {
    16: "뉴발란스", 17: "HDEX", 18: "노스페이스 화이트라벨", 28: "CK 진",
    33: "POP-UP WEST", 44: "아디다스 스튜디오", 46: "코닥 x 디오디", 47: "크록스",
    48: "나이스웨더", 11: "MLB", 12: "AAPE", 13: "캉골클럽", 14: "더샛",
    1: "THISISNEVERTHAT", 2: "쿠어", 3: "망고매니플리즈", 5: "시에", 6: "플리츠룸",
    7: "데우스 엑스 마키나", 8: "인사일런스", 9: "구호플러스", 10: "세터",
    19: "산산기어", 20: "포인트 오브 뷰", 32: "프로그램", 36: "PEER", 41: "마뗑킴",
    42: "더채널", 53: "하이츠 익스체인지", 54: "BeCLEAN(비클린)", 49: "스미스앤레더",
    50: "베호트", 51: "필아이다이", 52: "시티브리즈", 57: "오픈 YY", 59: "팝마트",
    58: "나이키 라이즈", 62: "ARKET", 64: "ARKET CAFE", 60: "POP-UP ICONIC B2",
    63: "마리떼프랑소와저버/LMC", 56: "아프리카안경", 45: "스탠드오일", 31: "이기스", 67: "YPHAUS",
}

FACILITIES = {
    68: ("poi", "TAX REFUND KIOSK", "tax_refund"),
    69: ("poi", "휴대전화 충전기 대여(유료)", "phone_charger_rental"),
    70: ("restroom", "화장실", "restroom"), 71: ("restroom", "화장실", "restroom"),
    72: ("escalator", "서쪽 에스컬레이터", "escalator"), 73: ("escalator", "서쪽 에스컬레이터", "escalator"),
    74: ("escalator", "중앙 에스컬레이터", "escalator"), 75: ("escalator", "중앙 에스컬레이터", "escalator"),
    76: ("escalator", "중앙 에스컬레이터", "escalator"), 77: ("escalator", "중앙 에스컬레이터", "escalator"),
    78: ("escalator", "동쪽 에스컬레이터", "escalator"), 79: ("escalator", "동쪽 에스컬레이터", "escalator"),
    80: ("escalator", "서쪽 에스컬레이터", "escalator"), 81: ("escalator", "서쪽 에스컬레이터", "escalator"),
    82: ("escalator", "중앙 에스컬레이터", "escalator"), 83: ("escalator", "중앙 에스컬레이터", "escalator"),
    84: ("escalator", "중앙 에스컬레이터", "escalator"), 85: ("escalator", "중앙 에스컬레이터", "escalator"),
    86: ("escalator", "동쪽 에스컬레이터", "escalator"), 87: ("escalator", "동쪽 에스컬레이터", "escalator"),
    88: ("restroom", "화장실", "restroom"), 89: ("restroom", "화장실", "restroom"),
    90: ("restroom", "화장실", "restroom"), 91: ("restroom", "화장실", "restroom"),
    92: ("poi", "정수기", "water_dispenser"), 93: ("restroom", "화장실", "restroom"),
    94: ("poi", "정수기", "water_dispenser"), 95: ("elevator", "지하철 5/9호선 여의도역", "subway_elevator"),
}

# PNG의 흰 아이콘이 초록색 fill을 끊어 놓아서 원본 추출에는 위/아래 조각이 각각
# 존재한다. 실제 평면도에서는 하나의 세로 에스컬레이터이므로 한 polygon으로 합친다.
ESCALATOR_GROUPS = {
    72: ((72, 80), "서쪽 에스컬레이터 1"),
    73: ((73, 81), "서쪽 에스컬레이터 2"),
    74: ((74, 82), "중앙 에스컬레이터 1"),
    75: ((75, 83), "중앙 에스컬레이터 2"),
    76: ((76, 84), "중앙 에스컬레이터 3"),
    77: ((77, 85), "중앙 에스컬레이터 4"),
    78: ((78, 86), "동쪽 에스컬레이터 1"),
    79: ((79, 87), "동쪽 에스컬레이터 2"),
}


def point(raw: dict) -> dict[str, float]:
    return {"x": round(raw["x"] * SCALE, 6), "y": round(raw["y"] * SCALE, 6)}


def raw_point(local: dict) -> dict[str, float]:
    return {"x": round(local["x"] / SCALE, 6), "y": round(local["y"] / SCALE, 6)}


def polygon(feature: dict) -> list[dict]:
    return [point(p) for p in feature["geometry"]["coordinates"]]


def inside(x: float, y: float, vertices: list[dict]) -> bool:
    hit = False
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        if (a["y"] > y) != (b["y"] > y):
            edge_x = (b["x"] - a["x"]) * (y - a["y"]) / (b["y"] - a["y"]) + a["x"]
            if x < edge_x:
                hit = not hit
    return hit


def segment_clear(a: dict, b: dict, blocked: list[list[dict]]) -> bool:
    distance = hypot(b["x"] - a["x"], b["y"] - a["y"])
    for index in range(1, max(2, int(distance / 1.5))):
        t = index / max(2, int(distance / 1.5))
        x, y = a["x"] + (b["x"] - a["x"]) * t, a["y"] + (b["y"] - a["y"]) * t
        if any(inside(x, y, shape) for shape in blocked):
            return False
    return True


def walkable_grid_path(start: dict, end: dict, blocked: list[list[dict]], width: float, height: float, cell: float = 4.0) -> list[dict] | None:
    """시설 polygon을 피하는 작은 보조 격자 A* 경로를 찾는다."""
    max_x, max_y = int(width // cell), int(height // cell)

    def to_cell(point: dict) -> tuple[int, int]:
        return (max(0, min(max_x, round(point["x"] / cell))), max(0, min(max_y, round(point["y"] / cell))))

    def to_point(cell_xy: tuple[int, int]) -> dict:
        return {"x": round(cell_xy[0] * cell, 6), "y": round(cell_xy[1] * cell, 6)}

    def allowed(cell_xy: tuple[int, int]) -> bool:
        x, y = cell_xy
        return 0 <= x <= max_x and 0 <= y <= max_y and not any(inside(to_point(cell_xy)["x"], to_point(cell_xy)["y"], shape) for shape in blocked)

    source, target = to_cell(start), to_cell(end)
    if not allowed(source) or not allowed(target):
        return None
    queue = [(0, 0, source)]
    previous: dict[tuple[int, int], tuple[int, int] | None] = {source: None}
    distance = {source: 0}
    while queue:
        _score, current_cost, current = heappop(queue)
        if current == target:
            path = []
            while current is not None:
                path.append(to_point(current))
                current = previous[current]
            return list(reversed(path))
        if current_cost != distance[current]:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = (current[0] + dx, current[1] + dy)
            if not allowed(candidate):
                continue
            candidate_cost = current_cost + 1
            if candidate_cost >= distance.get(candidate, float("inf")):
                continue
            distance[candidate] = candidate_cost
            previous[candidate] = current
            heuristic = abs(candidate[0] - target[0]) + abs(candidate[1] - target[1])
            heappush(queue, (candidate_cost + heuristic, candidate_cost, candidate))
    return None


def simplify_walkable_path(points: list[dict], blocked: list[list[dict]]) -> list[dict]:
    result, index = [points[0]], 0
    while index < len(points) - 1:
        next_index = index + 1
        for candidate in range(len(points) - 1, index, -1):
            if segment_clear(result[-1], points[candidate], blocked):
                next_index = candidate
                break
        result.append(points[next_index])
        index = next_index
    return result


def nearest(target: dict, nodes: list[dict]) -> dict:
    return min(nodes, key=lambda node: hypot(node["position"]["local_m"]["x"] - target["x"], node["position"]["local_m"]["y"] - target["y"]))


def closest_boundary(target: dict, shape: list[dict]) -> dict:
    best, best_distance = shape[0], float("inf")
    for start, end in zip(shape, shape[1:] + shape[:1]):
        dx, dy = end["x"] - start["x"], end["y"] - start["y"]
        length2 = dx * dx + dy * dy
        t = 0 if length2 == 0 else max(0, min(1, ((target["x"] - start["x"]) * dx + (target["y"] - start["y"]) * dy) / length2))
        candidate = {"x": round(start["x"] + t * dx, 6), "y": round(start["y"] + t * dy, 6)}
        distance = hypot(candidate["x"] - target["x"], candidate["y"] - target["y"])
        if distance < best_distance:
            best, best_distance = candidate, distance
    return best


def connect_corridor_components(corridor_nodes: list[dict], edges: list[dict], blocked: list[list[dict]], width: float, height: float) -> int:
    """분리된 격자 섬을 흰 통로를 통과하는 최단 connector로 연결한다."""
    bridges = 0
    while True:
        ids = {node["id"] for node in corridor_nodes}
        adjacency = {node_id: set() for node_id in ids}
        for edge in edges:
            if edge["from"] in ids and edge["to"] in ids:
                adjacency[edge["from"]].add(edge["to"])
                adjacency[edge["to"]].add(edge["from"])
        components, component_index = [], {}
        for node_id in ids:
            if node_id in component_index:
                continue
            index, stack, component = len(components), [node_id], []
            component_index[node_id] = index
            while stack:
                current = stack.pop()
                component.append(current)
                for other in adjacency[current]:
                    if other not in component_index:
                        component_index[other] = index
                        stack.append(other)
            components.append(component)
        if len(components) <= 1:
            return bridges
        candidates = []
        for index, first in enumerate(corridor_nodes):
            for second in corridor_nodes[index + 1:]:
                if component_index[first["id"]] == component_index[second["id"]]:
                    continue
                a, b = first["position"]["local_m"], second["position"]["local_m"]
                if segment_clear(a, b, blocked):
                    candidates.append((hypot(a["x"] - b["x"], a["y"] - b["y"]), first, second))
        if candidates:
            _distance, first, second = min(candidates, key=lambda item: item[0])
            geometry = [first["position"]["local_m"], second["position"]["local_m"]]
            edges.append({
                "id": f"edge_connector_{first['id']}_{second['id']}", "from": first["id"], "to": second["id"],
                "bidirectional": True, "geometry": {"local_m": geometry},
                "length_m": round(_distance, 6), "source": {"method": "walkable_component_connector_draft"},
            })
            bridges += 1
            continue

        # 직선으로 잇지 못하는 섬은 시설을 피해 A*로 우회한다.
        path_candidate = None
        pairs = []
        for index, first in enumerate(corridor_nodes):
            for second in corridor_nodes[index + 1:]:
                if component_index[first["id"]] != component_index[second["id"]]:
                    a, b = first["position"]["local_m"], second["position"]["local_m"]
                    pairs.append((hypot(a["x"] - b["x"], a["y"] - b["y"]), first, second))
        for _distance, first, second in sorted(pairs, key=lambda item: item[0])[:40]:
            path = walkable_grid_path(first["position"]["local_m"], second["position"]["local_m"], blocked, width, height)
            if path:
                path_candidate = (first, second, simplify_walkable_path(path, blocked))
                break
        # 폭이 4m보다 좁은 통로만 남은 경우에는 가장 가까운 후보에 한해 1m 격자로
        # 재시도한다. 전체 탐색을 촘촘하게 돌리지 않아 생성 시간은 제한한다.
        if path_candidate is None:
            for _distance, first, second in sorted(pairs, key=lambda item: item[0])[:8]:
                path = walkable_grid_path(first["position"]["local_m"], second["position"]["local_m"], blocked, width, height, cell=1.0)
                if path:
                    path_candidate = (first, second, simplify_walkable_path(path, blocked))
                    break
        if path_candidate is None:
            return bridges
        first, second, path = path_candidate
        previous_node = first
        for index, path_point in enumerate(path[1:-1], start=1):
            node = {
                "id": f"connector_corridor_{bridges + 1:02d}_{index:02d}", "type": "corridor",
                "position": {"source": raw_point(path_point), "local_m": path_point},
                "source": {"method": "walkable_astar_connector_draft"},
            }
            corridor_nodes.append(node)
            geometry = [previous_node["position"]["local_m"], node["position"]["local_m"]]
            edges.append({"id": f"edge_connector_{previous_node['id']}_{node['id']}", "from": previous_node["id"], "to": node["id"], "bidirectional": True, "geometry": {"local_m": geometry}, "length_m": round(hypot(geometry[1]["x"] - geometry[0]["x"], geometry[1]["y"] - geometry[0]["y"]), 6), "source": {"method": "walkable_astar_connector_draft"}})
            previous_node = node
        geometry = [previous_node["position"]["local_m"], second["position"]["local_m"]]
        edges.append({"id": f"edge_connector_{previous_node['id']}_{second['id']}", "from": previous_node["id"], "to": second["id"], "bidirectional": True, "geometry": {"local_m": geometry}, "length_m": round(hypot(geometry[1]["x"] - geometry[0]["x"], geometry[1]["y"] - geometry[0]["y"]), 6), "source": {"method": "walkable_astar_connector_draft"}})
        bridges += 1


def store_category(name: str | None) -> tuple[str, str]:
    if not name:
        return "미분류", "원본 이미지 추출"
    if "POP-UP" in name:
        return "팝업", "팝업"
    if name == "ARKET CAFE":
        return "식음료", "카페"
    return "패션·잡화", "패션·잡화"


def merged_escalator_feature(first: int, parts: list[dict]) -> dict:
    points = [point for part in parts for point in part["geometry"]["coordinates"]]
    min_x, max_x = min(p["x"] for p in points), max(p["x"] for p in points)
    min_y, max_y = min(p["y"] for p in points), max(p["y"] for p in points)
    return {
        "id": f"facility-b2-{first:03d}", "kind": "amenity",
        "centroid": {"x": (min_x + max_x) / 2, "y": (min_y + max_y) / 2},
        "geometry": {"type": "Polygon", "coordinates": [
            {"x": min_x, "y": min_y}, {"x": max_x, "y": min_y},
            {"x": max_x, "y": max_y}, {"x": min_x, "y": max_y},
        ]},
        "source_feature_ids": [part["id"] for part in parts],
    }


def main() -> None:
    raw = json.loads(INPUT.read_text(encoding="utf-8"))
    view = raw["coordinate_system"]["view_box"]
    features = raw["features"]
    occupied = [polygon(feature) for feature in features if feature["kind"] in {"store", "amenity"}]
    width, height = view["width"] * SCALE, view["height"] * SCALE

    nodes: list[dict] = []
    by_cell: dict[tuple[int, int], dict] = {}
    for ix, x in enumerate(range(STEP // 2, int(view["width"]), STEP)):
        for iy, y in enumerate(range(STEP // 2, int(view["height"]), STEP)):
            local = point({"x": x, "y": y})
            if any(inside(local["x"], local["y"], shape) for shape in occupied):
                continue
            node = {
                "id": f"corridor_{ix:02d}_{iy:02d}", "type": "corridor",
                "position": {"source": {"x": x, "y": y}, "local_m": local},
            }
            nodes.append(node)
            by_cell[ix, iy] = node

    edges: list[dict] = []
    for (ix, iy), node in by_cell.items():
        for other_key in ((ix + 1, iy), (ix, iy + 1)):
            other = by_cell.get(other_key)
            if other and segment_clear(node["position"]["local_m"], other["position"]["local_m"], occupied):
                geometry = [node["position"]["local_m"], other["position"]["local_m"]]
                edges.append({
                    "id": f"edge_{node['id']}_{other['id']}", "from": node["id"], "to": other["id"],
                    "geometry": {"local_m": geometry},
                    "length_m": round(hypot(geometry[1]["x"] - geometry[0]["x"], geometry[1]["y"] - geometry[0]["y"]), 6),
                    "source": {"method": "image_walkable_grid_draft"},
                })

    corridor_nodes = list(nodes)
    connector_count = connect_corridor_components(corridor_nodes, edges, occupied, width, height)
    nodes = list(corridor_nodes)
    stores: list[dict] = []
    store_features = [f for f in features if f["kind"] == "store" or f["id"].endswith("-067")]
    amenity_features = [f for f in features if f["kind"] == "amenity" and not f["id"].endswith("-067")]
    amenity_by_number = {int(feature["id"].rsplit("-", 1)[1]): feature for feature in amenity_features}
    grouped_numbers = {number for numbers, _name in ESCALATOR_GROUPS.values() for number in numbers}
    logical_amenity_features = [
        feature for feature in amenity_features
        if int(feature["id"].rsplit("-", 1)[1]) not in grouped_numbers
    ]
    logical_amenity_features.extend(
        merged_escalator_feature(first, [amenity_by_number[number] for number in numbers])
        for first, (numbers, _name) in ESCALATOR_GROUPS.items()
    )

    def connect(node: dict, corridor: dict, prefix: str) -> None:
        geometry = [node["position"]["local_m"], corridor["position"]["local_m"]]
        edges.append({
            "id": f"edge_{prefix}_{node['id']}_{corridor['id']}", "from": node["id"], "to": corridor["id"],
            "bidirectional": True, "geometry": {"local_m": geometry},
            "length_m": round(hypot(geometry[1]["x"] - geometry[0]["x"], geometry[1]["y"] - geometry[0]["y"]), 6),
            "source": {"method": "image_feature_to_walkable_grid_draft"},
        })

    # 매장은 개별 입구 노드와 연결한다. 입구는 매장 폴리곤의 경계 중 인접 통로에 가장
    # 가까운 점으로 잡아, Studio에서 polygon ↔ entrance 관계를 바로 편집할 수 있다.
    for feature in store_features:
        number = int(feature["id"].rsplit("-", 1)[1])
        local_centroid = point(feature["centroid"])
        shape = polygon(feature)
        corridor = nearest(local_centroid, corridor_nodes)
        entrance_local = closest_boundary(corridor["position"]["local_m"], shape)
        name = NAMES.get(number)
        entrance = {
            "id": f"store_entrance_b2_{number:03d}", "type": "store_entrance", "name": name or f"B2 미확인 매장 구역 {number:03d}",
            "category": "store_entrance", "position": {"source": raw_point(entrance_local), "local_m": entrance_local},
        }
        nodes.append(entrance)
        connect(entrance, corridor, "store")
        category, subcategory = store_category(name)
        stores.append({
            "id": f"b2_store_{number:03d}", "name": name or f"B2 미확인 매장 구역 {number:03d}",
            "category": category, "subcategory": subcategory,
            "floor_id": FLOOR_ID,
            "entrance_node_id": entrance["id"],
            "entrance_local_m": entrance_local,
            "entrance_wgs84": None,
            "centroid_local_m": local_centroid,
            "polygon_local_m": shape,
            "match": {
                "method": "manual_image_label_match" if name else "connected_component_unmatched",
                "legacy_store_id": feature["id"],
                "review_required": not bool(name),
            },
        })

    for feature in logical_amenity_features:
        number = int(feature["id"].rsplit("-", 1)[1])
        kind, name, category = FACILITIES[number]
        if number in ESCALATOR_GROUPS:
            name = ESCALATOR_GROUPS[number][1]
        local_centroid = point(feature["centroid"])
        corridor = nearest(local_centroid, corridor_nodes)
        shape = polygon(feature)
        anchor = closest_boundary(corridor["position"]["local_m"], shape)
        if kind == "escalator":
            xs, ys = [point["x"] for point in shape], [point["y"] for point in shape]
            center_x = round((min(xs) + max(xs)) / 2, 6)
            access_nodes = []
            for side, y in (("top", min(ys)), ("bottom", max(ys))):
                access = {"x": center_x, "y": y}
                nearest_corridor = nearest(access, corridor_nodes)
                node = {
                    "id": f"escalator_b2_{number:03d}_{side}", "type": "escalator", "name": f"{name} {'상단' if side == 'top' else '하단'}",
                    "category": category, "escalator_id": f"b2_escalator_{number:03d}",
                    "vertical_direction_status": "pending_on_site_verification",
                    "position": {"source": raw_point(access), "local_m": access}, "feature_polygon_local_m": shape,
                }
                nodes.append(node)
                connect(node, nearest_corridor, "escalator_access")
                access_nodes.append(node)
            node = access_nodes[0]
        else:
            node = {
                "id": f"{kind}_b2_{number:03d}", "type": kind, "name": name, "category": category,
                "position": {"source": raw_point(anchor), "local_m": anchor}, "feature_polygon_local_m": shape,
            }
            nodes.append(node)
            connect(node, corridor, "amenity")
            access_nodes = [node]
        # 검색·마커·폴리곤 목록은 매장과 시설을 한 배열에서 다룬다. node.type은
        # 길찾기에서의 의미(엘리베이터/에스컬레이터 등)를 보존한다.
        stores.append({
            "id": f"b2_amenity_{number:03d}", "name": name,
            "category": "편의시설", "subcategory": category,
            "floor_id": FLOOR_ID,
            "entrance_node_id": node["id"], "entrance_node_ids": [item["id"] for item in access_nodes], "entrance_local_m": node["position"]["local_m"],
            "entrance_wgs84": None, "centroid_local_m": local_centroid,
            "polygon_local_m": shape,
            "match": {"method": "manual_image_facility_match", "legacy_store_id": feature["id"], "review_required": False},
        })

    floor = {"id": FLOOR_ID, "name": "B2F", "level": -2, "order": -2}
    footprint = features[0]["geometry"]["coordinates"]
    graph = {
        "schema_version": "0.1.0", "building_id": "thehyundai-seoul", "floor": floor,
        "generated_from": {"provider": "user_supplied_vector_map", "source_artifacts": [str(INPUT)], "credentials_persisted": False},
        "coordinate_system": {
            "type": "provisional_local_meters_top_left", "calibration_version": "b2-floorgraph-studio-v13-draft-v1",
            "source_map_size": {"width": view["width"], "height": view["height"]},
            "floor_bounds_source": {"min_x": 0, "min_y": 0, "width": view["width"], "height": view["height"], "max_x": view["width"], "max_y": view["height"]},
            "scale": {"x_m_per_source_unit": SCALE, "y_m_per_source_unit": SCALE},
            "affine_transforms": {"source_to_local_m": {"type": "affine_2d", "matrix": [[SCALE, 0, 0], [0, SCALE, 0], [0, 0, 1]], "input_axes": ["x", "y"], "output_axes": ["x", "y"]}},
            "notes": ["이미지 좌표 0.1m/px 임시 환산. 실측 또는 공통 앵커로 보정 전에는 층간 정합/WGS84에 사용 금지.", "통로 graph는 매장/시설 폴리곤을 피한 40px 격자 초안이며 현장 검수 필요."],
        },
        "nodes": nodes, "edges": edges,
        # Studio는 이 polygon 목록을 표시한다. 모든 시설을 포함해 통로 간선이 해당
        # 영역을 가로지르는지를 즉시 검수할 수 있다.
        "store_polygons_local_m": [feature["geometry"]["coordinates"] for feature in store_features + logical_amenity_features],
        "store_polygons_imported": True,
        "store_polygon_metadata": [{"id": store["id"], "name": store["name"], "category": store["category"], "subcategory": store["subcategory"], "entrance_node_id": store["entrance_node_id"], "centroid_local_m": store["centroid_local_m"]} for store in stores],
        "manual_review_candidates": [store["id"] for store in stores if store["match"]["review_required"]],
        "counts": {"nodes": len(nodes), "edges": len(edges), "stores": len(store_features), "amenities": len(logical_amenity_features), "polygons": len(stores), "corridor_connectors": connector_count},
        "building_footprint_local_m": footprint,
    }
    store_payload = {"building_id": "thehyundai-seoul", "floor": floor, "coordinate_frame": "studio_local_m", "stores": stores,
                     "unmatched": [store["id"] for store in stores if store["match"]["review_required"]],
                     "summary": {"source": "B2 user supplied vector map", "store_count": len(store_features), "facility_count": len(logical_amenity_features), "polygon_count": len(stores), "named_store_matches": sum(bool(NAMES.get(int(feature["id"].rsplit("-", 1)[1]))) for feature in store_features), "review_required": True}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "b2.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "stores_b2.json").write_text(json.dumps(store_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"b2.json: nodes={len(nodes)} edges={len(edges)}")
    print(f"stores_b2.json: stores={len(stores)} named={store_payload['summary']['named_store_matches']}")


if __name__ == "__main__":
    main()
