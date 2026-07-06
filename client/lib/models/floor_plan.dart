import 'package:latlong2/latlong.dart';

class PoiMarker {
  const PoiMarker({required this.name, required this.point});

  final String name;
  final LatLng point;
}

/// api/app/schemas/building.py의 Floor.geojson(FeatureCollection)을 파싱한 결과.
/// 벽/문/경로 그래프는 M2-001에서 스키마가 정해지면 함께 확장한다.
class FloorPlan {
  const FloorPlan({required this.corridors, required this.pois});

  final List<List<LatLng>> corridors;
  final List<PoiMarker> pois;

  factory FloorPlan.fromGeoJson(Map<String, dynamic> geojson) {
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
            .map((c) => _toLatLng(c as List<dynamic>))
            .toList();
        corridors.add(coordinates);
      } else if (properties['type'] == 'poi') {
        final coordinate = geometry['coordinates'] as List<dynamic>;
        pois.add(
          PoiMarker(
            name: properties['name'] as String? ?? '',
            point: _toLatLng(coordinate),
          ),
        );
      }
    }

    return FloorPlan(corridors: corridors, pois: pois);
  }

  static LatLng _toLatLng(List<dynamic> coordinate) {
    // GeoJSON 좌표 순서는 [longitude, latitude]다.
    return LatLng(
      (coordinate[1] as num).toDouble(),
      (coordinate[0] as num).toDouble(),
    );
  }
}
