import 'package:flutter/material.dart';

import '../../core/api_config.dart';
import '../../core/service_locator.dart';
import '../../core/theme/app_theme.dart';
import '../../models/poi_search_result.dart';
import '../../routing/app_routes.dart';

/// 카테고리 필터 (design.md 8.2). 카테고리는 검색 결과의 category(매장 대분류
/// 또는 POI 타입)로 판별한다.
enum _CategoryFilter {
  all('전체'),
  store('매장'),
  toilet('화장실'),
  elevator('엘리베이터'),
  escalator('에스컬레이터');

  const _CategoryFilter(this.label);

  final String label;

  bool matches(PoiSearchResult result) {
    switch (this) {
      case _CategoryFilter.all:
        return true;
      case _CategoryFilter.store:
        // 매장은 mock에선 'store', 백엔드 실데이터에선 대분류(fashion 등)로 온다.
        return result.nodeId != null ||
            result.category == 'store' ||
            result.category == 'fashion' ||
            result.category == 'beauty' ||
            result.category == 'service';
      case _CategoryFilter.toilet:
        return result.category == 'toilet' || result.category == 'restroom';
      case _CategoryFilter.elevator:
        return result.category == 'elevator';
      case _CategoryFilter.escalator:
        return result.category == 'escalator';
    }
  }
}

/// 검색 화면 (design.md 8.2): 검색 입력창 + 카테고리 필터 + 결과/최근 검색.
class DestinationScreen extends StatefulWidget {
  const DestinationScreen({super.key});

  @override
  State<DestinationScreen> createState() => _DestinationScreenState();
}

class _DestinationScreenState extends State<DestinationScreen> {
  /// 최근 검색 (design.md 8.2). 앱 세션 동안만 유지한다.
  static final List<String> _recentSearches = [];

