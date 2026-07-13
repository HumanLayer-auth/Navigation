import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../models/poi_search_result.dart';
import '../../theme/app_theme.dart';
import '../../widgets/building_switcher_sheet.dart';
import '../../widgets/directions_sheet.dart';
import '../../widgets/map_bottom_bar.dart';
import '../../widgets/map_top_bar.dart';
import '../indoor_map/indoor_map_screen.dart';
import '../outdoor_map/outdoor_map_screen.dart';

/// 야외/실내 지도의 공통 뼈대. 홈(야외) ↔ 실내 전환은 Navigator push 없이
/// 이 화면 안에서 모드만 바꿔 탭처럼 즉시 반응하게 한다. 검색·길찾기·건물
/// 전환·위치 보정은 전부 이 화면이 상단/하단 공용 바를 통해 중계한다.
class MapShellScreen extends StatefulWidget {
  const MapShellScreen({super.key, this.initialMode = MapMode.outdoor});

  final MapMode initialMode;

  @override
  State<MapShellScreen> createState() => _MapShellScreenState();
}

/// 하단 공용 바(위치 보정 버튼 + 홈/실내 세그먼트)의 대략적인 높이. 지도
/// 본문의 ETA/매장 카드가 그 위에 가려지지 않도록 이 값만큼 띄운다.
const _bottomBarReservedHeight = 150.0;

class _MapShellScreenState extends State<MapShellScreen> {
  late MapMode _mode = widget.initialMode;
  String _buildingId = demoBuildingId;
  ({String title, String subtitle})? _placeInfo;

  final _outdoorKey = GlobalKey<OutdoorMapBodyState>();
  final _indoorKey = GlobalKey<IndoorMapBodyState>();

  @override
  void initState() {
    super.initState();
    _requestStartupPermissions();
  }

  /// 예전에는 스플래시 화면이 이 요청을 진행 중 화면과 함께 보여줬지만,
  /// 이제 앱이 바로 지도 화면으로 시작하므로 화면을 막지 않고 백그라운드로
  /// 요청만 하고, 거부된 게 있으면 지도 위에 짧게 안내만 띄운다.
  Future<void> _requestStartupPermissions() async {
    try {
      final statuses = await requestStartupPermissions();
      final anyDenied = statuses.values.any((status) => !status.isGranted);
      if (!mounted || !anyDenied) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('일부 권한이 거부되어 위치·실내 이동 관련 기능이 제한될 수 있습니다'),
        ),
      );
    } catch (_) {
      // 권한 플러그인을 쓸 수 없는 환경(테스트 등)에서도 앱을 계속 진행한다.
    }
  }

  void _setMode(MapMode mode) {
    if (mode == _mode) return;
    setState(() {
      _mode = mode;
      _placeInfo = null;
    });
  }

  Future<void> _onSearch(String query) async {
    final normalized = query.trim();
    if (normalized.isEmpty) {
      setState(() => _placeInfo = null);
      return;
    }

    if (_mode == MapMode.outdoor) {
      final buildings = await buildingRepository.getAllBuildings();
      final match = buildings
          .where((b) => b.name.toLowerCase().contains(normalized.toLowerCase()))
          .firstOrNull;
      if (!mounted) return;
      setState(() {
        _placeInfo = match == null
            ? null
            : (title: match.name, subtitle: '${match.floors.length}개 층');
      });
    } else {
      final results = await destinationRepository.searchDestinations(_buildingId, normalized);
      if (!mounted) return;
      final match = results.firstOrNull;
      setState(() {
        _placeInfo = match == null ? null : (title: match.name, subtitle: match.floor);
      });
    }

    if (!mounted) return;
    if (_placeInfo == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('검색 결과가 없습니다')),
      );
    }
  }

  Future<List<DirectionsCandidate>> _searchDirectionsCandidates(String query) async {
    final normalized = query.trim().toLowerCase();
    if (_mode == MapMode.outdoor) {
      final buildings = await buildingRepository.getAllBuildings();
      return buildings
          .where((b) => b.entrance != null)
          .where((b) => normalized.isEmpty || b.name.toLowerCase().contains(normalized))
          .map(
            (b) => DirectionsCandidate(
              title: b.name,
              subtitle: '${b.floors.length}개 층',
              point: b.entrance!,
            ),
          )
          .toList();
    }
    final results = await destinationRepository.searchDestinations(_buildingId, query);
    return results
        .map(
          (r) => DirectionsCandidate(
            title: r.name,
            subtitle: r.floor,
            point: r.point,
            nodeId: r.nodeId,
            floor: r.floor,
          ),
        )
        .toList();
  }

  Future<void> _onDirectionsTap() async {
    final candidate = await DirectionsSheet.show(
      context,
      originLabel: '현재 위치',
      search: _searchDirectionsCandidates,
    );
    if (candidate == null || !mounted) return;

    if (_mode == MapMode.outdoor) {
      await _outdoorKey.currentState?.showRouteTo(candidate.point, label: candidate.title);
    } else {
      await _indoorKey.currentState?.showRouteTo(
        PoiSearchResult(
          name: candidate.title,
          floor: candidate.floor ?? '',
          point: candidate.point,
          nodeId: candidate.nodeId,
        ),
      );
    }
  }

  Future<void> _onHamburgerTap() async {
    final selected = await BuildingSwitcherSheet.show(context, selectedBuildingId: _buildingId);
    if (selected == null || selected == _buildingId || !mounted) return;
    setState(() {
      _buildingId = selected;
      _placeInfo = null;
    });
  }

  void _onCalibrate() {
    if (_mode == MapMode.outdoor) {
      _outdoorKey.currentState?.recalibrate();
    } else {
      _indoorKey.currentState?.recalibrate();
    }
  }

  void _onEnterBuilding() => _setMode(MapMode.indoor);

  @override
  Widget build(BuildContext context) {
    final placeInfo = _placeInfo;
    return Scaffold(
      body: Stack(
        children: [
          IndexedStack(
            index: _mode == MapMode.outdoor ? 0 : 1,
            children: [
              OutdoorMapBody(
                key: _outdoorKey,
                onEnterBuilding: _onEnterBuilding,
                bottomOverlayHeight: _bottomBarReservedHeight,
              ),
              IndoorMapBody(
                key: _indoorKey,
                buildingId: _buildingId,
                bottomOverlayHeight: _bottomBarReservedHeight,
              ),
            ],
          ),

          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: MapTopBar(
              showHamburger: _mode == MapMode.indoor,
              onHamburgerTap: _onHamburgerTap,
              onSearch: _onSearch,
              onDirectionsTap: _onDirectionsTap,
            ),
          ),

          if (placeInfo != null)
            Positioned(
              top: 84,
              left: 12,
              right: 12,
              child: _PlaceInfoCard(
                title: placeInfo.title,
                subtitle: placeInfo.subtitle,
                onClose: () => setState(() => _placeInfo = null),
              ),
            ),

          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: MapBottomBar(
              mode: _mode,
              onModeChanged: _setMode,
              onCalibrate: _onCalibrate,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlaceInfoCard extends StatelessWidget {
  const _PlaceInfoCard({required this.title, required this.subtitle, required this.onClose});

  final String title;
  final String subtitle;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 12),
        child: Row(
          children: [
            const Icon(Icons.info_outline, color: AppColors.primary, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 12, color: AppColors.muted),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            IconButton(
              onPressed: onClose,
              icon: const Icon(Icons.close, size: 18, color: AppColors.muted),
            ),
          ],
        ),
      ),
    );
  }
}
