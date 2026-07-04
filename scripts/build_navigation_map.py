#!/usr/bin/env python3
"""Build a topology-first indoor navigation map from extracted floor assets."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlsplit

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "OpenCV 의존성이 없습니다. `pip install -r requirements.txt`를 먼저 실행하세요. "
        f"원인: {exc}"
    ) from exc

try:
    from pyproj import Transformer
except ImportError:  # pragma: no cover - requirements already include pyproj
    Transformer = None  # type: ignore[assignment]

try:
    from shapely.geometry import Point, Polygon, shape
except ImportError:  # pragma: no cover - requirements already include shapely
    Point = None  # type: ignore[assignment]
    Polygon = None  # type: ignore[assignment]
    shape = None  # type: ignore[assignment]


DEFAULT_FLOOR_ASSETS_DIR = Path("output/floor_assets")
DEFAULT_BUILDING_GEOJSON = Path("output/thehyundai_building.geojson")
DEFAULT_BUILDING_SUMMARY = Path("output/thehyundai_building_summary.json")
DEFAULT_OUTPUT = Path("output/navigation_map.json")
DEFAULT_DEBUG_DIR = Path("output/debug")

LOW_CONFIDENCE_THRESHOLD = 0.65
STORE_CATEGORY_CODES = {"24", "31", "32", "35", "36", "38", "54", "56"}
FACILITY_CATEGORY_CODES = {
    "9991": "toilet",
    "9992": "facility",
    "9993": "elevator",
    "9994": "escalator",
    "9995": "exit",
}


@dataclass(frozen=True)
class CoordinateTransform:
    map_width: float
    map_height: float
    source_bounds: list[float]
    scale_x_m: float
    scale_y_m: float
    bbox_projected: list[float] | None
    source_crs: str | None
    transformer_to_wgs84: Any = None

    def source_to_local(self, x: float, y: float) -> dict[str, float]:
        min_x, min_y, _max_x, _max_y = self.source_bounds
        return {
            "x": float((x - min_x) * self.scale_x_m),
            "y": float((y - min_y) * self.scale_y_m),
        }

    def source_to_projected(self, x: float, y: float) -> dict[str, float] | None:
        if not self.bbox_projected:
            return None
        min_x, _min_y, _max_x, max_y = self.bbox_projected
        local = self.source_to_local(x, y)
        return {
            "x": float(min_x + local["x"]),
            "y": float(max_y - local["y"]),
        }

    def source_to_wgs84(self, x: float, y: float) -> dict[str, float] | None:
        projected = self.source_to_projected(x, y)
        if not projected or self.transformer_to_wgs84 is None:
            return None
        lng, lat = self.transformer_to_wgs84.transform(projected["x"], projected["y"])
        return {"lat": float(lat), "lng": float(lng)}

    def distance_m(self, a: tuple[float, float], b: tuple[float, float]) -> float:
        dx = (a[0] - b[0]) * self.scale_x_m
        dy = (a[1] - b[1]) * self.scale_y_m
        return float(math.hypot(dx, dy))

    @property
    def source_width(self) -> float:
        return max(1.0, self.source_bounds[2] - self.source_bounds[0])

    @property
    def source_height(self) -> float:
        return max(1.0, self.source_bounds[3] - self.source_bounds[1])


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 JSON이 없습니다: {path.resolve()}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def localized_text(value: Any) -> str:
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        for preferred_lang in ("ko", "en"):
            for item in value:
                if isinstance(item, dict) and item.get("lang") == preferred_lang:
                    text = clean_text(item.get("text"))
                    if text:
                        return text
        for item in value:
            if isinstance(item, dict):
                text = clean_text(item.get("text"))
                if text:
                    return text
    return ""


def position_xy(item: dict[str, Any]) -> tuple[float, float] | None:
    pos = item.get("position")
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        return float(pos["x"]), float(pos["y"])
    return None


def coords_xy(item: dict[str, Any]) -> list[tuple[float, float]]:
    coords = item.get("coordinatesArray")
    if isinstance(coords, list) and coords:
        result: list[tuple[float, float]] = []
        for coord in coords:
            if isinstance(coord, list) and len(coord) >= 2:
                result.append((float(coord[0]), float(coord[1])))
        return result

    coords = item.get("coordinates")
    if isinstance(coords, list):
        result: list[tuple[float, float]] = []
        for coord in coords:
            if isinstance(coord, dict) and "x" in coord and "y" in coord:
                result.append((float(coord["x"]), float(coord["y"])))
            elif isinstance(coord, list) and len(coord) >= 2:
                result.append((float(coord[0]), float(coord[1])))
        return result
    return []


def centroid_of_points(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None
    if Polygon is not None and len(points) >= 3:
        polygon = Polygon(points)
        if polygon.is_valid and not polygon.is_empty:
            centroid = polygon.centroid
            return float(centroid.x), float(centroid.y)
    return (
        float(sum(point[0] for point in points) / len(points)),
        float(sum(point[1] for point in points) / len(points)),
    )


def point_payload(x: float, y: float, transform: CoordinateTransform) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": {"x": float(x), "y": float(y)},
        "local_m": transform.source_to_local(x, y),
    }
    projected = transform.source_to_projected(x, y)
    if projected:
        payload["projected"] = projected
    wgs84 = transform.source_to_wgs84(x, y)
    if wgs84:
        payload["wgs84"] = wgs84
    return payload


def polygon_payload(points: list[tuple[float, float]], transform: CoordinateTransform) -> dict[str, Any]:
    local_points = [transform.source_to_local(x, y) for x, y in points]
    source_points = [{"x": float(x), "y": float(y)} for x, y in points]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    local_xs = [point["x"] for point in local_points]
    local_ys = [point["y"] for point in local_points]
    return {
        "source": source_points,
        "local_m": local_points,
        "bbox_source": [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
        "bbox_local_m": [
            float(min(local_xs)),
            float(min(local_ys)),
            float(max(local_xs)),
            float(max(local_ys)),
        ],
    }


def find_map_json(floor_assets_dir: Path) -> Path:
    candidates = sorted((floor_assets_dir / "json").glob("map-*.json"))
    if not candidates:
        raise FileNotFoundError(
            "Dabeeo 지도 JSON을 찾지 못했습니다. 먼저 `scripts/extract_ehyundai_floor_assets.py`를 실행하세요."
        )
    valid: list[Path] = []
    for candidate in candidates:
        try:
            data = read_json(candidate)
        except Exception:
            continue
        payload = data.get("payload", {})
        if isinstance(payload, dict) and payload.get("floors"):
            valid.append(candidate)
    if not valid:
        raise ValueError(f"지도 JSON 후보는 있지만 payload.floors가 없습니다: {candidates}")
    return max(valid, key=lambda path: path.stat().st_size)


def floor_id_from_manifest(floor_assets_dir: Path) -> str | None:
    manifest_path = floor_assets_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = read_json(manifest_path)
    query = parse_qs(urlsplit(str(manifest.get("source_url", ""))).query)
    floor_ids = query.get("floor-id") or query.get("floorId")
    if floor_ids:
        return floor_ids[0]
    return None


def choose_floor(payload: dict[str, Any], requested_floor_id: str | None) -> dict[str, Any]:
    floors = payload.get("floors") or []
    if not floors:
        raise ValueError("지도 JSON에 floors 배열이 없습니다.")

    target_id = requested_floor_id or payload.get("defaultFloorId")
    if target_id:
        for floor in floors:
            if floor.get("id") == target_id:
                return floor

    default_floor_id = payload.get("defaultFloorId")
    for floor in floors:
        if floor.get("id") == default_floor_id:
            return floor
    return floors[0]


def load_building_geojson(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = read_json(path)
    features = data.get("features") or []
    if features:
        return features[0].get("geometry")
    return data.get("geometry") if data.get("type") == "Feature" else data


def compute_floor_source_bounds(floor: dict[str, Any]) -> list[float]:
    points: list[tuple[float, float]] = []
    for obj in floor.get("objects", []):
        if obj.get("attributeCode") == "OB-OUTLINE":
            continue
        points.extend(coords_xy(obj))
        xy = position_xy(obj)
        if xy:
            points.append(xy)
    for poi in floor.get("pois", []):
        xy = position_xy(poi)
        if xy:
            points.append(xy)
    for node in floor.get("nodes", []):
        xy = position_xy(node)
        if xy:
            points.append(xy)

    if not points:
        return [0.0, 0.0, 3000.0, 3000.0]

    min_x = min(x for x, _y in points)
    min_y = min(y for _x, y in points)
    max_x = max(x for x, _y in points)
    max_y = max(y for _x, y in points)
    if max_x <= min_x or max_y <= min_y:
        return [0.0, 0.0, 3000.0, 3000.0]
    return [float(min_x), float(min_y), float(max_x), float(max_y)]


def make_transform(payload: dict[str, Any], building_summary: dict[str, Any], floor: dict[str, Any]) -> CoordinateTransform:
    size = payload.get("size") or {}
    map_width = float(size.get("width") or 3000.0)
    map_height = float(size.get("height") or 3000.0)
    source_bounds = compute_floor_source_bounds(floor)
    bbox_projected = building_summary.get("bbox_projected")
    source_crs = building_summary.get("source_crs")

    if isinstance(bbox_projected, list) and len(bbox_projected) == 4:
        width_m = abs(float(bbox_projected[2]) - float(bbox_projected[0]))
        height_m = abs(float(bbox_projected[3]) - float(bbox_projected[1]))
    else:
        width_m = (source_bounds[2] - source_bounds[0]) * 0.1
        height_m = (source_bounds[3] - source_bounds[1]) * 0.1
        bbox_projected = None

    transformer = None
    if Transformer is not None and source_crs and bbox_projected:
        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)

    return CoordinateTransform(
        map_width=map_width,
        map_height=map_height,
        source_bounds=source_bounds,
        scale_x_m=width_m / max(1.0, source_bounds[2] - source_bounds[0]),
        scale_y_m=height_m / max(1.0, source_bounds[3] - source_bounds[1]),
        bbox_projected=[float(value) for value in bbox_projected] if bbox_projected else None,
        source_crs=str(source_crs) if source_crs else None,
        transformer_to_wgs84=transformer,
    )


def detect_map_bbox(image: np.ndarray) -> tuple[int, int, int, int]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    edges = cv2.Canny(gray, 60, 150)

    row_scores = (edges > 0).sum(axis=1)
    row_candidates = np.where(row_scores > width * 0.35)[0]
    groups = group_consecutive(row_candidates.tolist())
    row_centers = [int((group[0] + group[-1]) / 2) for group in groups if len(group) <= 8]
    row_centers = [row for row in row_centers if height * 0.08 < row < height * 0.9]

    best: tuple[int, int] | None = None
    for i, top in enumerate(row_centers):
        for bottom in row_centers[i + 1 :]:
            if bottom - top > height * 0.25:
                best = (top, bottom)
                break
        if best:
            break

    if best:
        y1, y2 = best
    else:
        y1, y2 = int(height * 0.18), int(height * 0.72)

    band = edges[max(0, y1 - 5) : min(height, y2 + 5), :]
    col_scores = (band > 0).sum(axis=0)
    col_candidates = np.where(col_scores > max(60, (y2 - y1) * 0.3))[0]
    col_groups = group_consecutive(col_candidates.tolist())
    col_centers = [int((group[0] + group[-1]) / 2) for group in col_groups if len(group) <= 12]
    col_centers = [col for col in col_centers if width * 0.005 < col < width * 0.995]

    if len(col_centers) >= 2:
        x1, x2 = col_centers[0], col_centers[-1]
    else:
        x1, x2 = int(width * 0.01), int(width * 0.99)

    if x2 <= x1 or y2 <= y1:
        return 0, 0, width, height
    return max(0, x1), max(0, y1), min(width, x2), min(height, y2)


def group_consecutive(values: list[int]) -> list[list[int]]:
    if not values:
        return []
    groups = [[values[0]]]
    for value in values[1:]:
        if value == groups[-1][-1] + 1:
            groups[-1].append(value)
        else:
            groups.append([value])
    return groups


def remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    labels_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    output = np.zeros_like(mask)
    for label in range(1, labels_count):
        if stats[label, cv2.CC_STAT_AREA] >= min_area:
            output[labels == label] = 255
    return output


def morphological_skeleton(binary_mask: np.ndarray) -> np.ndarray:
    mask = (binary_mask > 0).astype(np.uint8) * 255
    skeleton = np.zeros(mask.shape, np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))

    while cv2.countNonZero(mask) > 0:
        eroded = cv2.erode(mask, element)
        opened = cv2.dilate(eroded, element)
        temp = cv2.subtract(mask, opened)
        skeleton = cv2.bitwise_or(skeleton, temp)
        mask = eroded
    return skeleton


def analyze_floor_image(image_path: Path, debug_dir: Path) -> dict[str, Any]:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"층 안내도 이미지를 읽지 못했습니다: {image_path.resolve()}")

    debug_dir.mkdir(parents=True, exist_ok=True)
    height, width = image.shape[:2]
    x1, y1, x2, y2 = detect_map_bbox(image)
    roi = image[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    corridor_mask = np.where((saturation < 35) & (value > 238), 255, 0).astype(np.uint8)
    corridor_mask = cv2.morphologyEx(corridor_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    corridor_mask = cv2.morphologyEx(corridor_mask, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    corridor_mask = remove_small_components(corridor_mask, min_area=800)

    store_mask = np.where((saturation < 55) & (gray >= 145) & (gray <= 232), 255, 0).astype(np.uint8)
    store_mask = cv2.morphologyEx(store_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    store_mask = cv2.morphologyEx(store_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    wall_mask = cv2.Canny(gray, 50, 140)
    wall_mask = cv2.dilate(wall_mask, np.ones((2, 2), np.uint8), iterations=1)
    skeleton = morphological_skeleton(corridor_mask)

    contours, _hierarchy = cv2.findContours(store_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    store_candidates: list[dict[str, Any]] = []
    roi_area = max(1, roi.shape[0] * roi.shape[1])
    for index, contour in enumerate(contours):
        area = float(cv2.contourArea(contour))
        if area < 250 or area > roi_area * 0.2:
            continue
        bx, by, bw, bh = cv2.boundingRect(contour)
        if bw < 8 or bh < 8:
            continue
        store_candidates.append(
            {
                "id": f"cv_store_{index:03d}",
                "bbox_image": [int(x1 + bx), int(y1 + by), int(x1 + bx + bw), int(y1 + by + bh)],
                "centroid_image": [float(x1 + bx + bw / 2), float(y1 + by + bh / 2)],
                "area_px": area,
                "confidence": 0.52,
            }
        )

    corridor_overlay = image.copy()
    corridor_full = np.zeros((height, width), np.uint8)
    corridor_full[y1:y2, x1:x2] = corridor_mask
    corridor_overlay[corridor_full > 0] = (210, 255, 210)
    cv2.rectangle(corridor_overlay, (x1, y1), (x2, y2), (0, 120, 255), 2)
    cv2.imwrite(str(debug_dir / "corridors.png"), corridor_overlay)

    wall_debug = cv2.cvtColor(wall_mask, cv2.COLOR_GRAY2BGR)
    cv2.imwrite(str(debug_dir / "walls.png"), wall_debug)

    stores_overlay = image.copy()
    for candidate in store_candidates:
        bx1, by1, bx2, by2 = candidate["bbox_image"]
        cv2.rectangle(stores_overlay, (bx1, by1), (bx2, by2), (255, 120, 0), 2)
    cv2.imwrite(str(debug_dir / "stores.png"), stores_overlay)

    skeleton_full = np.zeros((height, width), np.uint8)
    skeleton_full[y1:y2, x1:x2] = skeleton

    return {
        "image_path": str(image_path.resolve()),
        "image_size": {"width": width, "height": height},
        "map_bbox_image": [int(x1), int(y1), int(x2), int(y2)],
        "corridor_mask_pixels": int(cv2.countNonZero(corridor_mask)),
        "wall_candidate_pixels": int(cv2.countNonZero(wall_mask)),
        "store_candidate_count": len(store_candidates),
        "store_candidates": store_candidates,
        "debug_paths": {
            "corridors": str((debug_dir / "corridors.png").resolve()),
            "walls": str((debug_dir / "walls.png").resolve()),
            "stores": str((debug_dir / "stores.png").resolve()),
        },
    }


def initial_source_to_image_affine(
    image_analysis: dict[str, Any],
    transform: CoordinateTransform,
) -> np.ndarray:
    x1, y1, x2, y2 = image_analysis["map_bbox_image"]
    min_x, min_y, max_x, max_y = transform.source_bounds
    sx = (x2 - x1) / max(1.0, max_x - min_x)
    sy = (y2 - y1) / max(1.0, max_y - min_y)
    tx = x1 - sx * min_x
    ty = y1 - sy * min_y
    return np.array([[sx, 0.0, tx], [0.0, sy, ty]], dtype=np.float32)


def source_to_image_point(
    x: float,
    y: float,
    image_analysis: dict[str, Any],
) -> tuple[float, float] | None:
    matrix = image_analysis.get("source_to_image_affine", {}).get("matrix")
    if not matrix:
        return None
    return (
        float(matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]),
        float(matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]),
    )


def image_to_source_point_from_affine(
    x: float,
    y: float,
    matrix: list[list[float]],
) -> tuple[float, float] | None:
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    det = a * e - b * d
    if abs(det) < 1e-9:
        return None
    px = x - c
    py = y - f
    return (
        float((e * px - b * py) / det),
        float((-d * px + a * py) / det),
    )


def mask_dice(a: np.ndarray, b: np.ndarray) -> float:
    a_mask = a > 0
    b_mask = b > 0
    denom = int(a_mask.sum() + b_mask.sum())
    if denom == 0:
        return 0.0
    return float(2.0 * np.logical_and(a_mask, b_mask).sum() / denom)


def calibrate_source_to_image_transform(
    floor: dict[str, Any],
    image_path: Path,
    image_analysis: dict[str, Any],
    transform: CoordinateTransform,
    debug_dir: Path,
) -> None:
    image = cv2.imread(str(image_path))
    if image is None:
        return

    initial = initial_source_to_image_affine(image_analysis, transform)
    h, w = image.shape[:2]
    source_mask = np.zeros((h, w), np.uint8)
    object_codes = {
        "OB-SHOPPING",
        "OB-OTHER_FACILITY",
        "OB-OTHER_FACILITIES",
        "OB-ELEVATOR",
        "OB-TOILET",
        "OB-FIXED_FACILITY",
    }
    for obj in floor.get("objects", []):
        if obj.get("attributeCode") not in object_codes:
            continue
        points = coords_xy(obj)
        if len(points) < 3:
            continue
        polygon = np.array(
            [
                [
                    int(round(initial[0, 0] * x + initial[0, 1] * y + initial[0, 2])),
                    int(round(initial[1, 0] * x + initial[1, 1] * y + initial[1, 2])),
                ]
                for x, y in points
            ],
            dtype=np.int32,
        )
        cv2.fillPoly(source_mask, [polygon], 255)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    target_mask = np.where((hsv[:, :, 1] < 60) & (gray >= 145) & (gray <= 230), 255, 0).astype(np.uint8)
    x1, y1, x2, y2 = image_analysis["map_bbox_image"]
    roi = np.zeros_like(target_mask)
    roi[max(0, y1 - 50) : min(h, y2 + 50), max(0, x1 - 50) : min(w, x2 + 50)] = 255
    target_mask = cv2.bitwise_and(target_mask, roi)
    target_mask = cv2.morphologyEx(target_mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    initial_score = mask_dice(source_mask, target_mask)
    final_matrix = initial.astype(np.float64)
    warp_matrix = np.eye(2, 3, dtype=np.float32)
    ecc_score: float | None = None
    aligned_mask = source_mask

    if cv2.countNonZero(source_mask) > 0 and cv2.countNonZero(target_mask) > 0:
        try:
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6)
            ecc_score, warp_matrix = cv2.findTransformECC(
                target_mask.astype(np.float32) / 255.0,
                source_mask.astype(np.float32) / 255.0,
                warp_matrix,
                cv2.MOTION_AFFINE,
                criteria,
                None,
                5,
            )
            warp3 = np.array(
                [
                    [float(warp_matrix[0, 0]), float(warp_matrix[0, 1]), float(warp_matrix[0, 2])],
                    [float(warp_matrix[1, 0]), float(warp_matrix[1, 1]), float(warp_matrix[1, 2])],
                    [0.0, 0.0, 1.0],
                ],
                dtype=np.float64,
            )
            initial3 = np.array(
                [
                    [float(initial[0, 0]), float(initial[0, 1]), float(initial[0, 2])],
                    [float(initial[1, 0]), float(initial[1, 1]), float(initial[1, 2])],
                    [0.0, 0.0, 1.0],
                ],
                dtype=np.float64,
            )
            final3 = np.linalg.inv(warp3) @ initial3
            final_matrix = final3[:2, :]
            aligned_mask = cv2.warpAffine(
                source_mask,
                warp_matrix,
                (w, h),
                flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP,
            )
        except cv2.error as exc:
            image_analysis.setdefault("calibration_notes", []).append(f"ECC 정합 실패: {exc}")

    final_score = mask_dice(aligned_mask, target_mask)
    image_analysis["source_to_image_affine"] = {
        "matrix": final_matrix.tolist(),
        "initial_matrix": initial.astype(float).tolist(),
        "ecc_warp_matrix": warp_matrix.astype(float).tolist(),
        "initial_dice": float(initial_score),
        "final_dice": float(final_score),
        "ecc_score": float(ecc_score) if ecc_score is not None else None,
        "method": "opencv_findTransformECC_store_mask",
    }

    overlay = image.copy()
    overlay[target_mask > 0] = (0.55 * overlay[target_mask > 0] + 0.45 * np.array([0, 210, 0])).astype(np.uint8)
    overlay[aligned_mask > 0] = (0.55 * overlay[aligned_mask > 0] + 0.45 * np.array([0, 0, 255])).astype(np.uint8)
    calibration_path = debug_dir / "calibration.png"
    cv2.imwrite(str(calibration_path), overlay)
    image_analysis.setdefault("debug_paths", {})["calibration"] = str(calibration_path.resolve())


def image_point_to_source(
    x: float,
    y: float,
    image_analysis: dict[str, Any],
    transform: CoordinateTransform,
) -> tuple[float, float]:
    matrix = image_analysis.get("source_to_image_affine", {}).get("matrix")
    if matrix:
        source = image_to_source_point_from_affine(x, y, matrix)
        if source:
            min_x, min_y, max_x, max_y = transform.source_bounds
            return (
                float(max(min_x, min(max_x, source[0]))),
                float(max(min_y, min(max_y, source[1]))),
            )

    x1, y1, x2, y2 = image_analysis["map_bbox_image"]
    width = max(1.0, float(x2 - x1))
    height = max(1.0, float(y2 - y1))
    min_x, min_y, max_x, max_y = transform.source_bounds
    source_x = min_x + (x - x1) / width * (max_x - min_x)
    source_y = min_y + (y - y1) / height * (max_y - min_y)
    return (
        float(max(min_x, min(max_x, source_x))),
        float(max(min_y, min(max_y, source_y))),
    )


def enrich_image_analysis_coordinates(
    image_analysis: dict[str, Any],
    transform: CoordinateTransform,
) -> None:
    for candidate in image_analysis.get("store_candidates", []):
        bbox = candidate.get("bbox_image")
        center = candidate.get("centroid_image")
        if isinstance(bbox, list) and len(bbox) == 4:
            sx1, sy1 = image_point_to_source(float(bbox[0]), float(bbox[1]), image_analysis, transform)
            sx2, sy2 = image_point_to_source(float(bbox[2]), float(bbox[3]), image_analysis, transform)
            candidate["bbox_source"] = [sx1, sy1, sx2, sy2]
        if isinstance(center, list) and len(center) == 2:
            sx, sy = image_point_to_source(float(center[0]), float(center[1]), image_analysis, transform)
            candidate["centroid"] = point_payload(sx, sy, transform)


def enrich_ocr_coordinates(
    ocr_results: list[dict[str, Any]],
    image_analysis: dict[str, Any],
    transform: CoordinateTransform,
) -> None:
    for result in ocr_results:
        bbox = result.get("bbox_image")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        sx1, sy1 = image_point_to_source(float(bbox[0]), float(bbox[1]), image_analysis, transform)
        sx2, sy2 = image_point_to_source(float(bbox[2]), float(bbox[3]), image_analysis, transform)
        cx = (sx1 + sx2) / 2
        cy = (sy1 + sy2) / 2
        result["bbox_source"] = [sx1, sy1, sx2, sy2]
        result["centroid"] = point_payload(cx, cy, transform)


def run_easyocr(
    image_path: Path,
    debug_dir: Path,
    image_analysis: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    notes: list[str] = []
    try:
        import easyocr  # type: ignore[import-not-found]
    except ImportError:
        notes.append("EasyOCR가 설치되어 있지 않아 OCR 단계는 건너뛰었습니다.")
        return [], notes

    image = cv2.imread(str(image_path))
    if image is None:
        notes.append(f"OCR 입력 이미지를 읽지 못했습니다: {image_path}")
        return [], notes

    ocr_input_path = image_path
    offset_x = 0
    offset_y = 0
    if image_analysis and image_analysis.get("map_bbox_image"):
        x1, y1, x2, y2 = image_analysis["map_bbox_image"]
        crop = image[y1:y2, x1:x2]
        if crop.size > 0:
            ocr_input_path = debug_dir / "ocr_input_crop.png"
            cv2.imwrite(str(ocr_input_path), crop)
            offset_x = int(x1)
            offset_y = int(y1)

    reader = easyocr.Reader(["ko", "en"], gpu=False)
    raw_results = reader.readtext(str(ocr_input_path), detail=1, paragraph=False)
    results: list[dict[str, Any]] = []
    debug = image.copy()
    for index, item in enumerate(raw_results):
        bbox, text, confidence = item
        points = [[float(x + offset_x), float(y + offset_y)] for x, y in bbox]
        if not clean_text(text):
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        result = {
            "id": f"ocr_{index:03d}",
            "text": clean_text(text),
            "confidence": float(confidence),
            "bbox_image": [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
            "polygon_image": points,
            "engine": "easyocr",
        }
        results.append(result)
        color = (0, 180, 0) if confidence >= 0.65 else (0, 120, 255)
        int_points = np.array([[int(x), int(y)] for x, y in points], dtype=np.int32)
        cv2.polylines(debug, [int_points], True, color, 2)
        cv2.putText(
            debug,
            f"{clean_text(text)[:12]} {confidence:.2f}",
            (int(min(xs)), max(15, int(min(ys) - 4))),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )
    cv2.imwrite(str(debug_dir / "ocr_result.png"), debug)
    return results, notes


def classify_node(node: dict[str, Any], degree: int) -> str:
    trans_code = str(node.get("transCode") or "")
    title = clean_text(node.get("title")).lower()
    if "ELEVATOR" in trans_code:
        return "elevator"
    if "ESCALATOR" in trans_code:
        return "escalator"
    if "STAIR" in trans_code or "계단" in title:
        return "stairs"
    if "EXIT" in trans_code or "출구" in title:
        return "exit"
    if degree >= 3:
        return "junction"
    if degree == 1:
        return "dead_end"
    return "corridor"


def normalize_poi_type(value: str) -> str:
    text = value.upper()
    if "ELEVATOR" in text or "엘리베이터" in value:
        return "elevator"
    if "ESCALATOR" in text or "에스컬레이터" in value:
        return "escalator"
    if "STAIR" in text or "계단" in value:
        return "stairs"
    if "EXIT" in text or "출구" in value:
        return "exit"
    if "TOILET" in text or "화장실" in value:
        return "toilet"
    return "poi"


def build_nodes_and_edges(
    floor: dict[str, Any],
    transform: CoordinateTransform,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    source_nodes = floor.get("nodes") or []
    source_by_id = {node.get("id"): node for node in source_nodes if node.get("id")}
    degree_by_id: dict[str, int] = {}
    for node in source_nodes:
        node_id = node.get("id")
        if not node_id:
            continue
        degree_by_id[node_id] = sum(
            1
            for edge in node.get("edges", [])
            if edge.get("passable", True)
            and not edge.get("linkedFloorId")
            and edge.get("nodeId") in source_by_id
        )

    nodes: list[dict[str, Any]] = []
    node_lookup: dict[str, dict[str, Any]] = {}
    for node in source_nodes:
        node_id = str(node.get("id"))
        xy = position_xy(node)
        if not node_id or xy is None:
            continue
        degree = degree_by_id.get(node_id, 0)
        nav_node = {
            "id": node_id,
            "type": classify_node(node, degree),
            "name": clean_text(node.get("title")),
            "floor_id": floor.get("id"),
            "degree": degree,
            "position": point_payload(xy[0], xy[1], transform),
            "source": {
                "kind": "dabeeo_node",
                "trans_code": node.get("transCode"),
                "object_ids": node.get("objectIds") or [],
            },
            "confidence": 0.95,
        }
        nodes.append(nav_node)
        node_lookup[node_id] = nav_node

    edges: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for node in source_nodes:
        source_id = str(node.get("id"))
        if source_id not in node_lookup:
            continue
        source_xy = position_xy(node)
        if source_xy is None:
            continue
        for edge in node.get("edges", []):
            target_id = str(edge.get("nodeId") or "")
            if not edge.get("passable", True) or edge.get("linkedFloorId") or target_id not in node_lookup:
                continue
            pair = tuple(sorted((source_id, target_id)))
            if pair in seen_pairs:
                continue
            target_xy = position_xy(source_by_id[target_id])
            if target_xy is None:
                continue
            seen_pairs.add(pair)
            edges.append(
                {
                    "id": f"edge_{len(edges):05d}",
                    "from": source_id,
                    "to": target_id,
                    "bidirectional": True,
                    "length_m": transform.distance_m(source_xy, target_xy),
                    "source_distance": float(edge.get("distance") or 0.0),
                    "geometry": {
                        "source": [
                            {"x": float(source_xy[0]), "y": float(source_xy[1])},
                            {"x": float(target_xy[0]), "y": float(target_xy[1])},
                        ],
                        "local_m": [
                            transform.source_to_local(source_xy[0], source_xy[1]),
                            transform.source_to_local(target_xy[0], target_xy[1]),
                        ],
                    },
                    "confidence": 0.95,
                    "source": {"kind": "dabeeo_edge", "source_edge_id": edge.get("id")},
                }
            )

    return nodes, edges, node_lookup


def is_store_poi(poi: dict[str, Any], object_by_id: dict[str, dict[str, Any]]) -> bool:
    object_id = poi.get("objectId")
    obj = object_by_id.get(object_id or "")
    icon = str(poi.get("iconUrl") or "").lower()
    category = str(poi.get("categoryCode") or "")
    if obj and obj.get("attributeCode") == "OB-SHOPPING":
        return True
    return category in STORE_CATEGORY_CODES or "store" in icon


def nearest_graph_connection(
    point: tuple[float, float],
    node_lookup: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    transform: CoordinateTransform,
) -> tuple[dict[str, Any], str | None]:
    best_edge: tuple[float, dict[str, Any], tuple[float, float], str] | None = None
    for edge in edges:
        source_geom = edge.get("geometry", {}).get("source") or []
        if len(source_geom) != 2:
            continue
        a = (float(source_geom[0]["x"]), float(source_geom[0]["y"]))
        b = (float(source_geom[1]["x"]), float(source_geom[1]["y"]))
        projected, ratio = project_point_to_segment(point, a, b)
        distance = transform.distance_m(point, projected)
        nearest_endpoint = edge["from"] if ratio <= 0.5 else edge["to"]
        if best_edge is None or distance < best_edge[0]:
            best_edge = (distance, edge, projected, nearest_endpoint)

    if best_edge:
        _distance, edge, projected, nearest_endpoint = best_edge
        return {
            "position": point_payload(projected[0], projected[1], transform),
            "nearest_edge_id": edge["id"],
            "nearest_node_id": nearest_endpoint,
        }, nearest_endpoint

    best_node_id = None
    best_distance = math.inf
    for node_id, node in node_lookup.items():
        source = node["position"]["source"]
        node_point = (float(source["x"]), float(source["y"]))
        distance = transform.distance_m(point, node_point)
        if distance < best_distance:
            best_distance = distance
            best_node_id = node_id
    return {"position": point_payload(point[0], point[1], transform), "nearest_node_id": best_node_id}, best_node_id


def project_point_to_segment(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[tuple[float, float], float]:
    px, py = point
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return a, 0.0
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return (ax + ratio * dx, ay + ratio * dy), ratio


def build_stores(
    floor: dict[str, Any],
    transform: CoordinateTransform,
    node_lookup: dict[str, dict[str, Any]],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    ocr_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    object_by_id = {str(obj.get("id")): obj for obj in floor.get("objects", []) if obj.get("id")}
    stores: list[dict[str, Any]] = []
    used_poi_ids: set[str] = set()

    for poi in floor.get("pois", []):
        if not is_store_poi(poi, object_by_id):
            continue
        poi_id = str(poi.get("id"))
        if poi_id in used_poi_ids:
            continue
        used_poi_ids.add(poi_id)

        object_id = str(poi.get("objectId") or "")
        obj = object_by_id.get(object_id)
        points = coords_xy(obj) if obj else []
        centroid = centroid_of_points(points) if points else position_xy(poi)
        if centroid is None:
            continue

        name = localized_text(poi.get("titleByLanguages")) or clean_text(poi.get("title")) or f"store_{len(stores):03d}"
        ocr_match = match_ocr(name, centroid, ocr_results)
        confidence = 0.88 if obj and points else 0.76
        if ocr_match:
            confidence = max(confidence, min(0.96, 0.55 + ocr_match["confidence"] * 0.4))

        entrance, nearest_node_id = nearest_graph_connection(centroid, node_lookup, edges, transform)
        entrance_node_id = f"store_entrance_{len(stores):03d}"
        entrance_source = entrance["position"]["source"]
        entrance_nav_node = {
            "id": entrance_node_id,
            "type": "store_entrance",
            "name": name,
            "floor_id": floor.get("id"),
            "degree": 1,
            "position": entrance["position"],
            "source": {
                "kind": "generated_store_entrance",
                "store_poi_id": poi_id,
                "nearest_edge_id": entrance.get("nearest_edge_id"),
                "nearest_node_id": nearest_node_id,
            },
            "confidence": round(confidence * 0.9, 4),
        }
        nodes.append(entrance_nav_node)
        node_lookup[entrance_node_id] = entrance_nav_node

        if nearest_node_id and nearest_node_id in node_lookup:
            nearest_source = node_lookup[nearest_node_id]["position"]["source"]
            edges.append(
                {
                    "id": f"store_edge_{len(stores):03d}",
                    "from": entrance_node_id,
                    "to": nearest_node_id,
                    "bidirectional": True,
                    "length_m": transform.distance_m(
                        (float(entrance_source["x"]), float(entrance_source["y"])),
                        (float(nearest_source["x"]), float(nearest_source["y"])),
                    ),
                    "geometry": {
                        "source": [
                            {"x": float(entrance_source["x"]), "y": float(entrance_source["y"])},
                            {"x": float(nearest_source["x"]), "y": float(nearest_source["y"])},
                        ],
                        "local_m": [
                            transform.source_to_local(float(entrance_source["x"]), float(entrance_source["y"])),
                            transform.source_to_local(float(nearest_source["x"]), float(nearest_source["y"])),
                        ],
                    },
                    "confidence": round(confidence * 0.85, 4),
                    "source": {"kind": "generated_store_connection", "store_poi_id": poi_id},
                }
            )

        store: dict[str, Any] = {
            "id": f"store_{len(stores):03d}",
            "source_id": poi_id,
            "object_id": object_id or None,
            "name": name,
            "centroid": point_payload(centroid[0], centroid[1], transform),
            "entrance": entrance["position"],
            "entrance_node_id": entrance_node_id,
            "nearest_node_id": nearest_node_id,
            "nearest_edge_id": entrance.get("nearest_edge_id"),
            "confidence": round(confidence, 4),
            "source": {
                "kind": "dabeeo_poi",
                "category_code": poi.get("categoryCode"),
                "title_by_languages": poi.get("titleByLanguages"),
            },
        }
        if points:
            store["polygon"] = polygon_payload(points, transform)
        else:
            store["bbox"] = None
        if ocr_match:
            store["ocr"] = {
                "id": ocr_match["id"],
                "text": ocr_match["text"],
                "confidence": ocr_match["confidence"],
            }
        stores.append(store)
    return stores


def match_ocr(
    store_name: str,
    centroid: tuple[float, float],
    ocr_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not ocr_results:
        return None
    compact_name = compact_text_for_match(store_name)
    best: tuple[float, dict[str, Any]] | None = None
    for result in ocr_results:
        compact_ocr = compact_text_for_match(str(result.get("text") or ""))
        if not compact_ocr:
            continue
        if compact_ocr in compact_name or compact_name in compact_ocr:
            text_score = 1.0
        else:
            text_score = SequenceMatcher(None, compact_name, compact_ocr).ratio()

        distance_penalty = 0.0
        ocr_centroid = result.get("centroid", {}).get("source") if isinstance(result.get("centroid"), dict) else None
        if isinstance(ocr_centroid, dict):
            distance_source = math.hypot(float(ocr_centroid["x"]) - centroid[0], float(ocr_centroid["y"]) - centroid[1])
            distance_penalty = min(0.35, distance_source / 700.0)

        score = text_score - distance_penalty
        if score >= 0.55 and (best is None or score > best[0]):
            best = (score, result)
    return best[1] if best else None


def compact_text_for_match(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).lower()


def build_pois(
    floor: dict[str, Any],
    transform: CoordinateTransform,
    node_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    object_by_id = {str(obj.get("id")): obj for obj in floor.get("objects", []) if obj.get("id")}
    pois: list[dict[str, Any]] = []
    seen: set[str] = set()

    for node in node_lookup.values():
        source = node.get("source", {})
        trans_code = str(source.get("trans_code") or "")
        if node["type"] in {"elevator", "escalator", "stairs", "exit"}:
            poi_id = f"poi_{node['id']}"
            seen.add(poi_id)
            pois.append(
                {
                    "id": poi_id,
                    "type": node["type"],
                    "name": node.get("name") or node["type"],
                    "centroid": node["position"],
                    "linked_node_id": node["id"],
                    "confidence": 0.94,
                    "source": {"kind": "dabeeo_node", "trans_code": trans_code},
                }
            )

    for poi in floor.get("pois", []):
        if is_store_poi(poi, object_by_id):
            continue
        xy = position_xy(poi)
        if xy is None:
            object_id = str(poi.get("objectId") or "")
            obj = object_by_id.get(object_id)
            xy = centroid_of_points(coords_xy(obj)) if obj else None
        if xy is None:
            continue
        category = str(poi.get("categoryCode") or "")
        name = localized_text(poi.get("titleByLanguages")) or clean_text(poi.get("title"))
        poi_type = FACILITY_CATEGORY_CODES.get(category) or normalize_poi_type(name)
        nearest_node_id = nearest_node_to_point(xy, node_lookup, transform)
        pois.append(
            {
                "id": f"poi_{len(pois):03d}",
                "source_id": poi.get("id"),
                "type": poi_type,
                "name": name or poi_type,
                "centroid": point_payload(xy[0], xy[1], transform),
                "linked_node_id": nearest_node_id,
                "confidence": 0.82,
                "source": {"kind": "dabeeo_poi", "category_code": category, "object_id": poi.get("objectId")},
            }
        )
    return pois


def build_floor_regions(floor: dict[str, Any], transform: CoordinateTransform) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    walls: list[dict[str, Any]] = []
    for index, section in enumerate(floor.get("sections", [])):
        points = coords_xy(section)
        if len(points) >= 3:
            sections.append(
                {
                    "id": str(section.get("id") or f"section_{index:03d}"),
                    "name": clean_text(section.get("title")),
                    "polygon": polygon_payload(points, transform),
                    "confidence": 0.82,
                    "source": {
                        "kind": "dabeeo_section",
                        "attribute_code": section.get("attributeCode"),
                        "passable": section.get("passable"),
                    },
                }
            )

    for index, obj in enumerate(floor.get("objects", [])):
        if obj.get("attributeCode") != "OB-OUTLINE":
            continue
        points = coords_xy(obj)
        if len(points) >= 2:
            walls.append(
                {
                    "id": str(obj.get("id") or f"wall_{index:03d}"),
                    "geometry": polygon_payload(points, transform) if len(points) >= 3 else None,
                    "confidence": 0.7,
                    "source": {"kind": "dabeeo_outline_object"},
                }
            )
    return {"sections": sections, "wall_candidates": walls}


def nearest_node_to_point(
    point: tuple[float, float],
    node_lookup: dict[str, dict[str, Any]],
    transform: CoordinateTransform,
) -> str | None:
    best_node_id = None
    best_distance = math.inf
    for node_id, node in node_lookup.items():
        source = node["position"]["source"]
        node_point = (float(source["x"]), float(source["y"]))
        distance = transform.distance_m(point, node_point)
        if distance < best_distance:
            best_node_id = node_id
            best_distance = distance
    return best_node_id


def manual_review_candidates(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
    stores: Iterable[dict[str, Any]],
    pois: Iterable[dict[str, Any]],
    ocr_results: Iterable[dict[str, Any]],
    notes: list[str],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for kind, items in (("node", nodes), ("edge", edges), ("store", stores), ("poi", pois), ("ocr", ocr_results)):
        for item in items:
            confidence = float(item.get("confidence") or 0)
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                candidates.append(
                    {
                        "kind": kind,
                        "id": item.get("id"),
                        "confidence": confidence,
                        "reason": "low_confidence",
                    }
                )
    for note in notes:
        if "OCR" in note or "EasyOCR" in note:
            candidates.append(
                {
                    "kind": "pipeline",
                    "id": "ocr",
                    "confidence": 0.0,
                    "reason": note,
                }
            )
    return candidates


def draw_navigation_debug(
    image_path: Path,
    debug_dir: Path,
    image_analysis: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    stores: list[dict[str, Any]],
    pois: list[dict[str, Any]],
    transform: CoordinateTransform,
) -> dict[str, str]:
    image = cv2.imread(str(image_path))
    if image is None:
        return {}

    x1, y1, x2, y2 = image_analysis["map_bbox_image"]
    map_w = max(1, x2 - x1)
    map_h = max(1, y2 - y1)

    def to_image(source: dict[str, Any]) -> tuple[int, int]:
        sx = float(source["x"])
        sy = float(source["y"])
        calibrated = source_to_image_point(sx, sy, image_analysis)
        if calibrated:
            return int(round(calibrated[0])), int(round(calibrated[1]))
        min_x, min_y, max_x, max_y = transform.source_bounds
        return (
            int(round(x1 + (sx - min_x) / max(1.0, max_x - min_x) * map_w)),
            int(round(y1 + (sy - min_y) / max(1.0, max_y - min_y) * map_h)),
        )

    graph_debug = image.copy()
    node_by_id = {node["id"]: node for node in nodes}
    for edge in edges:
        a = node_by_id.get(edge["from"])
        b = node_by_id.get(edge["to"])
        if not a or not b:
            continue
        cv2.line(graph_debug, to_image(a["position"]["source"]), to_image(b["position"]["source"]), (255, 60, 60), 2)
    for node in nodes:
        color = (30, 30, 220) if node["type"] != "store_entrance" else (0, 120, 255)
        cv2.circle(graph_debug, to_image(node["position"]["source"]), 3, color, -1)
    cv2.imwrite(str(debug_dir / "navigation_graph.png"), graph_debug)

    final_debug = image.copy()
    for store in stores:
        if store.get("polygon"):
            points = np.array([to_image(point) for point in store["polygon"]["source"]], dtype=np.int32)
            cv2.polylines(final_debug, [points], True, (255, 140, 0), 2)
        center = to_image(store["centroid"]["source"])
        entrance = to_image(store["entrance"]["source"])
        cv2.circle(final_debug, center, 4, (0, 160, 255), -1)
        cv2.line(final_debug, center, entrance, (0, 160, 255), 1)
    for edge in edges:
        a = node_by_id.get(edge["from"])
        b = node_by_id.get(edge["to"])
        if not a or not b:
            continue
        cv2.line(final_debug, to_image(a["position"]["source"]), to_image(b["position"]["source"]), (80, 80, 230), 1)
    for poi in pois:
        cv2.circle(final_debug, to_image(poi["centroid"]["source"]), 5, (0, 180, 0), -1)
    cv2.imwrite(str(debug_dir / "final_navigation_map.png"), final_debug)

    ocr_debug = debug_dir / "ocr_result.png"
    if not ocr_debug.exists():
        cv2.imwrite(str(ocr_debug), image)

    return {
        "navigation_graph": str((debug_dir / "navigation_graph.png").resolve()),
        "ocr_result": str(ocr_debug.resolve()),
        "final_navigation_map": str((debug_dir / "final_navigation_map.png").resolve()),
    }


def choose_image(floor_assets_dir: Path) -> Path:
    for name in ("map_element_screenshot.png", "page_screenshot.png", "highres_screenshot.png"):
        path = floor_assets_dir / name
        if path.exists():
            return path
    raise FileNotFoundError(f"층 안내도 스크린샷을 찾지 못했습니다: {floor_assets_dir.resolve()}")


def build_navigation_map(
    floor_assets_dir: Path = DEFAULT_FLOOR_ASSETS_DIR,
    building_geojson_path: Path = DEFAULT_BUILDING_GEOJSON,
    building_summary_path: Path = DEFAULT_BUILDING_SUMMARY,
    output_path: Path = DEFAULT_OUTPUT,
    debug_dir: Path = DEFAULT_DEBUG_DIR,
    floor_id: str | None = None,
    image_path: Path | None = None,
    skip_ocr: bool = False,
) -> dict[str, Any]:
    floor_assets_dir = Path(floor_assets_dir)
    map_json_path = find_map_json(floor_assets_dir)
    map_json = read_json(map_json_path)
    payload = map_json.get("payload") or {}
    requested_floor_id = floor_id or floor_id_from_manifest(floor_assets_dir)
    floor = choose_floor(payload, requested_floor_id)
    building_summary = read_json(building_summary_path)
    building_geometry = load_building_geojson(building_geojson_path)
    transform = make_transform(payload, building_summary, floor)
    selected_image = Path(image_path) if image_path else choose_image(floor_assets_dir)

    notes: list[str] = []
    image_analysis = analyze_floor_image(selected_image, debug_dir)
    calibrate_source_to_image_transform(floor, selected_image, image_analysis, transform, debug_dir)
    enrich_image_analysis_coordinates(image_analysis, transform)
    if skip_ocr:
        ocr_results: list[dict[str, Any]] = []
        notes.append("사용자 옵션으로 OCR을 건너뛰었습니다.")
    else:
        ocr_results, ocr_notes = run_easyocr(selected_image, debug_dir, image_analysis)
        notes.extend(ocr_notes)
    enrich_ocr_coordinates(ocr_results, image_analysis, transform)

    nodes, edges, node_lookup = build_nodes_and_edges(floor, transform)
    stores = build_stores(floor, transform, node_lookup, nodes, edges, ocr_results)
    pois = build_pois(floor, transform, node_lookup)
    floor_regions = build_floor_regions(floor, transform)

    debug_paths = dict(image_analysis.get("debug_paths") or {})
    debug_paths.update(
        draw_navigation_debug(
            selected_image,
            debug_dir,
            image_analysis,
            nodes,
            edges,
            stores,
            pois,
            transform,
        )
    )

    map_name = localized_text(payload.get("name")) or clean_text(payload.get("name")) or "The Hyundai Seoul"
    floor_name = localized_text(floor.get("name")) or clean_text(floor.get("name")) or str(floor.get("id"))
    navigation_map = {
        "schema_version": "0.1.0",
        "generated_from": {
            "floor_assets_dir": str(floor_assets_dir.resolve()),
            "map_json": str(map_json_path.resolve()),
            "floor_image": str(selected_image.resolve()),
            "building_geojson": str(building_geojson_path.resolve()),
            "building_summary": str(building_summary_path.resolve()),
        },
        "building": {
            "name": map_name,
            "floor": {
                "id": floor.get("id"),
                "name": floor_name,
                "level": floor.get("level"),
                "order": floor.get("order"),
            },
            "source_crs": building_summary.get("source_crs"),
            "bbox_projected": building_summary.get("bbox_projected"),
            "bbox_wgs84": building_summary.get("bbox_wgs84"),
            "area_m2": building_summary.get("area_m2"),
            "perimeter_m": building_summary.get("perimeter_m"),
            "exterior_geojson": building_geometry,
        },
        "coordinate_system": {
            "type": "local_meters_top_left",
            "source_map_size": {"width": transform.map_width, "height": transform.map_height},
            "floor_bounds_source": {
                "min_x": transform.source_bounds[0],
                "min_y": transform.source_bounds[1],
                "max_x": transform.source_bounds[2],
                "max_y": transform.source_bounds[3],
                "width": transform.source_width,
                "height": transform.source_height,
            },
            "scale": {
                "x_m_per_source_unit": transform.scale_x_m,
                "y_m_per_source_unit": transform.scale_y_m,
            },
            "notes": [
                "좌표 변환은 VWorld 건물 외곽 bbox와 실제 1F floor content bounds의 선형 매핑입니다.",
                "CAD 정밀도보다 navigation graph topology 보존을 우선합니다.",
            ],
        },
        "preview": {
            "background_image": str(selected_image.resolve()),
            "image_size": image_analysis.get("image_size"),
            "map_bbox_image": image_analysis.get("map_bbox_image"),
            "source_bounds": {
                "min_x": transform.source_bounds[0],
                "min_y": transform.source_bounds[1],
                "max_x": transform.source_bounds[2],
                "max_y": transform.source_bounds[3],
            },
        },
        "image_analysis": image_analysis,
        "floor_regions": floor_regions,
        "ocr_results": ocr_results,
        "nodes": nodes,
        "edges": edges,
        "stores": stores,
        "pois": pois,
        "manual_review_candidates": manual_review_candidates(nodes, edges, stores, pois, ocr_results, notes),
        "debug": debug_paths,
        "notes": notes,
    }
    write_json(output_path, navigation_map)
    print(f"Navigation nodes: {len(nodes)}")
    print(f"Navigation edges: {len(edges)}")
    print(f"Stores: {len(stores)}")
    print(f"POIs: {len(pois)}")
    print(f"Manual review candidates: {len(navigation_map['manual_review_candidates'])}")
    print(f"Navigation map 저장: {output_path.resolve()}")
    return navigation_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="추출된 더현대서울 floor asset으로 topology 기반 indoor navigation map을 생성합니다.")
    parser.add_argument("--floor-assets-dir", default=str(DEFAULT_FLOOR_ASSETS_DIR), help="기존 층 안내도 추출 산출물 디렉토리")
    parser.add_argument("--building-geojson", default=str(DEFAULT_BUILDING_GEOJSON), help="VWorld 건물 외곽 GeoJSON")
    parser.add_argument("--building-summary", default=str(DEFAULT_BUILDING_SUMMARY), help="VWorld 건물 외곽 summary JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="navigation_map.json 출력 경로")
    parser.add_argument("--debug-dir", default=str(DEFAULT_DEBUG_DIR), help="debug 이미지 출력 디렉토리")
    parser.add_argument("--floor-id", help="처리할 Dabeeo floor id. 생략하면 manifest URL의 floor-id 또는 defaultFloorId 사용")
    parser.add_argument("--image", help="OpenCV/OCR 분석에 사용할 층 안내도 이미지")
    parser.add_argument("--skip-ocr", action="store_true", help="OCR 실행을 건너뜁니다.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_navigation_map(
            floor_assets_dir=Path(args.floor_assets_dir),
            building_geojson_path=Path(args.building_geojson),
            building_summary_path=Path(args.building_summary),
            output_path=Path(args.output),
            debug_dir=Path(args.debug_dir),
            floor_id=args.floor_id,
            image_path=Path(args.image) if args.image else None,
            skip_ocr=args.skip_ocr,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should print root cause
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