  final TextEditingController _controller = TextEditingController();
  bool _loading = true;
  String _query = '';
  _CategoryFilter _filter = _CategoryFilter.all;
  List<PoiSearchResult> _results = [];

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String query) async {
    setState(() {
      _query = query;
      _loading = true;
    });
    final results = await destinationRepository.searchDestinations(
      demoBuildingId,
      query,
    );
    if (!mounted) return;
    setState(() {
      _results = results;
      _loading = false;
    });
  }

  void _applyRecentSearch(String query) {
    _controller.text = query;
    _controller.selection = TextSelection.collapsed(offset: query.length);
    _search(query);
  }

  void _selectDestination(PoiSearchResult destination) {
    _recentSearches
      ..remove(destination.name)
      ..insert(0, destination.name);
    if (_recentSearches.length > 5) _recentSearches.removeLast();

    Navigator.of(context).pushNamed(
      AppRoutes.routeGuide,
      arguments: destination,
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _results.where(_filter.matches).toList();

    return Scaffold(
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.xs,
                AppSpacing.xs,
                AppSpacing.screen,
                0,
              ),
              child: Row(
                children: [
                  IconButton(
                    onPressed: () => Navigator.of(context).maybePop(),
                    icon: const Icon(Icons.arrow_back),
                    color: AppColors.textPrimary,
                    tooltip: '뒤로',
                  ),
                  Expanded(child: _buildSearchField()),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            _buildCategoryChips(),
            const SizedBox(height: AppSpacing.xxs),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _buildResultList(filtered),
            ),
          ],
        ),
      ),
    );
  }

  /// design.md 9.1 Search Bar.
  Widget _buildSearchField() {
    return Container(
      height: 52,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(AppRadius.medium),
        boxShadow: appShadow,
      ),
      child: TextField(
        controller: _controller,
        autofocus: true,
        onChanged: _search,
        style: AppTextStyles.body,
        cursorColor: AppColors.primary,
        decoration: InputDecoration(
          hintText: '어디로 갈까요?',
          hintStyle: AppTextStyles.body.copyWith(color: AppColors.textTertiary),
          prefixIcon:
              const Icon(Icons.search, size: 22, color: AppColors.iconDefault),
          suffixIcon: _query.isEmpty
              ? null
              : IconButton(
                  icon: const Icon(
                    Icons.close,
                    size: 20,
                    color: AppColors.iconDefault,
                  ),
                  tooltip: '지우기',
                  onPressed: () {
                    _controller.clear();
                    _search('');
                  },
                ),
          filled: true,
          fillColor: AppColors.surface,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.medium),
            borderSide: const BorderSide(color: AppColors.border),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadius.medium),
            borderSide: const BorderSide(color: AppColors.primary),
          ),
        ),
      ),
    );
  }

  /// design.md 9.6 Category Chip: 34px, 선택 시 Deep Teal border + text.
  Widget _buildCategoryChips() {
    return SizedBox(
      height: 34,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screen),
        itemCount: _CategoryFilter.values.length,
        separatorBuilder: (_, _) => const SizedBox(width: AppSpacing.xs),
        itemBuilder: (context, index) {
          final filter = _CategoryFilter.values[index];
          final selected = filter == _filter;
          return Material(
            color: selected ? AppColors.surface : Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.large),
              side: BorderSide(
                color: selected ? AppColors.primary : AppColors.border,
              ),
            ),
            child: InkWell(
              onTap: () => setState(() => _filter = filter),
              borderRadius: BorderRadius.circular(AppRadius.large),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Center(
                  child: Text(
                    filter.label,
                    style: AppTextStyles.label.copyWith(
                      color: selected
                          ? AppColors.primary
                          : AppColors.textSecondary,
                      fontWeight:
                          selected ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildResultList(List<PoiSearchResult> results) {
    if (results.isEmpty) {
      return Center(
        child: Text(
          '찾을 수 없어요. 다시 입력해볼까요?',
          style: AppTextStyles.body.copyWith(color: AppColors.textSecondary),
        ),
      );
    }

    final showRecent = _query.isEmpty &&
        _filter == _CategoryFilter.all &&
        _recentSearches.isNotEmpty;

    return ListView(
      children: [
        if (showRecent) ...[
          _SectionHeader(
            title: '최근 검색',
            action: '전체 삭제',
            onAction: () => setState(_recentSearches.clear),
          ),
          for (final query in _recentSearches)
            _RecentSearchRow(
              query: query,
              onTap: () => _applyRecentSearch(query),
            ),
          const SizedBox(height: AppSpacing.xs),
          const _SectionHeader(title: '전체 장소'),
        ],
        for (final (index, result) in results.indexed) ...[
          if (index != 0)
            const Divider(indent: AppSpacing.screen, endIndent: AppSpacing.screen),
          _ResultRow(result: result, onTap: () => _selectDestination(result)),
        ],
      ],
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, this.action, this.onAction});

  final String title;
  final String? action;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.screen,
        AppSpacing.md,
        AppSpacing.screen,
        AppSpacing.xxs,
      ),
      child: Row(
        children: [
          Expanded(child: Text(title, style: AppTextStyles.label)),
          if (action != null)
            GestureDetector(
              onTap: onAction,
              child: Text(
                action!,
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textTertiary,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _RecentSearchRow extends StatelessWidget {
  const _RecentSearchRow({required this.query, required this.onTap});

  final String query;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.screen,
          vertical: AppSpacing.sm,
        ),
        child: Row(
          children: [
            const Icon(Icons.history, size: 20, color: AppColors.iconDefault),
            const SizedBox(width: AppSpacing.sm),
            Expanded(child: Text(query, style: AppTextStyles.body)),
            const Icon(
              Icons.north_west,
              size: 16,
              color: AppColors.textTertiary,
            ),
          ],
        ),
      ),
    );
  }
}

/// 검색 결과 행 (design.md 8.2): 회색 아이콘 + `장소명 3F` + 보조 설명 + chevron.
class _ResultRow extends StatelessWidget {
  const _ResultRow({required this.result, required this.onTap});

  final PoiSearchResult result;
  final VoidCallback onTap;

  IconData get _icon {
    switch (result.category) {
      case 'toilet':
      case 'restroom':
        return Icons.wc;
      case 'elevator':
        return Icons.elevator_outlined;
      case 'escalator':
        return Icons.escalator;
      case 'exit':
        return Icons.logout;
      case null:
        return Icons.place_outlined;
      default:
        return Icons.storefront_outlined;
    }
  }

  String get _categoryLabel {
    switch (result.category) {
      case 'toilet':
      case 'restroom':
        return '화장실';
      case 'elevator':
        return '엘리베이터';
      case 'escalator':
        return '에스컬레이터';
      case 'exit':
        return '출구';
      case 'store':
      case 'fashion':
      case 'beauty':
      case 'service':
        return '매장';
      default:
        return '장소';
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Container(
        constraints: const BoxConstraints(minHeight: 68),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.screen,
          vertical: AppSpacing.sm,
        ),
        child: Row(
          children: [
            Icon(_icon, size: 22, color: AppColors.iconDefault),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text.rich(
                    TextSpan(
                      text: result.name,
                      style: AppTextStyles.bodyStrong,
                      children: [
                        TextSpan(
                          text: '  ${result.floor}',
                          style: AppTextStyles.label,
                        ),
                      ],
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$_categoryLabel · ${result.floor}',
                    style: AppTextStyles.caption,
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.chevron_right,
              size: 20,
              color: AppColors.textTertiary,
            ),
          ],
        ),
      ),
    );
  }
}
