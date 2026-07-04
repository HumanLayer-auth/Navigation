#!/usr/bin/env python3
"""Extract The Hyundai Seoul building polygon from VWorld building SHP data."""

from __future__ import annotations

import argparse
import json
import math
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    import geopandas as gpd
    import pandas as pd
    from pyproj import CRS, Transformer
    from shapely.geometry import Point
except ImportError as exc:  # pragma: no cover - exercised before dependencies exist
    raise SystemExit(
        "필수 Python 패키지가 없습니다. 먼저 `pip install -r requirements.txt`를 실행하세요. "
        f"원인: {exc}"
    ) from exc


DEFAULT_SHP_FILENAME = "AL_D010_11_20260609.shp"
DEFAULT_TARGET_LAT = 37.5259
DEFAULT_TARGET_LNG = 126.9284
DEFAULT_OUTPUT_DIR = Path("thehyundai_indoor_navigation_dataset")
BUILDING_GEOJSON_NAME = "thehyundai_building.geojson"
BUILDING_SUMMARY_NAME = "thehyundai_building_summary.json"

KEYWORDS = (
    "더현대서울",
    "현대백화점",
    "여의대로 108",
    "서울특별시 영등포구 여의대로 108",
)
STRONG_KEYWORDS = (
    "더현대서울",
    "여의대로 108",
    "서울특별시 영등포구 여의대로 108",
)
DEFAULT_MAX_ATTRIBUTE_DISTANCE_M = 500.0

REQUIRED_SIDECARS = (".shp", ".dbf", ".shx", ".prj")
OPTIONAL_SIDECARS = (".fix",)


def normalize_for_path_match(value: str) -> str:
    """Normalize Korean path text enough to survive macOS NFD/NFC differences."""
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(normalized.casefold().split())


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def expected_file_list(shp_path: Path | None = None) -> list[str]:
    base = shp_path.with_suffix("") if shp_path else Path(DEFAULT_SHP_FILENAME).with_suffix("")
    return [str(base.with_suffix(suffix)) for suffix in REQUIRED_SIDECARS + OPTIONAL_SIDECARS]


def resolve_shp_path(shp_arg: str | None, cwd: Path) -> Path:
    """Resolve the SHP path while tolerating Korean folder spelling/normalization drift."""
    attempted: list[Path] = []

    if shp_arg:
        supplied = Path(shp_arg).expanduser()
        attempted.append(supplied if supplied.is_absolute() else cwd / supplied)
    else:
        folder_candidates = [
            "서울특별시 gis 데이터",
            "서울특별시 GIS데이터",
            "서울특별시 GIS 데이터",
            "서울특별시 gis데이터",
        ]
        attempted.extend(cwd / folder / DEFAULT_SHP_FILENAME for folder in folder_candidates)

        target_dir_key = normalize_for_path_match("서울특별시 gis 데이터")
        for child in cwd.iterdir():
            if child.is_dir() and normalize_for_path_match(child.name) == target_dir_key:
                attempted.append(child / DEFAULT_SHP_FILENAME)

    for path in unique_paths(attempted):
        if path.exists():
            return path

    recursive_matches = sorted(cwd.rglob(DEFAULT_SHP_FILENAME))
    if recursive_matches:
        return recursive_matches[0]

    attempted_text = "\n".join(f"  - {path}" for path in unique_paths(attempted)) or "  - (없음)"
    required_text = "\n".join(f"  - {item}" for item in expected_file_list())
    raise FileNotFoundError(
        "SHP 파일을 찾지 못했습니다.\n"
        f"현재 작업 디렉토리: {cwd}\n"
        f"시도한 경로:\n{attempted_text}\n"
        f"필요한 파일 목록:\n{required_text}"
    )


def validate_shapefile_parts(shp_path: Path) -> None:
    missing_required = [shp_path.with_suffix(suffix) for suffix in REQUIRED_SIDECARS if not shp_path.with_suffix(suffix).exists()]
    if missing_required:
        missing_text = "\n".join(f"  - {path}" for path in missing_required)
        expected_text = "\n".join(f"  - {path}" for path in expected_file_list(shp_path))
        raise FileNotFoundError(
            "SHP 부속 파일이 누락되었습니다.\n"
            f"현재 작업 디렉토리: {Path.cwd()}\n"
            f"누락된 필수 파일:\n{missing_text}\n"
            f"필요한 파일 목록:\n{expected_text}"
        )

    missing_optional = [shp_path.with_suffix(suffix) for suffix in OPTIONAL_SIDECARS if not shp_path.with_suffix(suffix).exists()]
    if missing_optional:
        print("선택 부속 파일이 없습니다. 읽기는 계속 진행합니다:")
        for path in missing_optional:
            print(f"  - {path}")


