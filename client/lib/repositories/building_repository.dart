import '../models/building.dart';
import '../models/building_graph.dart';
import '../models/indoor_route.dart';

abstract class BuildingRepository {
  Future<List<Building>> getAllBuildings();

  Future<Building?> getBuilding(String buildingId);

  Future<Map<String, dynamic>?> getFloorGeoJson(String buildingId, String floor);

  /// 두 노드 사이 최단 경로. 경로가 없거나 층/노드를 찾을 수 없으면 null.
  Future<IndoorRoute?> getShortestRoute(
    String buildingId,
    String floor,
    String startNodeId,
    String endNodeId,
  );

  /// 건물 전체 길찾기 그래프(전 층 노드 + 층 내부 간선 + 수직 전이 간선).
  /// 층 간 경로 계산의 입력이며, 건물이 없으면 null.
  Future<BuildingGraph?> getBuildingGraph(
    String buildingId, {
    String vertical = 'auto',
  });
}
