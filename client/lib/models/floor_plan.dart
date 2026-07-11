import 'package:latlong2/latlong.dart';

class PoiMarker {
  const PoiMarker({required this.name, required this.point, this.type});

  final String name;
  final LatLng point;

  /// 백엔드 실데이터에서만 채워짐(예: elevator/escalator/restroom). mock GeoJSON엔 없음.
  final String? type;
}

class StorePolygon {
  const StorePolygon({
    required this.name,
    required this.polygon,
    required this.centroid,
  });

  final String name;
  final List<LatLng> polygon;
  final LatLng centroid;
}

/// 층 평면도. 두 가지 소스를 모두 파싱한다:
/// - mock: api/app/data/sample_building.json과 동일한 GeoJSON FeatureCollection
/// - 백엔드: api/app/router/buildingRouter.py의 /floors/{floor} 응답
///   (footprint_local_m/stores/pois, 건물 로컬 좌표계 - 미터 단위, 위경도 아님)
///
/// 로컬 좌표는 flutter_map의 CrsSimple(비지리 평면 좌표계)에서
/// LatLng(y, x)로 그대로 사용한다 - 실제 위경도로 투영하지 않는다.
class FloorPlan {
  const FloorPlan({
    this.footprint = const [],
    this.corridors = const [],
    this.stores = const [],
    required this.pois,
  });

  final List<LatLng> footprint;
  final List<List<LatLng>> corridors;
  final List<StorePolygon> stores;
  final List<PoiMarker> pois;

  factory FloorPlan.fromJson(Map<String, dynamic> json) {
    if (json.containsKey('footprint_local_m')) {
      return _fromApiResponse(json);
    }
    return _fromGeoJson(json);
  }

  static FloorPlan _fromApiResponse(Map<String, dynamic> json) {
    final footprint = ((json['footprint_local_m'] as List<dynamic>?) ??
            const [])
        .map((point) => _toLocalLatLng(point as Map<String, dynamic>))
        .toList();

    final stores = ((json['stores'] as List<dynamic>?) ?? const [])
        .cast<Map<String, dynamic>>()
        .map(
          (store) => StorePolygon(
            name: store['name'] as String? ?? '',
            polygon: ((store['polygon_local_m'] as List<dynamic>?) ?? const [])
                .map((point) => _toLocalLatLng(point as Map<String, dynamic>))
                .toList(),
            centroid: _toLocalLatLng(
              store['centroid_local_m'] as Map<String, dynamic>,
            ),
          ),
        )
        .toList();

    final pois = ((json['pois'] as List<dynamic>?) ?? const [])
        .cast<Map<String, dynamic>>()
        .map(
          (poi) => PoiMarker(
            name: poi['name'] as String? ?? '',
            point: _toLocalLatLng(
              poi['position_local_m'] as Map<String, dynamic>,
            ),
            type: poi['type'] as String?,
          ),
        )
        .toList();

    return FloorPlan(footprint: footprint, stores: stores, pois: pois);
  }

  static LatLng _toLocalLatLng(Map<String, dynamic> point) {
    return LatLng((point['y'] as num).toDouble(), (point['x'] as num).toDouble());
  }

  static FloorPlan _fromGeoJson(Map<String, dynamic> geojson) {
    final corridors = <List<LatLng>>[];
    final pois = <PoiMarker>[];

    final features = (geojson['features'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();

    for (final feature in features) {
      final properties =
          (feature['properties'] as Map<String, dynamic>?) ?? const {};
      final geometry = feature['geometry'] as Map<String, dynamic>?;
      if (geometry == null) continue;

      if (properties['type'] == 'corridor') {
        final coordinates = (geometry['coordinates'] as List<dynamic>? ??
                const [])
            .map((c) => _toGeoJsonLatLng(c as List<dynamic>))
            .toList();
        corridors.add(coordinates);
      } else if (properties['type'] == 'poi') {
        final coordinate = geometry['coordinates'] as List<dynamic>;
        pois.add(
          PoiMarker(
            name: properties['name'] as String? ?? '',
            point: _toGeoJsonLatLng(coordinate),
          ),
        );
      }
    }

    return FloorPlan(corridors: corridors, pois: pois);
  }

  static LatLng _toGeoJsonLatLng(List<dynamic> coordinate) {
    // GeoJSON 좌표 순서는 [longitude, latitude]다.
    return LatLng(
      (coordinate[1] as num).toDouble(),
      (coordinate[0] as num).toDouble(),
    );
  }
}
