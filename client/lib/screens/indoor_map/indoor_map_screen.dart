import 'package:flutter/material.dart';
import 'package:latlong2/latlong.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../core/theme/app_theme.dart';
import '../../models/building.dart';
import '../../models/floor_plan.dart';
import '../../models/poi_search_result.dart';
import '../../routing/app_routes.dart';
import '../../widgets/floor_plan_view.dart';

const _walkingSpeedMetersPerSecond = 1.2;

/// 지도 홈 (design.md 8.1): 상단 검색창 + 가로 층 선택기 + 실내 지도 +
/// 선택 장소 하단 패널.
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
  StorePolygon? _selectedStore;
  bool _bookmarked = false;

  /// 값이 바뀌면 FloorPlanView가 새로 만들어져 초기 fit(전체 보기)으로 돌아간다.
  int _mapResetKey = 0;

  @override
  void initState() {
    super.initState();
    _loadBuilding();
  }

  Future<void> _loadBuilding() async {
    final building = await buildingRepository.getBuilding(demoBuildingId);
    if (!mounted) return;

    final selectedFloor =
        building != null && building.floors.isNotEmpty ? building.floors.first : null;
    setState(() {
      _building = building;
      _selectedFloor = selectedFloor;
      _loading = false;
    });
    if (selectedFloor != null) await _loadFloorPlan(selectedFloor);
  }

  /// 목적지 검색·경로 안내 화면(route_guide_screen.dart)과 동일하게
  /// buildingRepository를 통해 층 지도를 받아온다 — 데이터 소스를 하나로
  /// 맞춰야 실내 지도에서 본 것과 경로 안내 화면의 지도가 어긋나지 않는다.
  Future<void> _loadFloorPlan(String floor) async {
    final geojson = await buildingRepository.getFloorGeoJson(demoBuildingId, floor);
    if (!mounted || geojson == null) return;
    setState(() => _floorPlan = FloorPlan.fromJson(geojson));
  }

  void _selectFloor(String floor) {
    if (floor == _selectedFloor) return;
    setState(() {
      _selectedFloor = floor;
      _floorPlan = null;
      _selectedStore = null;
      _bookmarked = false;
    });
    _loadFloorPlan(floor);
  }

  void _selectStore(StorePolygon store) {
    setState(() {
      _selectedStore = store;
      _bookmarked = false;
    });
  }

  void _startRoute(StorePolygon store) {
    final floor = _selectedFloor;
    if (floor == null) return;
    Navigator.of(context).pushNamed(
      AppRoutes.routeGuide,
      arguments: PoiSearchResult(
        name: store.name,
        floor: floor,
        point: store.centroid,
        nodeId: store.entranceNodeId,
        category: store.category,
      ),
    );
  }

  /// 경로 안내 화면과 같은 규칙의 임시 "현재 위치" (PDR 연동 전까지):
  /// 평면도 중심 또는 첫 복도 시작점.
  LatLng? _approximateCurrentPoint() {
    final floorPlan = _floorPlan;
    if (floorPlan == null) return null;
    if (floorPlan.footprint.isNotEmpty) {
      final avgLat =
          floorPlan.footprint.map((p) => p.latitude).reduce((a, b) => a + b) /
              floorPlan.footprint.length;
      final avgLng =
          floorPlan.footprint.map((p) => p.longitude).reduce((a, b) => a + b) /
              floorPlan.footprint.length;
      return LatLng(avgLat, avgLng);
    }
    if (floorPlan.corridors.isNotEmpty && floorPlan.corridors.first.isNotEmpty) {
      return floorPlan.corridors.first.first;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final building = _building;
    final selectedStore = _selectedStore;

    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(child: _buildMapArea()),
          SafeArea(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.screen,
                    AppSpacing.sm,
                    AppSpacing.screen,
                    0,
                  ),
                  child: _SearchBarButton(
                    onTap: () {
                      Navigator.of(context).pushNamed(AppRoutes.destination);
                    },
                  ),
                ),
                if (building != null && building.floors.isNotEmpty)
                  _FloorTabs(
                    floors: building.floors,
                    selected: _selectedFloor,
                    onSelect: _selectFloor,
                  ),
              ],
            ),
          ),
          // 지도 제어 버튼 (design.md 8.1) — 전체 보기 복귀.
          Align(
            alignment: Alignment.centerRight,
            child: Padding(
              padding: const EdgeInsets.only(right: AppSpacing.screen),
              child: MapIconButton(
                icon: Icons.my_location,
                tooltip: '전체 보기',
                onPressed: () => setState(() => _mapResetKey++),
              ),
            ),
          ),
          if (selectedStore != null)
            Align(
              alignment: Alignment.bottomCenter,
              child: _DestinationPreviewPanel(
                store: selectedStore,
                floor: _selectedFloor ?? '',
                currentPoint: _approximateCurrentPoint(),
                bookmarked: _bookmarked,
                onToggleBookmark: () =>
                    setState(() => _bookmarked = !_bookmarked),
                onStartRoute: () => _startRoute(selectedStore),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMapArea() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_building == null) {
      return const Center(
        child: Text('건물 정보를 찾을 수 없습니다', style: AppTextStyles.body),
      );
    }
    final floorPlan = _floorPlan;
    if (floorPlan == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return FloorPlanView(
      key: ValueKey(_mapResetKey),
      floorPlan: floorPlan,
      onStoreSelected: _selectStore,
    );
  }
}

