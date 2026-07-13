import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../models/building.dart';
import '../../models/directions_route.dart';
import '../../theme/app_theme.dart';
import '../../widgets/eta_card.dart';
import '../../widgets/location_marker.dart';
import '../../widgets/route_polyline.dart';
import '../../widgets/status_badge.dart';

// 위치 조회 실패 시 대체 좌표 (서울시청).
const _fallbackLocation = LatLng(37.5665, 126.9780);
const _lowAccuracyThresholdMeters = 30.0;

/// 배경지도 타일 공급자. 플랫폼 채널·네트워크가 없는 위젯 테스트 환경에서는
/// 이 변수를 실제 OSM/VWorld에 요청하지 않는 가짜 TileProvider로 교체한다
/// (안 그러면 진짜 HTTP 요청이 백그라운드에 남아 이후 테스트의 pumpAndSettle과
/// 뒤섞여 타임아웃을 일으킨다).
TileProvider Function() outdoorTileProvider = NetworkTileProvider.new;

// 건물 진입 판정: "입구 근처" + "신호가 방금 나빠짐"을 같이 봐서
// 건물 앞을 그냥 지나가는 경우(신호는 안 나빠짐)와 구분한다.
// 세 값 다 실측 검증 전이라 추정치이고, 실기기 테스트하며 조정이 필요하다.
const _buildingEntryThresholdMeters = 20.0;
const _degradedAccuracyFloorMeters = 15.0;
const _accuracyWorsenedRatio = 1.3;

/// 야외 지도 본문(지도 + 위치/경로 오버레이). 검색창·길찾기·건물 전환 같은
/// 공통 UI는 [MapShellScreen]이 상단/하단 바로 얹으므로 여기서는 다루지 않는다.
class OutdoorMapBody extends StatefulWidget {
  const OutdoorMapBody({
    super.key,
    required this.onEnterBuilding,
    this.bottomOverlayHeight = 140,
  });

  /// GPS로 건물 입구 진입이 감지됐을 때 호출된다. 상위(MapShellScreen)가
  /// 이 콜백으로 하단 바 모드를 "실내"로 전환한다.
  final VoidCallback onEnterBuilding;

  /// 하단 공용 바(위치 보정 버튼 + 홈/실내 세그먼트)가 차지하는 높이만큼,
  /// ETA 카드가 그 위에 가려지지 않도록 띄운다.
  final double bottomOverlayHeight;

  @override
  State<OutdoorMapBody> createState() => OutdoorMapBodyState();
}

class OutdoorMapBodyState extends State<OutdoorMapBody> {
  bool _loading = true;
  bool _autoNavigated = false;
  Position? _position;
  LatLng? _entrance;
  DirectionsRoute? _route;
  double? _previousAccuracy;
  StreamSubscription<Position>? _positionSubscription;
  final MapController _mapController = MapController();

  /// 길찾기 시트에서 사용자가 직접 고른 목적지. null이면 건물 입구까지의
  /// 경로를 대신 보여준다(기존 "자동 안내" 동작).
  LatLng? _userDestination;
  String? _userDestinationLabel;

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
    final isNear = distance <= _buildingEntryThresholdMeters;

    final previousAccuracy = _previousAccuracy;
    _previousAccuracy = position.accuracy;
    final accuracyWorsened =
        position.accuracy > _degradedAccuracyFloorMeters &&
        (previousAccuracy == null ||
            position.accuracy > previousAccuracy * _accuracyWorsenedRatio);

    if (!isNear || !accuracyWorsened) return;

    _autoNavigated = true;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('건물 감지 중...')));
    widget.onEnterBuilding();
  }

  Future<void> _updateRoute(Position position) async {
    final target = _userDestination ?? _entrance;
    if (target == null) return;

    final route = await directionsRepository.getWalkingRoute(
      origin: LatLng(position.latitude, position.longitude),
      destination: target,
    );
    if (!mounted) return;
    setState(() => _route = route);
  }

  /// 위치 보정 버튼: 즉시 새 GPS 위치를 한 번 더 조회해 마커·지도 중심을 갱신한다.
  Future<void> recalibrate() async {
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.best),
      );
      _handlePosition(position);
      _mapController.move(
        LatLng(position.latitude, position.longitude),
        _mapController.camera.zoom,
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('위치를 다시 확인하지 못했습니다')),
      );
    }
  }

  /// 길찾기 시트에서 도착지를 고르면 호출된다. 현재 위치에서 [destination]까지의
  /// 보행 경로를 계산해 지도 위에 표시한다.
  Future<void> showRouteTo(LatLng destination, {required String label}) async {
    setState(() {
      _userDestination = destination;
      _userDestinationLabel = label;
    });
    final position = _position;
    if (position == null) return;
    await _updateRoute(position);
  }

  void _clearUserDestination() {
    setState(() {
      _userDestination = null;
      _userDestinationLabel = null;
      _route = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return _loading ? const Center(child: CircularProgressIndicator()) : _buildBody();
  }

  Widget _buildBody() {
    final position = _position;
    final center = position == null
        ? _fallbackLocation
        : LatLng(position.latitude, position.longitude);
    final accuracy = position?.accuracy ?? 0;
    final lowAccuracy = position == null || accuracy > _lowAccuracyThresholdMeters;
    final markerColor = lowAccuracy ? AppColors.warning : AppColors.primary;
    final entrance = _entrance;
    final userDestination = _userDestination;
    final route = _route;

    return Stack(
      children: [
        FlutterMap(
          mapController: _mapController,
          options: MapOptions(initialCenter: center, initialZoom: 17),
          children: [
            TileLayer(
              // VWorld는 키 발급(도메인 등록) 전제. 키가 없으면 OSM으로 대체해
              // 로컬 개발·테스트 환경에서도 지도가 항상 뜨도록 한다.
              urlTemplate: vworldApiKey.isEmpty
                  ? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                  : 'https://api.vworld.kr/req/wmts/1.0.0/$vworldApiKey/Base/{z}/{y}/{x}.png',
              userAgentPackageName: 'com.navigation.navigation_client',
              tileProvider: outdoorTileProvider(),
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
                if (userDestination != null)
                  Marker(
                    point: userDestination,
                    child: const Icon(Icons.place, color: AppColors.dest),
                  )
                else if (entrance != null)
                  Marker(
                    point: entrance,
                    child: const Icon(Icons.place, color: AppColors.dest),
                  ),
              ],
            ),
          ],
        ),

        if (lowAccuracy)
          Positioned(
            top: 76,
            left: 12,
            child: StatusBadge(
              label: 'GPS 신호 약함',
              color: AppColors.warning,
              icon: Icons.warning_amber_rounded,
            ),
          ),

        if (route != null)
          Positioned(
            left: 12,
            right: 12,
            bottom: widget.bottomOverlayHeight,
            child: EtaCard(
              distanceMeters: route.distanceMeters,
              minutes: (route.durationSeconds / 60).ceil().clamp(1, 999),
              label: userDestination != null
                  ? (_userDestinationLabel ?? '목적지까지')
                  : '건물 입구까지',
              onClose: userDestination != null ? _clearUserDestination : null,
            ),
          ),
      ],
    );
  }
}