def read_shapefile(shp_path: Path, encoding: str | None = None) -> tuple[gpd.GeoDataFrame, str]:
    encodings = [encoding] if encoding else ["cp949", "utf-8", "euc-kr", None]
    errors: list[str] = []

    for candidate_encoding in encodings:
        try:
            kwargs: dict[str, str] = {}
            if candidate_encoding:
                kwargs["encoding"] = candidate_encoding
            gdf = gpd.read_file(shp_path, **kwargs)
            return gdf, candidate_encoding or "driver-default"
        except Exception as exc:  # noqa: BLE001 - include all driver errors in final message
            label = candidate_encoding or "driver-default"
            errors.append(f"{label}: {type(exc).__name__}: {exc}")

    raise RuntimeError("SHP 읽기에 실패했습니다.\n" + "\n".join(f"  - {error}" for error in errors))


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return json_safe(value.item())
    if pd.isna(value):
        return None
    return str(value)


def row_attributes(row: pd.Series, geometry_column: str) -> dict[str, Any]:
    return {str(key): json_safe(value) for key, value in row.items() if key != geometry_column}


def print_shp_overview(gdf: gpd.GeoDataFrame, shp_path: Path, encoding: str) -> None:
    print(f"SHP path: {shp_path.resolve()}")
    print(f"Rows: {len(gdf)}")
    print(f"Encoding: {encoding}")
    print(f"CRS: {gdf.crs}")
    print("Columns:")
    for column in gdf.columns:
        print(f"  - {column}")


def transform_target_point(source_crs: CRS, target_lat: float, target_lng: float) -> Point:
    transformer = Transformer.from_crs("EPSG:4326", source_crs, always_xy=True)
    x, y = transformer.transform(target_lng, target_lat)
    return Point(x, y)


def find_attribute_matches(gdf: gpd.GeoDataFrame, keywords: tuple[str, ...]) -> tuple[gpd.GeoDataFrame, dict[Any, list[str]]]:
    geometry_column = gdf.geometry.name
    attribute_columns = [column for column in gdf.columns if column != geometry_column]
    if not attribute_columns:
        return gdf.iloc[0:0].copy(), {}

    total_mask = pd.Series(False, index=gdf.index)
    matched_keywords: dict[Any, list[str]] = {}

    for keyword in keywords:
        keyword_mask = pd.Series(False, index=gdf.index)
        for column in attribute_columns:
            try:
                column_mask = gdf[column].astype("string").str.contains(keyword, regex=False, na=False)
            except Exception:
                continue
            keyword_mask = keyword_mask | column_mask

        for index_value in gdf.index[keyword_mask]:
            matched_keywords.setdefault(index_value, []).append(keyword)
        total_mask = total_mask | keyword_mask

    return gdf.loc[total_mask].copy(), matched_keywords


def print_nearest_candidates(candidates: gpd.GeoDataFrame, target_point: Point, limit: int = 10) -> None:
    working = candidates.copy()
    working["_distance_m"] = working.geometry.distance(target_point)
    working["_area_m2"] = working.geometry.area
    nearest = working.nsmallest(limit, "_distance_m")

    print(f"좌표를 포함하는 Polygon이 없어 가장 가까운 후보 {len(nearest)}개를 출력합니다.")
    geometry_column = working.geometry.name
    for rank, (index_value, row) in enumerate(nearest.iterrows(), start=1):
        attrs = row_attributes(row, geometry_column)
        preview_items = [(key, value) for key, value in attrs.items() if value not in (None, "")]
        preview = ", ".join(f"{key}={value}" for key, value in preview_items[:8])
        print(
            f"[{rank}] index={index_value} "
            f"distance_m={float(row['_distance_m']):.3f} "
            f"area_m2={float(row['_area_m2']):.3f} "
            f"{preview}"
        )


