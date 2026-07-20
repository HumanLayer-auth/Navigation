import 'package:flutter/material.dart';

import '../core/service_locator.dart';
import '../models/floor_plan.dart';
import '../theme/app_theme.dart';
import 'sheet_header.dart';

/// 검색창 아래 "카테고리" pill을 누르면 뜨는 시트. 현재 건물에 존재하는
/// 대분류를 매장 수와 함께 보여주고, 항목 탭하면 해당 카테고리 이름으로
/// pop해서 호출자가 [CategoryStoresSheet]로 넘겨준다.
///
/// 카테고리 목록은 건물 전 층을 순회해 `stores[].category`를 unique하게
/// 뽑아 만든다 — 데이터가 늘어나거나 줄어도 별도 유지 없이 자동 반영된다.
/// HttpBuildingRepository가 층별 응답을 캐시하므로 두 번째 호출부턴 즉시.
class CategoryListSheet extends StatefulWidget {
  const CategoryListSheet({
    super.key,
    required this.buildingId,
    required this.onCloseAll,
  });

  final String buildingId;

  /// X 버튼이 눌리면 호출. 부모(MapShellScreen)가 chain-close 플래그를 세팅
  /// 해 위쪽 시트들도 다시 열리지 않게 한다.
  final VoidCallback onCloseAll;

  static Future<String?> show(
    BuildContext context, {
    required String buildingId,
    required VoidCallback onCloseAll,
  }) {
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      isDismissible: true,
      backgroundColor: Colors.transparent,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => CategoryListSheet(
        buildingId: buildingId,
        onCloseAll: onCloseAll,
      ),
    );
  }

  @override
  State<CategoryListSheet> createState() => _CategoryListSheetState();
}

class _CategoryListSheetState extends State<CategoryListSheet> {
  late final Future<List<_CategoryEntry>> _entriesFuture = _load();

  /// back/X/항목 선택으로 명시적 pop될 때 true. PopScope가 이 값이 false인
  /// pop(=barrier/drag)을 잡아 chain 전체를 닫는다.
  bool _intentionalPop = false;
  void _markIntentional() => _intentionalPop = true;

  Future<List<_CategoryEntry>> _load() async {
    final building = await buildingRepository.getBuilding(widget.buildingId);
    if (building == null) return const [];
    final counts = <String, int>{};
    for (final floor in building.floors) {
      final json = await buildingRepository.getFloorGeoJson(
        widget.buildingId,
        floor,
      );
      if (json == null) continue;
      final plan = FloorPlan.fromJson(json);
      for (final store in plan.stores) {
        final c = store.category;
        if (c == null || c.isEmpty) continue;
        counts[c] = (counts[c] ?? 0) + 1;
      }
    }
    final entries = counts.entries
        .map((e) => _CategoryEntry(name: e.key, storeCount: e.value))
        .toList();
    // 매장 수 많은 순, 동수면 이름 순.
    entries.sort((a, b) {
      final c = b.storeCount.compareTo(a.storeCount);
      return c != 0 ? c : a.name.compareTo(b.name);
    });
    return entries;
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop && !_intentionalPop) widget.onCloseAll();
      },
      child: GestureDetector(
        onTap: () => Navigator.of(context).maybePop(),
        behavior: HitTestBehavior.opaque,
        child: DraggableScrollableSheet(
          initialChildSize: 0.55,
          minChildSize: 0.35,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return GestureDetector(
              onTap: () {},
              behavior: HitTestBehavior.opaque,
              child: Material(
                color: Colors.white,
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                ),
                clipBehavior: Clip.antiAlias,
                child: FutureBuilder<List<_CategoryEntry>>(
                  future: _entriesFuture,
                  builder: (context, snapshot) {
                    return CustomScrollView(
                      controller: scrollController,
                      slivers: [
                        SliverToBoxAdapter(
                          child: SheetHeader(
                            title: '카테고리',
                            leading: Container(
                              width: 32,
                              height: 32,
                              decoration: BoxDecoration(
                                color: const Color(0xFFEEF3FF),
                                borderRadius: BorderRadius.circular(9),
                              ),
                              alignment: Alignment.center,
                              child: const Icon(
                                Icons.category_outlined,
                                size: 16,
                                color: AppColors.primary,
                              ),
                            ),
                            onCloseAll: widget.onCloseAll,
                            onIntentionalPop: _markIntentional,
                          ),
                        ),
                        ..._buildBody(snapshot),
                      ],
                    );
                  },
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  List<Widget> _buildBody(AsyncSnapshot<List<_CategoryEntry>> snapshot) {
    if (snapshot.connectionState != ConnectionState.done) {
      return const [
        SliverFillRemaining(
          hasScrollBody: false,
          child: Padding(
            padding: EdgeInsets.symmetric(vertical: 40),
            child: Center(child: CircularProgressIndicator()),
          ),
        ),
      ];
    }
    if (snapshot.hasError) {
      return const [
        SliverToBoxAdapter(
          child: Padding(
            padding: EdgeInsets.fromLTRB(20, 8, 20, 24),
            child: Text('카테고리를 불러오지 못했습니다. 서버 연결을 확인해주세요.'),
          ),
        ),
      ];
    }
    final entries = snapshot.data ?? const [];
    if (entries.isEmpty) {
      return const [
        SliverToBoxAdapter(
          child: Padding(
            padding: EdgeInsets.fromLTRB(20, 8, 20, 24),
            child: Text('표시할 카테고리가 없습니다.'),
          ),
        ),
      ];
    }
    return [
      SliverList.separated(
        itemCount: entries.length,
        separatorBuilder: (_, _) => const Divider(height: 1, indent: 20, endIndent: 20),
        itemBuilder: (context, index) {
          final entry = entries[index];
          return ListTile(
            onTap: () {
              _markIntentional();
              Navigator.of(context).pop(entry.name);
            },
            leading: const Icon(Icons.storefront, size: 20, color: AppColors.primary),
            title: Text(
              entry.name,
              style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.w700),
            ),
            subtitle: Text(
              '매장 ${entry.storeCount}개',
              style: const TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            trailing: const Icon(Icons.chevron_right, size: 18, color: AppColors.muted),
          );
        },
      ),
      const SliverToBoxAdapter(child: SizedBox(height: 12)),
    ];
  }
}

class _CategoryEntry {
  const _CategoryEntry({required this.name, required this.storeCount});

  final String name;
  final int storeCount;
}
