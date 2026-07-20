"""FloorGraph Studio graph JSON에서 stores_{floor}.json을 다시 만든다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def apply_matrix(matrix: list[list[float]], point: dict) -> dict[str, float]:
    return {
        "x": round(matrix[0][0] * point["x"] + matrix[0][1] * point["y"] + matrix[0][2], 6),
        "y": round(matrix[1][0] * point["x"] + matrix[1][1] * point["y"] + matrix[1][2], 6),
    }


def centroid(points: list[dict]) -> dict[str, float]:
    area2 = cx = cy = 0.0
    for first, second in zip(points, points[1:] + points[:1]):
        cross = first["x"] * second["y"] - second["x"] * first["y"]
        area2 += cross
        cx += (first["x"] + second["x"]) * cross
        cy += (first["y"] + second["y"]) * cross
    if abs(area2) < 1e-9:
        return {"x": round(sum(point["x"] for point in points) / len(points), 6), "y": round(sum(point["y"] for point in points) / len(points), 6)}
    return {"x": round(cx / (3 * area2), 6), "y": round(cy / (3 * area2), 6)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    graph = json.loads(args.input.read_text(encoding="utf-8"))
    matrix = graph["coordinate_system"]["affine_transforms"]["source_to_local_m"]["matrix"]
    nodes = {node["id"]: node for node in graph["nodes"]}
    stores, unresolved = [], []
    for polygon, metadata in zip(graph.get("store_polygons_local_m", []), graph.get("store_polygon_metadata", [])):
        local_polygon = [apply_matrix(matrix, point) for point in polygon]
        entrance_id = metadata.get("entrance_node_id")
        entrance_node = nodes.get(entrance_id)
        name = metadata.get("name") or metadata["id"]
        category = metadata.get("category")
        subcategory = metadata.get("subcategory")
        if entrance_node and entrance_node.get("type") in {"elevator", "escalator", "restroom", "poi"}:
            # 수작업으로 바꾼 node type/name을 시설 분류의 최종 기준으로 사용한다.
            name = entrance_node.get("name") or name
            category, subcategory = "편의시설", entrance_node["type"]
        if entrance_node is None:
            unresolved.append(metadata["id"])
        stores.append({
            "id": metadata["id"], "name": name, "category": category, "subcategory": subcategory,
            "floor_id": graph["floor"]["id"],
            "entrance_node_id": entrance_id if entrance_node else None,
            "entrance_local_m": entrance_node["position"]["local_m"] if entrance_node else None,
            "entrance_wgs84": None,
            "centroid_local_m": centroid(local_polygon), "polygon_local_m": local_polygon,
            "match": {"method": "floorgraph_studio_manual", "review_required": entrance_node is None},
        })
    payload = {
        "building_id": graph.get("building_id"), "floor": graph["floor"], "coordinate_frame": "studio_local_m",
        "stores": stores, "unmatched": unresolved,
        "summary": {"source": args.input.name, "polygon_count": len(stores), "unresolved_entrance_count": len(unresolved), "review_required": bool(unresolved)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"stores={len(stores)} unresolved_entrances={len(unresolved)}")


if __name__ == "__main__":
    main()