def choose_from_candidates(
    candidates: gpd.GeoDataFrame,
    target_point: Point,
    reason_prefix: str,
) -> tuple[Any, str]:
    if candidates.empty:
        raise ValueError("선택할 후보 Polygon이 없습니다.")

    contains_mask = candidates.geometry.covers(target_point)
    containing = candidates.loc[contains_mask]
    if not containing.empty:
        areas = containing.geometry.area
        selected_index = areas.idxmax()
        return selected_index, f"{reason_prefix}_contains_target_point"

    distances = candidates.geometry.distance(target_point)
    selected_index = distances.idxmin()
    return selected_index, f"{reason_prefix}_nearest_to_target_point"


def select_building_polygon(
    gdf: gpd.GeoDataFrame,
    target_point: Point,
    keywords: tuple[str, ...],
    max_attribute_distance_m: float = DEFAULT_MAX_ATTRIBUTE_DISTANCE_M,
) -> tuple[Any, str, dict[Any, list[str]], list[str]]:
    notes: list[str] = []
    attribute_matches, matched_keywords = find_attribute_matches(gdf, keywords)
    print(f"속성 키워드 검색 결과: {len(attribute_matches)}개 후보")

    if not attribute_matches.empty:
        selected_index, selection_method = choose_from_candidates(attribute_matches, target_point, "attribute_match")
        selected_distance = float(attribute_matches.loc[[selected_index]].geometry.distance(target_point).iloc[0])
        matched_for_selected = matched_keywords.get(selected_index, [])
        has_strong_keyword = any(keyword in STRONG_KEYWORDS for keyword in matched_for_selected)
        selected_contains_target = bool(attribute_matches.loc[[selected_index]].geometry.covers(target_point).iloc[0])

        if selected_contains_target or has_strong_keyword or selected_distance <= max_attribute_distance_m:
            return selected_index, selection_method, matched_keywords, notes

        note = (
            "속성 후보가 기준 좌표에서 너무 멀어 좌표 기반 검색으로 전환했습니다. "
            f"selected_attribute_distance_m={selected_distance:.3f}, "
            f"threshold_m={max_attribute_distance_m:.3f}, "
            f"matched_keywords={matched_for_selected}"
        )
        print(note)
        notes.append(note)

    contains_mask = gdf.geometry.covers(target_point)
    containing = gdf.loc[contains_mask]
    if not containing.empty:
        selected_index, selection_method = choose_from_candidates(containing, target_point, "coordinate_match")
        return selected_index, selection_method, matched_keywords, notes

    print_nearest_candidates(gdf, target_point, limit=10)
    distances = gdf.geometry.distance(target_point)
    selected_index = distances.idxmin()
    return selected_index, "nearest_polygon_fallback", matched_keywords, notes


def metric_geometry(selected_projected: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, str, list[str]]:
    notes: list[str] = []
    source_crs = CRS.from_user_input(selected_projected.crs)
    if not source_crs.is_geographic:
        return selected_projected, str(selected_projected.crs), notes

    estimated_crs = selected_projected.estimate_utm_crs()
    if estimated_crs is None:
        raise ValueError("면적/둘레 계산용 투영 CRS를 추정하지 못했습니다.")
    notes.append(
        "원본 CRS가 위경도 좌표계라 면적/둘레 계산에는 GeoPandas가 추정한 투영 CRS를 사용했습니다."
    )
    return selected_projected.to_crs(estimated_crs), str(estimated_crs), notes


def build_summary(
    selected_projected: gpd.GeoDataFrame,
    selected_index: Any,
    selection_method: str,
    matched_keywords: dict[Any, list[str]],
    shp_path: Path,
    source_crs: CRS,
    encoding: str,
    output_geojson: Path,
    output_summary: Path,
) -> dict[str, Any]:
    metric_gdf, metric_crs, notes = metric_geometry(selected_projected)
    metric_geom = metric_gdf.geometry.iloc[0]
    projected_geom = selected_projected.geometry.iloc[0]

    centroid_projected = projected_geom.centroid
    transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    centroid_lng, centroid_lat = transformer.transform(centroid_projected.x, centroid_projected.y)
    wgs84 = selected_projected.to_crs("EPSG:4326")

    row = selected_projected.iloc[0]
    geometry_column = selected_projected.geometry.name
    matched_for_row = matched_keywords.get(selected_index, [])

    summary = {
        "source_shp": str(shp_path.resolve()),
        "source_crs": str(source_crs),
        "encoding": encoding,
        "selected_index": json_safe(selected_index),
        "selection_method": selection_method,
        "matched_keywords": matched_for_row,
        "centroid_lat": float(centroid_lat),
        "centroid_lng": float(centroid_lng),
        "area_m2": float(metric_geom.area),
        "perimeter_m": float(metric_geom.length),
        "bbox_wgs84": [float(value) for value in wgs84.total_bounds],
        "bbox_projected": [float(value) for value in selected_projected.total_bounds],
        "metric_crs": metric_crs,
        "building_geojson": str(output_geojson.resolve()),
        "building_summary": str(output_summary.resolve()),
        "selected_attributes": row_attributes(row, geometry_column),
        "notes": notes,
    }
    return summary


