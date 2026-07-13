import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../core/theme/app_theme.dart';
import '../../models/floor_plan.dart';
import '../../models/indoor_route.dart';
import '../../models/poi_search_result.dart';
import '../../routing/app_routes.dart';
import '../../widgets/floor_plan_view.dart';
import '../../widgets/location_marker.dart';
import '../../widgets/rag_chat_panel.dart';
import '../../widgets/uncertainty_circle.dart';

const _fallbackCenter = LatLng(37.5665, 126.9780);
const _walkingSpeedMetersPerSecond = 1.2;

/// 경로 위 첫 방향 전환 지점 판정 각도(도). 이보다 완만하면 직진으로 본다.
const _turnThresholdDegrees = 30.0;

/// 다음 행동 안내 (design.md 8.4 상단 안내).
class _Instruction {
  const _Instruction({
    required this.icon,
    required this.distanceMeters,
    required this.headline,
    required this.detail,
  });

  final IconData icon;
  final double distanceMeters;

  /// "앞에서 오른쪽으로 이동" 같은 본문. 거리 숫자는 따로 크게 그린다.
  final String headline;
  final String detail;
}

/// 실시간 길안내 (design.md 8.4): 상단 방향 안내 + 지도 + 하단 요약/제어.
class RouteGuideScreen extends StatefulWidget {
  const RouteGuideScreen({super.key});

  @override
  State<RouteGuideScreen> createState() => _RouteGuideScreenState();
}

