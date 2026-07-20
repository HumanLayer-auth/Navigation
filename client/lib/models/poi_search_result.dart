import 'package:latlong2/latlong.dart';

class PoiSearchResult {
  const PoiSearchResult({
    required this.name,
    required this.floor,
    required this.point,
    this.nodeId,
    this.category,
    this.subcategory,
  });

  final String name;
  final String floor;
  final LatLng point;

  /// 경로탐색 시작/도착점으로 쓸 그래프 노드 ID. 매장의 entranceNodeId에서 온다.
  /// 없으면(예: 일부 POI) 실제 경로탐색은 불가능하다.
  final String? nodeId;

  /// 매장 대분류(예: 패션·뷰티·서비스). 매장 폴리곤 탭 흐름에서만 채워지고,
  /// 텍스트 검색/저장한 장소에서 온 경우엔 null일 수 있다.
  final String? category;

  /// 매장 소분류(예: 여성패션·남성패션). category와 함께만 의미 있음.
  final String? subcategory;
}