def extract_thehyundai_building(
    shp_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    target_lat: float = DEFAULT_TARGET_LAT,
    target_lng: float = DEFAULT_TARGET_LNG,
    encoding: str | None = None,
    max_attribute_distance_m: float = DEFAULT_MAX_ATTRIBUTE_DISTANCE_M,
) -> dict[str, Any]:
    cwd = Path.cwd()
    resolved_shp = resolve_shp_path(str(shp_path) if shp_path else None, cwd)
    validate_shapefile_parts(resolved_shp)

    gdf, used_encoding = read_shapefile(resolved_shp, encoding=encoding)
    print_shp_overview(gdf, resolved_shp, used_encoding)

    if gdf.empty:
        raise ValueError("SHP에 feature가 없습니다.")
    if gdf.crs is None:
        raise ValueError(f"SHP CRS를 확인할 수 없습니다. .prj 파일을 확인하세요: {resolved_shp.with_suffix('.prj')}")

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        raise ValueError("유효한 geometry가 있는 feature가 없습니다.")

    source_crs = CRS.from_user_input(gdf.crs)
    target_point = transform_target_point(source_crs, target_lat, target_lng)
    print(f"Target WGS84: lat={target_lat}, lng={target_lng}")
    print(f"Target in SHP CRS: x={target_point.x:.3f}, y={target_point.y:.3f}")

    selected_index, selection_method, matched_keywords, selection_notes = select_building_polygon(
        gdf,
        target_point,
        KEYWORDS,
        max_attribute_distance_m=max_attribute_distance_m,
    )
    selected_projected = gdf.loc[[selected_index]].copy()

    output_base = Path(output_dir)
    output_base.mkdir(parents=True, exist_ok=True)
    output_geojson = output_base / BUILDING_GEOJSON_NAME
    output_summary = output_base / BUILDING_SUMMARY_NAME

    selected_projected.to_crs("EPSG:4326").to_file(output_geojson, driver="GeoJSON")
    summary = build_summary(
        selected_projected=selected_projected,
        selected_index=selected_index,
        selection_method=selection_method,
        matched_keywords=matched_keywords,
        shp_path=resolved_shp,
        source_crs=source_crs,
        encoding=used_encoding,
        output_geojson=output_geojson,
        output_summary=output_summary,
    )
    summary["notes"].extend(selection_notes)
    output_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"선택 방식: {selection_method}")
    print(f"GeoJSON 저장: {output_geojson.resolve()}")
    print(f"Summary 저장: {output_summary.resolve()}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="더현대서울 건물 외곽 Polygon을 VWorld SHP에서 추출합니다.")
    parser.add_argument("--shp", help=f"SHP 경로. 기본값은 {DEFAULT_SHP_FILENAME} 자동 검색")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="결과를 저장할 디렉토리")
    parser.add_argument("--target-lat", type=float, default=DEFAULT_TARGET_LAT, help="더현대서울 기준 위도")
    parser.add_argument("--target-lng", type=float, default=DEFAULT_TARGET_LNG, help="더현대서울 기준 경도")
    parser.add_argument("--encoding", help="DBF 인코딩 강제 지정 예: cp949")
    parser.add_argument(
        "--max-attribute-distance-m",
        type=float,
        default=DEFAULT_MAX_ATTRIBUTE_DISTANCE_M,
        help="일반 속성 키워드 후보를 좌표 기준으로 신뢰할 최대 거리",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        extract_thehyundai_building(
            shp_path=args.shp,
            output_dir=args.output_dir,
            target_lat=args.target_lat,
            target_lng=args.target_lng,
            encoding=args.encoding,
            max_attribute_distance_m=args.max_attribute_distance_m,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should print clear root cause
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
