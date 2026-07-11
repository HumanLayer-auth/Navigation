import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../models/building.dart';
import '../../models/floor_plan.dart';
import '../../routing/app_routes.dart';
import '../../widgets/location_marker.dart';
import '../../widgets/uncertainty_circle.dart';

const _fallbackCenter = LatLng(37.5665, 126.9780);

class IndoorMapScreen extends StatefulWidget {
  const IndoorMapScreen({super.key});

  @override
  State<IndoorMapScreen> createState() => _IndoorMapScreenState();
}

class _IndoorMapScreenState extends State<IndoorMapScreen> {
  bool _loading = true;
  Building? _building;
  String? _selectedFloor;
  FloorPlan? _floorPlan;

  @override
  void initState() {
    super.initState();
    _loadBuilding();
  }

  Future<void> _loadBuilding() async {
    final building = await buildingRepository.getBuilding(demoBuildingId);
    if (!mounted) return;

    if (building == null || building.floors.isEmpty) {
      setState(() {
        _building = building;
        _loading = false;
      });
      return;
    }

    setState(() => _building = building);
    await _loadFloorPlan(building.floors.first);
  }

  Future<void> _loadFloorPlan(String floor) async {
    setState(() => _loading = true);
    final geojson = await buildingRepository.getFloorGeoJson(
      demoBuildingId,
      floor,
    );
    if (!mounted) return;
    setState(() {
      _selectedFloor = floor;
      _floorPlan = geojson == null ? null : FloorPlan.fromJson(geojson);
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final building = _building;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          building == null
              ? '실내 지도 (PDR 모드)'
              : '${building.name} · $_selectedFloor',
        ),
        actions: [
          if (building != null && building.floors.length > 1)
            PopupMenuButton<String>(
              icon: const Icon(Icons.layers),
              tooltip: '층 전환',
              onSelected: (floor) => _loadFloorPlan(floor),
              itemBuilder: (context) => building.floors
                  .map(
                    (floor) => PopupMenuItem(value: floor, child: Text(floor)),
                  )
                  .toList(),
            ),
        ],
      ),
      body: _loading ? const Center(child: CircularProgressIndicator()) : _buildBody(),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: () {
              Navigator.of(context).pushNamed(AppRoutes.destination);
            },
            child: const Text('목적지 검색'),
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_building == null) {
      return const Center(child: Text('건물 정보를 찾을 수 없습니다'));
    }

    final floorPlan = _floorPlan;
    if (floorPlan == null) {
      return const Center(child: Text('평면도를 찾을 수 없습니다'));
    }

    final center = floorPlan.corridors.isNotEmpty &&
            floorPlan.corridors.first.isNotEmpty
        ? floorPlan.corridors.first.first
        : floorPlan.stores.isNotEmpty
            ? floorPlan.stores.first.centroid
            : (floorPlan.pois.isNotEmpty ? floorPlan.pois.first.point : _fallbackCenter);

