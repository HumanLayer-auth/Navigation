import 'package:latlong2/latlong.dart';

import 'poi_search_result.dart';

/// 사용자가 "장소" 탭에 저장해둔 매장 한 개.
///
/// PoiSearchResult를 그대로 저장하지 않고 별도 모델로 두는 이유는 (1) 어느
/// 건물에서 저장했는지도 함께 기억해야 하고, (2) SharedPreferences로 앱
/// 재실행 뒤에도 살아남게 JSON 직렬화가 필요하기 때문이다.
class FavoritePlace {
  const FavoritePlace({
    required this.buildingId,
    required this.name,
    required this.floor,
    required this.lat,
    required this.lng,
    this.nodeId,
  });

  final String buildingId;
  final String name;
  final String floor;
  final double lat;
  final double lng;

  /// 매장 입구 노드 ID. 있으면 이걸로 그래프 상에서 유일하게 식별하고,
  /// 없으면(POI만 있고 노드가 없는 경우) 건물+층+이름 조합으로 식별한다.
  final String? nodeId;

  /// 같은 매장을 두 번 저장하지 않기 위한 키. 노드 ID가 있으면 그걸로,
  /// 없으면 건물/층/이름 조합으로 대체한다.
  String get key => nodeId != null
      ? '$buildingId::node::$nodeId'
      : '$buildingId::$floor::$name';

  PoiSearchResult toPoiSearchResult() => PoiSearchResult(
    name: name,
    floor: floor,
    point: LatLng(lat, lng),
    nodeId: nodeId,
  );

  factory FavoritePlace.fromPoiSearchResult(
    PoiSearchResult poi, {
    required String buildingId,
  }) => FavoritePlace(
    buildingId: buildingId,
    name: poi.name,
    floor: poi.floor,
    lat: poi.point.latitude,
    lng: poi.point.longitude,
    nodeId: poi.nodeId,
  );

  Map<String, dynamic> toJson() => {
    'buildingId': buildingId,
    'name': name,
    'floor': floor,
    'lat': lat,
    'lng': lng,
    if (nodeId != null) 'nodeId': nodeId,
  };

  factory FavoritePlace.fromJson(Map<String, dynamic> json) => FavoritePlace(
    buildingId: json['buildingId'] as String,
    name: json['name'] as String,
    floor: json['floor'] as String,
    lat: (json['lat'] as num).toDouble(),
    lng: (json['lng'] as num).toDouble(),
    nodeId: json['nodeId'] as String?,
  );
}
