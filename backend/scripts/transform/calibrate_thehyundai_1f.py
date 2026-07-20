"""더현대 서울 1F의 Dabeo -> SVG -> physical local_m 보정 도구.

기본 실행은 대응점과 가설 치수만 분석해 JSON 보고서를 쓴다. ``--apply``는
물리 스케일과 WGS84 지오리퍼런스가 모두 verified인 calibration에서만 Studio
JSON을 재생성한다. 확인되지 않은 Naver 치수를 production 좌표에 섞지 않기
위한 의도적인 안전 장치다.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CALIBRATION = REPO_ROOT / "backend/resources/calibration/thehyundai-seoul/1f.json"
DEFAULT_REPORT = REPO_ROOT / "backend/resources/calibration/thehyundai-seoul/1f-report.json"
_NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve(relative: str) -> Path:
    return REPO_ROOT / relative


def _normalise_name(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _polygon_centroid(points: list[dict]) -> np.ndarray:
    area2 = cx = cy = 0.0
    for first, second in zip(points, points[1:] + points[:1]):
        cross = first["x"] * second["y"] - second["x"] * first["y"]
        area2 += cross
        cx += (first["x"] + second["x"]) * cross
        cy += (first["y"] + second["y"]) * cross
    if abs(area2) < 1e-9:
        return np.mean([[point["x"], point["y"]] for point in points], axis=0)
    return np.array([cx / (3 * area2), cy / (3 * area2)])


def _parse_path(path_data: str) -> list[dict[str, float]]:
    # 이 SVG의 매장/외곽 path는 M/L/Z만 사용한다. 다른 명령이 들어오면 조용히
    # 오독하지 않고 실패시켜 source artifact 변경을 드러낸다.
    commands = re.findall(r"[A-Za-z]", path_data)
    if any(command not in {"M", "L", "Z"} for command in commands):
        raise ValueError(f"지원하지 않는 SVG path 명령: {commands}")
    values = [float(value) for value in _NUMBER.findall(path_data)]
    if len(values) % 2:
        raise ValueError("SVG path 좌표 수가 홀수입니다.")
    return [{"x": values[index], "y": values[index + 1]} for index in range(0, len(values), 2)]


def _read_svg(path: Path) -> tuple[list[dict], dict[str, np.ndarray]]:
    root = ET.parse(path).getroot()
    footprint: list[dict] | None = None
    stores: dict[str, np.ndarray] = {}
    for element in root.iter():
        if not element.tag.endswith("path"):
            continue
        element_id = element.attrib.get("id")
        path_data = element.attrib.get("d")
        name = element.attrib.get("data-name")
        if not path_data or (element_id != "building-footprint" and not name):
            continue
        points = _parse_path(path_data)
        if element_id == "building-footprint":
            footprint = points
        if name:
            stores[_normalise_name(name)] = _polygon_centroid(points)
    if footprint is None:
        raise ValueError("SVG building-footprint path가 없습니다.")
    return footprint, stores


def _fit_affine(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    design = np.column_stack([source, np.ones(len(source))])
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    return np.vstack([coefficients.T, [0.0, 0.0, 1.0]])


def _apply(matrix: np.ndarray, point: dict | np.ndarray) -> dict[str, float]:
    x, y = (point["x"], point["y"]) if isinstance(point, dict) else point
    result = matrix @ np.array([x, y, 1.0])
    return {"x": round(float(result[0]), 6), "y": round(float(result[1]), 6)}


def _robust_affine(source: np.ndarray, target: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    best: np.ndarray | None = None
    best_error = math.inf
    for sample in itertools.combinations(range(len(source)), 3):
        matrix = _fit_affine(source[list(sample)], target[list(sample)])
        predicted = np.column_stack([source, np.ones(len(source))]) @ matrix[:2].T
        residuals = np.linalg.norm(predicted - target, axis=1)
        inliers = residuals <= threshold
        count = int(inliers.sum())
        error = float(np.median(residuals[inliers])) if count else math.inf
        if best is None or count > int(best.sum()) or (count == int(best.sum()) and error < best_error):
            best, best_error = inliers, error
    if best is None:
        raise ValueError("affine RANSAC 대응점을 찾지 못했습니다.")
    matrix = _fit_affine(source[best], target[best])
    predicted = np.column_stack([source, np.ones(len(source))]) @ matrix[:2].T
    return matrix, best, np.linalg.norm(predicted - target, axis=1)


def analyze(calibration: dict) -> dict:
    footprint, svg_stores = _read_svg(_resolve(calibration["sources"]["svg"]))
    raw_stores = _load(_resolve(calibration["sources"]["dabeeo_stores"]))["stores"]
    aliases = {
        _normalise_name(source): _normalise_name(target)
        for source, target in calibration.get("name_aliases", {}).items()
    }
    matches: list[tuple[str, np.ndarray, np.ndarray]] = []
    unmatched: list[str] = []
    for store in raw_stores:
        key = aliases.get(_normalise_name(store["name"]), _normalise_name(store["name"]))
        svg = svg_stores.get(key)
        if svg is None:
            unmatched.append(store["name"])
            continue
        source = store["centroid"]["source"]
        matches.append((store["name"], np.array([source["x"], source["y"]]), svg))

    source = np.array([item[1] for item in matches])
    target = np.array([item[2] for item in matches])
    matrix, inliers, residuals = _robust_affine(
        source, target, float(calibration["robust_fit"]["inlier_threshold_svg_px"])
    )
    if int(inliers.sum()) < int(calibration["robust_fit"]["minimum_inliers"]):
        raise ValueError(f"control point inlier가 부족합니다: {int(inliers.sum())}")

    singular_values = np.linalg.svd(matrix[:2, :2], compute_uv=False)
    xs, ys = [point["x"] for point in footprint], [point["y"] for point in footprint]
    measurements = []
    for measurement in calibration["physical_scale"]["measurements"]:
        measurements.append({
            "id": measurement["id"],
            "same_vertices_confirmed": measurement["same_vertices_confirmed"],
            "meters_per_svg_px_candidate": measurement["measured_length_m"] / measurement["svg_length_px"],
        })
    candidate_scales = [item["meters_per_svg_px_candidate"] for item in measurements]
    return {
        "calibration_version": calibration["calibration_version"],
        "source_to_svg_px": {
            "matrix": matrix.tolist(),
            "matched": len(matches),
            "inliers": int(inliers.sum()),
            "rmse_inlier_px": float(np.sqrt(np.mean(np.square(residuals[inliers])))),
            "median_inlier_px": float(np.median(residuals[inliers])),
            "max_inlier_px": float(residuals[inliers].max()),
            "linear_singular_values": singular_values.tolist(),
            "anisotropy_ratio": float(singular_values.max() / singular_values.min()),
        },
        "control_points": [
            {"name": name, "residual_svg_px": float(residuals[index]), "inlier": bool(inliers[index])}
            for index, (name, _source, _svg) in enumerate(matches)
        ],
        "unmatched_dabeeo_names": unmatched,
        "svg_footprint_bounds": {
            "min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys),
            "width": max(xs) - min(xs), "height": max(ys) - min(ys),
            "ratio": (max(xs) - min(xs)) / (max(ys) - min(ys)),
        },
        "physical_scale": {
            "status": calibration["physical_scale"]["status"],
            "measurements": measurements,
            "candidate_relative_spread": (max(candidate_scales) - min(candidate_scales)) / np.mean(candidate_scales),
            "production_ready": _is_verified(calibration),
        },
        "vworld_validation": calibration["vworld_validation"],
    }


def _is_verified(calibration: dict) -> bool:
    scale = calibration["physical_scale"]
    georef = calibration["georeference"]
    return (
        scale.get("status") == "verified"
        and isinstance(scale.get("meters_per_svg_px"), (int, float))
        and all(item.get("same_vertices_confirmed") for item in scale["measurements"])
        and georef.get("status") == "verified"
        and georef.get("svg_px_to_wgs84") is not None
    )


def regenerate(calibration: dict, report: dict) -> None:
    if not _is_verified(calibration):
        raise ValueError(
            "production 재생성 거부: physical_scale과 georeference의 동일 꼭짓점 근거가 verified가 아닙니다."
        )
    graph_path = _resolve(calibration["sources"]["studio_graph"])
    stores_path = _resolve(calibration["sources"]["studio_stores"])
    graph, stores = _load(graph_path), _load(stores_path)
    source_to_svg = np.array(report["source_to_svg_px"]["matrix"])
    scale = float(calibration["physical_scale"]["meters_per_svg_px"])
    bounds = report["svg_footprint_bounds"]
    svg_to_local = np.array([[scale, 0, -bounds["min_x"] * scale], [0, scale, -bounds["min_y"] * scale], [0, 0, 1]])
    source_to_local = svg_to_local @ source_to_svg
    svg_to_wgs84 = np.array(calibration["georeference"]["svg_px_to_wgs84"])
    source_to_wgs84 = svg_to_wgs84 @ source_to_svg
    local_to_wgs84 = svg_to_wgs84 @ np.linalg.inv(svg_to_local)
    old_source_to_local = np.array(graph["coordinate_system"]["affine_transforms"]["source_to_local_m"]["matrix"])
    local_to_source = np.linalg.inv(old_source_to_local)

    for node in graph["nodes"]:
        source = node["position"]["source"]
        node["position"]["local_m"] = _apply(source_to_local, source)
        wgs = _apply(source_to_wgs84, source)
        node["position"]["wgs84"] = {"lng": wgs["x"], "lat": wgs["y"]}
    for edge in graph["edges"]:
        source_geometry = edge["geometry"]["source"]
        geometry = [_apply(source_to_local, point) for point in source_geometry]
        edge["geometry"]["local_m"] = geometry
        edge["length_m"] = round(sum(math.dist((a["x"], a["y"]), (b["x"], b["y"])) for a, b in zip(geometry, geometry[1:])), 6)

    footprint, _svg_stores = _read_svg(_resolve(calibration["sources"]["svg"]))
    graph["building_footprint_svg_px"] = footprint
    graph["building_footprint_local_m"] = [_apply(svg_to_local, point) for point in footprint]
    graph["coordinate_system"] = {
        "type": "physical_local_meters_top_left",
        "calibration_version": calibration["calibration_version"],
        "scale": {"meters_per_svg_px": scale},
        "affine_transforms": {
            "source_to_svg_px": {"matrix": source_to_svg.tolist()},
            "svg_px_to_local_m": {"matrix": svg_to_local.tolist()},
            "source_to_local_m": {"matrix": source_to_local.tolist()},
            "svg_px_to_wgs84": {"matrix": svg_to_wgs84.tolist()},
            "source_to_wgs84": {"matrix": source_to_wgs84.tolist()},
            "local_m_to_wgs84": {"matrix": local_to_wgs84.tolist()},
        },
    }

    for store in stores["stores"]:
        for local_key, source_key in (("polygon_local_m", "polygon_source"),):
            source_points = [_apply(local_to_source, point) for point in store.get(local_key) or []]
            store[source_key] = source_points
            store[local_key] = [_apply(source_to_local, point) for point in source_points]
        for local_key, source_key in (("centroid_local_m", "centroid_source"), ("entrance_local_m", "entrance_source")):
            if store.get(local_key) is None:
                continue
            source_point = _apply(local_to_source, store[local_key])
            store[source_key] = source_point
            store[local_key] = _apply(source_to_local, source_point)
        if store.get("entrance_source"):
            wgs = _apply(source_to_wgs84, store["entrance_source"])
            store["entrance_wgs84"] = {"lng": wgs["x"], "lat": wgs["y"]}
    stores["coordinate_frame"] = "physical_local_m"
    stores["map_calibration_version"] = calibration["calibration_version"]
    _dump(graph_path, graph)
    _dump(stores_path, stores)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    calibration = _load(args.calibration)
    report = analyze(calibration)
    _dump(args.report, report)
    if args.apply:
        regenerate(calibration, report)
    print(json.dumps(report["source_to_svg_px"], ensure_ascii=False, indent=2))
    print(f"production_ready={report['physical_scale']['production_ready']}")


if __name__ == "__main__":
    main()
