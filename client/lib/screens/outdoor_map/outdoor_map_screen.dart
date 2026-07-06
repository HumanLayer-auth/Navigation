import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../models/building.dart';
import '../../models/directions_route.dart';
import '../../routing/app_routes.dart';
import '../../widgets/eta_card.dart';
import '../../widgets/location_marker.dart';
import '../../widgets/route_polyline.dart';
import '../../widgets/status_badge.dart';

// 위치 조회 실패 시 대체 좌표 (서울시청).
const _fallbackLocation = LatLng(37.5665, 126.9780);
const _lowAccuracyThresholdMeters = 30.0;

// 건물 입구 반경 이 안으로 들어오면 실내 진입으로 간주해 자동 전환한다.
const _buildingEntryThresholdMeters = 50.0;

class OutdoorMapScreen extends StatefulWidget {
  const OutdoorMapScreen({super.key});

  @override
  State<OutdoorMapScreen> createState() => _OutdoorMapScreenState();
}

class _OutdoorMapScreenState extends State<OutdoorMapScreen> {
  bool _loading = true;
  bool _autoNavigated = false;
  Position? _position;
  LatLng? _entrance;
  DirectionsRoute? _route;
  StreamSubscription<Position>? _positionSubscription;

  @override
  void initState() {
    super.initState();
    _loadBuildingEntrance();
    _positionSubscription = watchPosition().listen(
      _handlePosition,
      onError: (Object _) => _handlePositionError(),
    );
  }

  @override
  void dispose() {
    _positionSubscription?.cancel();
    super.dispose();
  }

  Future<void> _loadBuildingEntrance() async {
    final Building? building = await buildingRepository.getBuilding(
      demoBuildingId,
    );
    if (!mounted) return;
    setState(() => _entrance = building?.entrance);
  }

  void _handlePositionError() {
    if (!mounted) return;
    setState(() {
      _position = null;
      _loading = false;
    });
  }

  void _handlePosition(Position position) {
    if (!mounted) return;
    setState(() {
      _position = position;
      _loading = false;
    });
    _maybeAutoEnter(position);
    _updateRoute(position);
  }

  void _maybeAutoEnter(Position position) {
    final entrance = _entrance;
    if (_autoNavigated || entrance == null) return;

    final distance = const Distance().as(
      LengthUnit.Meter,
      LatLng(position.latitude, position.longitude),
      entrance,
    );
    if (distance > _buildingEntryThresholdMeters) return;

    _autoNavigated = true;
    _positionSubscription?.cancel();
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('건물 감지 중...')));
    Navigator.of(context).pushNamed(AppRoutes.indoorMap);
  }

  Future<void> _updateRoute(Position position) async {
    final entrance = _entrance;
    if (entrance == null) return;

    final route = await directionsRepository.getWalkingRoute(
      origin: LatLng(position.latitude, position.longitude),
      destination: entrance,
    );
    if (!mounted) return;
    setState(() => _route = route);
  }

  @override
  Widget build(BuildContext context) {
    final entrance = _entrance;
    return Scaffold(
      appBar: AppBar(title: const Text('야외 지도 (GPS 모드)')),
      body: _loading ? const Center(child: CircularProgressIndicator()) : _buildBody(),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (_route != null)
                EtaCard(
                  distanceMeters: _route!.distanceMeters,
                  minutes: (_route!.durationSeconds / 60).ceil().clamp(1, 999),
                ),
              if (_route != null) const SizedBox(height: 8),
              // 건물 입구 좌표를 모를 때만 수동 진입 버튼을 남겨둔다.
              // 좌표를 아는 경우엔 design.md 원칙대로 자동 감지만으로 전환한다.
              if (!_loading && entrance == null)
                FilledButton(
                  onPressed: () {
                    Navigator.of(context).pushNamed(AppRoutes.indoorMap);
                  },
                  child: const Text('건물 진입 감지 (임시)'),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    final position = _position;
    final center = position == null
        ? _fallbackLocation
        : LatLng(position.latitude, position.longitude);
    final accuracy = position?.accuracy ?? 0;
    final lowAccuracy = position == null || accuracy > _lowAccuracyThresholdMeters;
    final markerColor = lowAccuracy ? Colors.amber : Colors.blue;
    final entrance = _entrance;
    final route = _route;

    return Stack(
      children: [
        FlutterMap(
          options: MapOptions(initialCenter: center, initialZoom: 17),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.navigation.navigation_client',
            ),
            CircleLayer(
              circles: [
                CircleMarker(
                  point: center,
                  radius: accuracy > 0 ? accuracy : 20,
                  useRadiusInMeter: true,
                  color: markerColor.withValues(alpha: 0.2),
                  borderColor: markerColor,
                  borderStrokeWidth: 1,
                ),
              ],
            ),
            if (route != null)
              PolylineLayer(polylines: [buildRoutePolyline(route.points)]),
            MarkerLayer(
              markers: [
                Marker(
                  point: center,
                  child: LocationMarker(
                    mode: LocationMode.outdoor,
                    colorOverride: markerColor,
                  ),
                ),
                if (entrance != null)
                  Marker(
                    point: entrance,
                    child: const Icon(Icons.place, color: Colors.red),
                  ),
              ],
            ),
          ],
        ),
        if (lowAccuracy)
          const Positioned(
            top: 12,
            left: 12,
            child: StatusBadge(label: 'GPS 신호 약함'),
          ),
      ],
    );
  }
}
