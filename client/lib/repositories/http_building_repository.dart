import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/api_config.dart';
import '../models/building.dart';
import 'building_repository.dart';

/// api/app/routers/buildings.py의 /buildings 엔드포인트를 그대로 호출한다.
class HttpBuildingRepository implements BuildingRepository {
  HttpBuildingRepository({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  @override
  Future<List<Building>> getAllBuildings() async {
    final response = await _client.get(Uri.parse('$apiBaseUrl/buildings'));
    final list = jsonDecode(response.body) as List<dynamic>;
    return list
        .map((item) => Building.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<Building?> getBuilding(String buildingId) async {
    final response = await _client.get(
      Uri.parse('$apiBaseUrl/buildings/$buildingId'),
    );
    if (response.statusCode == 404) return null;
    return Building.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  @override
  Future<Map<String, dynamic>?> getFloorGeoJson(
    String buildingId,
    int floor,
  ) async {
    final response = await _client.get(
      Uri.parse('$apiBaseUrl/buildings/$buildingId/floors/$floor'),
    );
    if (response.statusCode == 404) return null;
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