class _RouteGuideScreenState extends State<RouteGuideScreen> {
  bool _initialized = false;
  bool _loading = true;
  bool _voiceOn = false;
  PoiSearchResult? _destination;
  FloorPlan? _floorPlan;
  IndoorRoute? _route;
  int _mapResetKey = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_initialized) return;
    _initialized = true;
    _destination =
        ModalRoute.of(context)?.settings.arguments as PoiSearchResult?;
    _loadFloorPlan();
  }

  Future<void> _loadFloorPlan() async {
    final destination = _destination;
    if (destination == null) {
      setState(() => _loading = false);
      return;
    }

    final geojson = await buildingRepository.getFloorGeoJson(
      demoBuildingId,
      destination.floor,
    );
    if (!mounted) return;
    final floorPlan = geojson == null ? null : FloorPlan.fromJson(geojson);
    setState(() {
      _floorPlan = floorPlan;
      _loading = false;
    });
    if (floorPlan != null) {
      await _loadRoute(floorPlan, destination);
    }
  }

  /// 실제 최단 경로를 조회한다. 시작/도착 노드 ID를 못 구하면(PDR 미연동,
  /// 목적지에 entranceNodeId 없음 등) route는 null로 남고 화면은 직선 fallback을 쓴다.
  Future<void> _loadRoute(
    FloorPlan floorPlan,
    PoiSearchResult destination,
  ) async {
    final endNodeId = destination.nodeId;
    final startNodeId = _pickStartNodeId(floorPlan, excludingNodeId: endNodeId);
    if (endNodeId == null || startNodeId == null) return;

    final route = await buildingRepository.getShortestRoute(
      demoBuildingId,
      destination.floor,
      startNodeId,
      endNodeId,
    );
    if (!mounted) return;
    setState(() => _route = route);
  }

  /// PDR이 아직 없어 "현재 위치"를 알 수 없다. 임시로 층 평면도 중심에서
  /// 가장 가까운 매장 입구 노드를 출발점으로 쓴다. 실제 PDR 위치 연동은
  /// M3~M4에서 이 자리를 대체한다.
  String? _pickStartNodeId(FloorPlan floorPlan, {String? excludingNodeId}) {
    final origin = _footprintCenter(floorPlan) ?? _currentLocation();
    StorePolygon? nearest;
    double? nearestDistance;
    for (final store in floorPlan.stores) {
      final nodeId = store.entranceNodeId;
      if (nodeId == null || nodeId == excludingNodeId) continue;
      final distance = localDistanceMeters(origin, store.centroid);
      if (nearestDistance == null || distance < nearestDistance) {
        nearestDistance = distance;
        nearest = store;
      }
    }
    return nearest?.entranceNodeId;
  }

  LatLng? _footprintCenter(FloorPlan floorPlan) {
    if (floorPlan.footprint.isEmpty) return null;
    final avgLat =
        floorPlan.footprint.map((p) => p.latitude).reduce((a, b) => a + b) /
        floorPlan.footprint.length;
    final avgLng =
        floorPlan.footprint.map((p) => p.longitude).reduce((a, b) => a + b) /
        floorPlan.footprint.length;
    return LatLng(avgLat, avgLng);
  }

  void _openBuildingInfo() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => const RagChatPanel(),
    );
  }

  LatLng _currentLocation() {
    final floorPlan = _floorPlan;
    if (floorPlan == null) return _fallbackCenter;
    if (floorPlan.corridors.isNotEmpty &&
        floorPlan.corridors.first.isNotEmpty) {
      return floorPlan.corridors.first.first;
    }
    if (floorPlan.pois.isNotEmpty) return floorPlan.pois.first.point;
    return _fallbackCenter;
  }

  List<LatLng> _activeRoutePoints(PoiSearchResult destination) {
    final route = _route;
    if (route != null && route.points.length >= 2) return route.points;
    return [_currentLocation(), destination.point];
  }

  double _totalDistance(PoiSearchResult destination) {
    final points = _activeRoutePoints(destination);
    var total = 0.0;
    for (var i = 1; i < points.length; i++) {
      total += localDistanceMeters(points[i - 1], points[i]);
    }
    return total;
  }

  /// 경로 폴리라인에서 첫 번째 방향 전환을 찾아 안내 문구로 바꾼다.
  /// 전환점이 없으면(직선 경로·fallback) 목적지까지 직진 안내를 만든다.
  _Instruction _buildInstruction(PoiSearchResult destination) {
    final points = _activeRoutePoints(destination);

    var traveled = 0.0;
    for (var i = 1; i < points.length - 1; i++) {
      traveled += localDistanceMeters(points[i - 1], points[i]);

      final inbound = _headingDegrees(points[i - 1], points[i]);
      final outbound = _headingDegrees(points[i], points[i + 1]);
      var delta = outbound - inbound;
      while (delta > 180) {
        delta -= 360;
      }
      while (delta < -180) {
        delta += 360;
      }
      if (delta.abs() < _turnThresholdDegrees) continue;

      final right = delta > 0;
      return _Instruction(
        icon: right ? Icons.turn_right : Icons.turn_left,
        distanceMeters: traveled,
        headline: right ? '앞에서\n오른쪽으로 이동' : '앞에서\n왼쪽으로 이동',
        detail: '${destination.name} 방향',
      );
    }

    return _Instruction(
      icon: Icons.straight,
      distanceMeters: _totalDistance(destination),
      headline: '직진하면\n목적지예요',
      detail: '${destination.name} 방향',
    );
  }

  /// 화면 좌표(local_m 비율 유지) 기준 진행 방위각. 시계 방향(+)이 오른쪽 회전.
  double _headingDegrees(LatLng from, LatLng to) {
    final dx = to.longitude - from.longitude;
    final dy = to.latitude - from.latitude;
    return math.atan2(dx, dy) * 180 / math.pi;
  }

  String _formatArrivalTime(int minutes) {
    final arrival = DateTime.now().add(Duration(minutes: minutes));
    final period = arrival.hour < 12 ? '오전' : '오후';
    var hour = arrival.hour % 12;
    if (hour == 0) hour = 12;
    final minute = arrival.minute.toString().padLeft(2, '0');
    return '$period $hour:$minute 도착 예정';
  }

  @override
  Widget build(BuildContext context) {
    final destination = _destination;

    return Scaffold(
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : destination == null
          ? const Center(child: Text('목적지 정보가 없습니다', style: AppTextStyles.body))
          : _buildGuide(destination),
    );
  }

  Widget _buildGuide(PoiSearchResult destination) {
    final instruction = _buildInstruction(destination);

    return Stack(
      children: [
        Positioned.fill(child: _buildMap(destination)),
        SafeArea(
          bottom: false,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.screen,
                  AppSpacing.sm,
                  AppSpacing.screen,
                  0,
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: _InstructionCard(instruction: instruction)),
                    const SizedBox(width: AppSpacing.sm),
                    MapIconButton(
                      icon: Icons.close,
                      tooltip: '경로 종료',
                      onPressed: () => Navigator.of(context).maybePop(),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              // 층 선택기(세로 compact) + 지도 제어 (design.md 9.2).
              Align(
                alignment: Alignment.centerRight,
                child: Padding(
                  padding: const EdgeInsets.only(right: AppSpacing.screen),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      _FloorBadge(floor: destination.floor),
                      const SizedBox(height: AppSpacing.xs),
                      MapIconButton(
                        icon: Icons.my_location,
                        tooltip: '전체 보기',
                        onPressed: () => setState(() => _mapResetKey++),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              _buildSummaryPanel(destination),
            ],
          ),
        ),
      ],
    );
  }

  /// 하단 요약 + 제어 버튼 (design.md 8.4).
  Widget _buildSummaryPanel(PoiSearchResult destination) {
    final distance = _totalDistance(destination);
    final minutes = (distance / _walkingSpeedMetersPerSecond / 60).ceil().clamp(
      1,
      999,
    );
    const numberStyle = TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.w700,
      color: AppColors.textPrimary,
      height: 36 / 28,
    );

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.screen,
        AppSpacing.md,
        AppSpacing.screen,
        AppSpacing.sm,
      ),
      decoration: const BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(AppRadius.sheet),
        ),
        boxShadow: appShadow,
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_formatArrivalTime(minutes), style: AppTextStyles.caption),
            const SizedBox(height: 2),
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Text('$minutes분', style: numberStyle),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                  child: Text(
                    '·',
                    style: TextStyle(
                      fontSize: 22,
                      color: AppColors.textTertiary,
                    ),
                  ),
                ),
                Text('${distance.round()}m', style: numberStyle),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: _ControlButton(
                    icon: _voiceOn ? Icons.volume_up : Icons.volume_off,
                    label: '음성 안내',
                    selected: _voiceOn,
                    onTap: () => setState(() => _voiceOn = !_voiceOn),
                  ),
                ),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: _ControlButton(
                    icon: Icons.share_outlined,
                    label: '경로 공유',
                    onTap: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('경로 공유는 준비 중이에요')),
                      );
                    },
                  ),
                ),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: _ControlButton(
                    icon: Icons.info_outline,
                    label: '상세 정보',
                    onTap: _openBuildingInfo,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () {
                  Navigator.of(
                    context,
                  ).pushNamed(AppRoutes.arrival, arguments: _destination);
                },
                child: const Text('도착'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMap(PoiSearchResult destination) {
    final floorPlan = _floorPlan;
    if (floorPlan == null) {
      return const Center(
        child: Text('평면도를 찾을 수 없습니다', style: AppTextStyles.body),
      );
    }

    final route = _route;
    // 실제 경로가 있으면 그 시작점을, 없으면(fallback) 임시 현재 위치를 마커에 쓴다 —
    // 그려지는 선의 출발점과 마커 위치가 항상 일치하도록.
    final current = (route != null && route.points.isNotEmpty)
        ? route.points.first
        : _currentLocation();

    return FloorPlanView(
      key: ValueKey(_mapResetKey),
      floorPlan: floorPlan,
      routePoints: route?.points ?? [current, destination.point],
      extraMarkers: [
        // 현재 위치 (design.md 7.6): 마커 + 반투명 정확도 반경.
        Marker(
          point: current,
          width: 64,
          height: 64,
          child: const Stack(
            alignment: Alignment.center,
            children: [
              UncertaintyCircle(diameter: 64, color: AppColors.primary),
              LocationMarker(mode: LocationMode.indoor),
            ],
          ),
        ),
        // 목적지 (design.md 7.7): Coral pin. 핀 꼭짓점이 목적지 좌표에 오도록
        // 위쪽 정렬로 그린다.
        Marker(
          point: destination.point,
          width: 34,
          height: 34,
          alignment: Alignment.topCenter,
          child: const Icon(
            Icons.location_on,
            color: AppColors.destination,
            size: 34,
            shadows: [Shadow(color: Color(0x33000000), blurRadius: 4)],
          ),
        ),
      ],
    );
  }
}

/// 상단 방향 안내 카드: 큰 화살표 + `18m 앞에서 / 오른쪽으로 이동`.
class _InstructionCard extends StatelessWidget {
  const _InstructionCard({required this.instruction});

  final _Instruction instruction;

  @override
  Widget build(BuildContext context) {
    final headlineLines = instruction.headline.split('\n');

    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.large),
        boxShadow: appShadow,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: AppColors.primarySoft,
              borderRadius: BorderRadius.circular(AppRadius.medium),
            ),
            child: Icon(instruction.icon, size: 34, color: AppColors.primary),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: '${instruction.distanceMeters.round()}m',
                        style: const TextStyle(
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primary,
                          height: 32 / 26,
                        ),
                      ),
                      TextSpan(
                        text: ' ${headlineLines.first}',
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w700,
                          color: AppColors.textPrimary,
                          height: 28 / 20,
                        ),
                      ),
                    ],
                  ),
                ),
                if (headlineLines.length > 1)
                  Text(
                    headlineLines[1],
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                      height: 28 / 20,
                    ),
                  ),
                const SizedBox(height: 2),
                Text(instruction.detail, style: AppTextStyles.caption),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// 길안내 화면용 세로 compact 층 표시 (design.md 9.2).
class _FloorBadge extends StatelessWidget {
  const _FloorBadge({required this.floor});

  final String floor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.medium),
        border: Border.all(color: AppColors.border),
        boxShadow: appShadow,
      ),
      child: Center(
        child: Text(
          floor,
          style: AppTextStyles.bodyStrong.copyWith(color: AppColors.primary),
        ),
      ),
    );
  }
}

/// 하단 제어 버튼 (음성 안내/경로 공유/상세 정보).
class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.label,
    required this.onTap,
    this.selected = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.primary : AppColors.iconDefault;
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        side: BorderSide(
          color: selected ? AppColors.primary : AppColors.border,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.medium),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 22, color: color),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                label,
                style: AppTextStyles.label.copyWith(
                  color: selected ? AppColors.primary : AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