    return LayoutBuilder(
      builder: (context, constraints) {
        // mock(GeoJSON, 위경도 흉내)과 백엔드 실데이터(건물 로컬 미터)는 좌표 스케일이
        // 완전히 다르다. flutter_map의 LatLngBounds/CameraFit.bounds는 위경도
        // 범위(±90/±180)를 강제해서 미터 단위 좌표(예: y=117)에는 못 쓰기 때문에,
        // 뷰포트 크기에 맞는 줌을 직접 계산해서 평면도 전체가 항상 보이게 한다.
        final fit = _fitToViewport(floorPlan, constraints.biggest);

        return FlutterMap(
          // 백엔드 실데이터는 위경도가 아니라 건물 로컬 좌표(미터)라서,
          // 지리 투영 없는 평면 좌표계(CrsSimple)로 그대로 그린다.
          options: MapOptions(
            crs: const CrsSimple(),
            initialCenter: fit?.center ?? center,
            initialZoom: fit?.zoom ?? 19,
          ),
          children: [
            if (floorPlan.footprint.isNotEmpty)
              PolygonLayer(
                polygons: [
                  Polygon(
                    points: floorPlan.footprint,
                    color: Colors.transparent,
                    borderColor: Colors.black54,
                    borderStrokeWidth: 2,
                  ),
                ],
              ),
            if (floorPlan.stores.isNotEmpty)
              PolygonLayer(
                polygons: [
                  for (final store in floorPlan.stores)
                    Polygon(
                      points: store.polygon,
                      color: Colors.blueGrey.withValues(alpha: 0.15),
                      borderColor: Colors.blueGrey,
                      borderStrokeWidth: 1,
                    ),
                ],
              ),
            PolylineLayer(
              polylines: [
                for (final corridor in floorPlan.corridors)
                  Polyline(points: corridor, color: Colors.grey, strokeWidth: 6),
              ],
            ),
            MarkerLayer(
              markers: [
                for (final store in floorPlan.stores)
                  Marker(
                    point: store.centroid,
                    width: 90,
                    height: 24,
                    child: Text(
                      store.name,
                      style: const TextStyle(fontSize: 9),
                      overflow: TextOverflow.ellipsis,
                      textAlign: TextAlign.center,
                    ),
                  ),
                for (final poi in floorPlan.pois)
                  Marker(
                    point: poi.point,
                    width: 80,
                    height: 40,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(_iconForPoiType(poi.type), size: 16, color: Colors.black54),
                        Text(
                          poi.name,
                          style: const TextStyle(fontSize: 10),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                // 더미 현재 위치 마커. 실제 PDR 위치 갱신은 M3~M4에서 연결한다.
                Marker(
                  point: center,
                  child: const Stack(
                    alignment: Alignment.center,
                    children: [
                      UncertaintyCircle(diameter: 40, color: Color(0xFF6C3FE0)),
                      LocationMarker(mode: LocationMode.indoor),
                    ],
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }

  ({LatLng center, double zoom})? _fitToViewport(FloorPlan floorPlan, Size viewportSize) {
    final points = [
      ...floorPlan.footprint,
      for (final store in floorPlan.stores) ...[store.centroid, ...store.polygon],
      for (final corridor in floorPlan.corridors) ...corridor,
      for (final poi in floorPlan.pois) poi.point,
    ];
    if (points.isEmpty || viewportSize.isEmpty) return null;

    var minX = points.first.longitude;
    var maxX = points.first.longitude;
    var minY = points.first.latitude;
    var maxY = points.first.latitude;
    for (final point in points) {
      minX = math.min(minX, point.longitude);
      maxX = math.max(maxX, point.longitude);
      minY = math.min(minY, point.latitude);
      maxY = math.max(maxY, point.latitude);
    }

    const padding = 32.0;
    final availableWidth = math.max(viewportSize.width - padding * 2, 1.0);
    final availableHeight = math.max(viewportSize.height - padding * 2, 1.0);
    // 평면도 폭/높이가 0에 가까우면(예: mock의 단일 지점) 과도한 줌을 막는다.
    final spanX = math.max(maxX - minX, 1e-6);
    final spanY = math.max(maxY - minY, 1e-6);

    // CrsSimple 스케일 공식(Crs.scale)과 동일: scale(zoom) = 256 * 2^zoom.
    final zoomForWidth = _log2(availableWidth / (256 * spanX));
    final zoomForHeight = _log2(availableHeight / (256 * spanY));

    return (
      center: LatLng((minY + maxY) / 2, (minX + maxX) / 2),
      zoom: math.min(zoomForWidth, zoomForHeight),
    );
  }

  static double _log2(double value) => math.log(value) / math.ln2;

  IconData _iconForPoiType(String? type) {
    switch (type) {
      case 'elevator':
        return Icons.elevator;
      case 'escalator':
        return Icons.escalator;
      case 'toilet':
        return Icons.wc;
      case 'exit':
        return Icons.exit_to_app;
      case 'facility':
        return Icons.info_outline;
      default:
        return Icons.place;
    }
  }
}
