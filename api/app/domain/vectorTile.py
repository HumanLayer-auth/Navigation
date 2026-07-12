"""건물의 local_m 지오메트리를 MVT 타일용 WGS84 GeoJSON 레이어로 변환한다.

MVT 바이트 인코딩(mapbox_vector_tile) 자체는 외부 포맷 라이브러리 의존이라
Service 쪽에서 호출한다. 이 모듈은 순수하게 (1) 슬리피맵 z/x/y -> WGS84 경계
상자 계산, (2) local_m -> wgs84 좌표 변환, (3) 타일과 겹치는 feature만 골라
GeoJSON 레이어를 만드는 역할만 한다. FastAPI, SQLite, mapbox_vector_tile을
알지 못한다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.building import Building, Poi, Store
from app.domain.georeference import GeoTransform


@dataclass(frozen=True)
class TileBounds:
    """슬리피맵 타일 하나가 덮는 WGS84 경계 상자."""

    west: float
    south: float
    east: float
    north: float

    def intersects(self, other_west: float, other_south: float, other_east: float, other_north: float) -> bool:
        """이 경계 상자가 다른 경계 상자와 겹치는지(경계 포함) 확인한다."""
        return (
            self.west <= other_east
            and other_west <= self.east
            and self.south <= other_north
            and other_south <= self.north
        )


def tile_bounds(z: int, x: int, y: int) -> TileBounds:
    """표준 슬리피맵(z/x/y, Web Mercator) 타일 좌표를 WGS84 경계 상자로 바꾼다."""
    if z < 0 or not (0 <= x < 2**z) or not (0 <= y < 2**z):
        raise ValueError(f"타일 좌표 범위를 벗어났습니다: z={z}, x={x}, y={y}")

    tiles_per_axis = 2.0**z
    west = x / tiles_per_axis * 360.0 - 180.0
    east = (x + 1) / tiles_per_axis * 360.0 - 180.0
    # 타일 y는 위쪽(북쪽)이 작은 값이라 north가 y, south가 y+1에 대응한다.
    north = _tile_edge_latitude(y, tiles_per_axis)
    south = _tile_edge_latitude(y + 1, tiles_per_axis)
    return TileBounds(west=west, south=south, east=east, north=north)


def _tile_edge_latitude(y: int, tiles_per_axis: float) -> float:
    """Web Mercator 타일 y좌표 한쪽 변의 위도(도)."""
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / tiles_per_axis)))
    return math.degrees(lat_rad)


def _polygon_bbox(ring: list[list[float]]) -> tuple[float, float, float, float]:
    lngs = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lngs), min(lats), max(lngs), max(lats)


def local_points_to_lnglat(points: list[dict], transform: GeoTransform) -> list[list[float]]:
    """local_m 점 목록을 [lng, lat] 목록으로 옮긴다(폴리곤을 닫지는 않음).

    MVT 타일 빌더뿐 아니라 일반 JSON 응답(층 지도, 경로)에서도 재사용한다.
    """
    return [list(reversed(transform.apply(p["x"], p["y"]))) for p in points]


def _close_ring(ring: list[list[float]]) -> list[list[float]]:
    if ring and ring[0] != ring[-1]:
        return [*ring, ring[0]]
    return ring


def _local_polygon_ring(points: list[dict], transform: GeoTransform) -> list[list[float]]:
    return _close_ring(local_points_to_lnglat(points, transform))


def _wgs84_dicts_to_ring(points: list[dict]) -> list[list[float]]:
    """이미 wgs84로 계산돼 저장된 {"lat":..,"lng":..} 목록을 [lng, lat] 폴리곤 링으로 만든다.

    georeference_svg_floor_map.py가 SVG 도면에서 미리 계산해둔 외곽선/매장
    폴리곤(footprint_wgs84_svg, store.svg_polygon_wgs84)에 쓴다 — 건물
    전체 similarity 변환보다 정확하므로 있으면 이걸 우선 쓴다.
    """
    return _close_ring([[point["lng"], point["lat"]] for point in points])


def store_centroid_offset(store: Store, transform: GeoTransform) -> tuple[float, float] | None:
    """매장의 실측 centroid wgs84와 변환식 예측치의 차이(offset_lng, offset_lat).

    건물 전체에 적용하는 similarity 변환은 건물 단위(수백m)로 피팅된 것이라
    지점마다 수십m 오차가 남는다. 매장 centroid는 원본 데이터에 이미 계산된
    실측값이 따로 있으므로, "변환이 이 매장 centroid를 예측한 위치"와
    "실제 알려진 위치"의 차이를 구해서 매장 폴리곤 전체를 보정하는 데 쓴다.
    매장 폭은 수 미터 수준이라 이 안에서 회전/스케일 오차는 무시할 만큼
    작고, 평행이동만으로도 centroid 오차를 사실상 0으로 없앨 수 있다.
    실측값이 없으면 None(보정 없음).
    """
    if store.centroid_lat is None or store.centroid_lng is None:
        return None
    predicted_lat, predicted_lng = transform.apply(store.centroid.x_m, store.centroid.y_m)
    return (store.centroid_lng - predicted_lng, store.centroid_lat - predicted_lat)


def snap_points(points: list[list[float]], offset: tuple[float, float] | None) -> list[list[float]]:
    """[lng, lat] 목록에 (offset_lng, offset_lat)을 더한다. offset이 None이면 그대로 반환."""
    if offset is None:
        return points
    offset_lng, offset_lat = offset
    return [[lng + offset_lng, lat + offset_lat] for lng, lat in points]


def _snap_to_known_centroid(
    ring: list[list[float]],
    store: Store,
    transform: GeoTransform,
) -> list[list[float]]:
    return snap_points(ring, store_centroid_offset(store, transform))


def build_floor_tile_layers(
    building: Building,
    stores: list[Store],
    pois: list[Poi],
    bounds: TileBounds,
) -> list[dict]:
    """건물 하나의 layers(footprint/stores/pois)를 wgs84 GeoJSON feature로 만든다.

    이 타일 경계 상자와 겹치지 않는 feature는 걸러낸다(정밀 클리핑은 하지
    않고 bbox 교차만 확인 — 실내 지도는 feature 수가 적어 이 정도로도
    타일이 과도하게 커지지 않는다).

    building.geo_transform이 없으면(실좌표 앵커가 없는 건물, 예: test-center)
    빈 리스트를 반환한다 — 호출자가 이를 "이 건물은 타일을 못 만든다"는
    신호로 쓴다.
    """
    transform = building.geo_transform
    if transform is None:
        return []

    layers: list[dict] = []

    # SVG 도면에서 미리 계산해둔 외곽선이 있으면 그걸 우선 쓴다 — 건물 전체
    # similarity 변환보다 정확하고, 사람이 정리한 도형이라 모양도 깔끔하다.
    footprint_ring = (
        _wgs84_dicts_to_ring(building.footprint_wgs84_svg)
        if building.footprint_wgs84_svg
        else _local_polygon_ring(building.footprint_local_m, transform)
    )
    if footprint_ring and bounds.intersects(*_polygon_bbox(footprint_ring)):
        layers.append(
            {
                "name": "footprint",
                "features": [
                    {
                        "geometry": {"type": "Polygon", "coordinates": [footprint_ring]},
                        "properties": {"kind": "footprint", "building_id": building.id},
                    }
                ],
            }
        )

    store_features = []
    for store in stores:
        if store.svg_polygon_wgs84:
            # SVG에서 이름이 매칭된 매장: 깔끔한 도형 + 실측 centroid로 이미 앵커링됨.
            ring = _wgs84_dicts_to_ring(store.svg_polygon_wgs84)
        elif store.polygon_local_m:
            # SVG에 대응 도형이 없는 매장: CV 추출 폴리곤을 건물 변환으로 근사.
            ring = _local_polygon_ring(store.polygon_local_m, transform)
            ring = _snap_to_known_centroid(ring, store, transform)
        else:
            continue
        if not ring or not bounds.intersects(*_polygon_bbox(ring)):
            continue
        store_features.append(
            {
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {"id": store.id, "name": store.name, "kind": "store"},
            }
        )
    layers.append({"name": "stores", "features": store_features})

    poi_features = []
    for poi in pois:
        lat, lng = transform.apply(poi.position.x_m, poi.position.y_m)
        if not bounds.intersects(lng, lat, lng, lat):
            continue
        poi_features.append(
            {
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {"id": poi.id, "name": poi.name, "type": poi.type},
            }
        )
    layers.append({"name": "pois", "features": poi_features})

    return layers