/// design.md 9.1 Search Bar. 지도 홈에서는 입력 대신 검색 화면으로 이동하는
/// 버튼 역할만 한다.
class _SearchBarButton extends StatelessWidget {
  const _SearchBarButton({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        boxShadow: appShadow,
      ),
      child: Material(
        color: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.medium),
          side: const BorderSide(color: AppColors.border),
        ),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(AppRadius.medium),
          child: SizedBox(
            height: 52,
            child: Row(
              children: [
                const SizedBox(width: AppSpacing.md),
                const Icon(Icons.search, size: 22, color: AppColors.iconDefault),
                const SizedBox(width: AppSpacing.sm),
                Text(
                  '어디로 갈까요?',
                  style: AppTextStyles.body.copyWith(
                    color: AppColors.textTertiary,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// design.md 9.2 Floor Selector(지도 홈): 가로 탭 + 활성 층 밑줄.
class _FloorTabs extends StatelessWidget {
  const _FloorTabs({
    required this.floors,
    required this.selected,
    required this.onSelect,
  });

  final List<String> floors;
  final String? selected;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
      child: Row(
        children: [
          for (final floor in floors)
            InkWell(
              onTap: () => onSelect(floor),
              borderRadius: BorderRadius.circular(AppRadius.small),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: AppSpacing.sm,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      floor,
                      style: floor == selected
                          ? AppTextStyles.bodyStrong.copyWith(
                              color: AppColors.primary,
                            )
                          : AppTextStyles.body.copyWith(
                              color: AppColors.textSecondary,
                            ),
                    ),
                    const SizedBox(height: 3),
                    Container(
                      width: 24,
                      height: 2.5,
                      decoration: BoxDecoration(
                        color: floor == selected
                            ? AppColors.primary
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// 목적지 미리보기 하단 패널 (design.md 8.3).
class _DestinationPreviewPanel extends StatelessWidget {
  const _DestinationPreviewPanel({
    required this.store,
    required this.floor,
    required this.currentPoint,
    required this.bookmarked,
    required this.onToggleBookmark,
    required this.onStartRoute,
  });

  final StorePolygon store;
  final String floor;
  final LatLng? currentPoint;
  final bool bookmarked;
  final VoidCallback onToggleBookmark;
  final VoidCallback onStartRoute;

  @override
  Widget build(BuildContext context) {
    final current = currentPoint;
    final distance =
        current == null ? null : localDistanceMeters(current, store.centroid);
    final minutes = distance == null
        ? null
        : (distance / _walkingSpeedMetersPerSecond / 60).ceil().clamp(1, 999);

    return SafeArea(
      top: false,
      child: Container(
        margin: const EdgeInsets.fromLTRB(
          AppSpacing.sm,
          0,
          AppSpacing.sm,
          AppSpacing.sm,
        ),
        padding: const EdgeInsets.all(AppSpacing.screen),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.large),
          boxShadow: appShadow,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.location_on,
                  size: 22,
                  color: AppColors.destination,
                ),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: Text(
                    '${store.name} $floor',
                    style: AppTextStyles.title,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  onPressed: onToggleBookmark,
                  icon: Icon(
                    bookmarked ? Icons.bookmark : Icons.bookmark_border,
                    color: bookmarked
                        ? AppColors.primary
                        : AppColors.iconDefault,
                  ),
                  tooltip: '즐겨찾기',
                ),
              ],
            ),
            if (distance != null && minutes != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Row(
                children: [
                  Expanded(
                    child: _MetricColumn(value: '$minutes분', label: '예상 시간'),
                  ),
                  Container(width: 1, height: 36, color: AppColors.divider),
                  Expanded(
                    child: _MetricColumn(
                      value: '${distance.round()}m',
                      label: '거리',
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: onStartRoute,
                child: const Text('경로 시작'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricColumn extends StatelessWidget {
  const _MetricColumn({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w700,
            color: AppColors.textPrimary,
            height: 32 / 24,
          ),
        ),
        const SizedBox(height: 2),
        Text(label, style: AppTextStyles.caption),
      ],
    );
  }
}
