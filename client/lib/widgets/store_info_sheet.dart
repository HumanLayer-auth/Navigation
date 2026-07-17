import 'package:flutter/material.dart';

import '../core/service_locator.dart';
import '../models/favorite_place.dart';
import '../state/favorites_controller.dart';
import '../theme/app_theme.dart';

/// 매장 정보 시트에서 사용자가 고를 수 있는 다음 동작.
enum StoreInfoAction { setOrigin, setDestination }

/// 실내 검색에서 매장을 고르면 뜨는 정보 시트. 길찾기 시트와 같은 형태로
/// 아래에서 올라온다. 매장 상세 정보(사진·설명 등)는 아직 백엔드에 없어
/// 비워두고, 우하단의 출발지/도착지 버튼으로 바로 길찾기 시트로 넘어갈 수
/// 있게만 한다.
///
/// [favorite]이 주어지면 매장 이름 옆에 즐겨찾기 토글(+/체크) 버튼이 붙는다.
/// 저장되지 않은 상태에서 누르면 [FavoritesController]에 추가, 이미 저장된
/// 상태에서 누르면 삭제한다.
class StoreInfoSheet extends StatefulWidget {
  const StoreInfoSheet({
    super.key,
    required this.title,
    required this.subtitle,
    this.favorite,
  });

  final String title;
  final String subtitle;

  /// null이면 즐겨찾기 버튼을 숨긴다(예: 건물 자체 정보처럼 매장이 아닌 경우).
  final FavoritePlace? favorite;

  static Future<StoreInfoAction?> show(
    BuildContext context, {
    required String title,
    required String subtitle,
    FavoritePlace? favorite,
  }) {
    return showModalBottomSheet<StoreInfoAction>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => StoreInfoSheet(
        title: title,
        subtitle: subtitle,
        favorite: favorite,
      ),
    );
  }

  @override
  State<StoreInfoSheet> createState() => _StoreInfoSheetState();
}

class _StoreInfoSheetState extends State<StoreInfoSheet> {
  @override
  void initState() {
    super.initState();
    favoritesController.addListener(_onFavoritesChanged);
  }

  @override
  void dispose() {
    favoritesController.removeListener(_onFavoritesChanged);
    super.dispose();
  }

  void _onFavoritesChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _onToggleFavorite() async {
    final favorite = widget.favorite;
    if (favorite == null) return;
    await favoritesController.toggle(favorite);
    if (!mounted) return;
    final saved = favoritesController.contains(favorite.key);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(saved ? '장소에 저장했습니다' : '저장을 취소했습니다'),
        duration: const Duration(milliseconds: 1400),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final favorite = widget.favorite;
    final saved = favorite != null && favoritesController.contains(favorite.key);
    return DraggableScrollableSheet(
      initialChildSize: 0.42,
      minChildSize: 0.3,
      maxChildSize: 0.8,
      expand: false,
      builder: (context, scrollController) {
        return SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: const Color(0xFFEEF3FF),
                      borderRadius: BorderRadius.circular(13),
                    ),
                    alignment: Alignment.center,
                    child: const Icon(Icons.storefront, color: AppColors.primary, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                widget.title,
                                style: const TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.text,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            if (favorite != null) ...[
                              const SizedBox(width: 6),
                              IconButton(
                                onPressed: _onToggleFavorite,
                                iconSize: 20,
                                padding: EdgeInsets.zero,
                                visualDensity: VisualDensity.compact,
                                constraints: const BoxConstraints(
                                  minWidth: 32,
                                  minHeight: 32,
                                ),
                                tooltip: saved ? '저장 취소' : '장소로 저장',
                                icon: Icon(
                                  saved ? Icons.check_circle : Icons.add_circle_outline,
                                  color: saved ? Colors.green : AppColors.primary,
                                ),
                              ),
                            ],
                          ],
                        ),
                        Text(
                          widget.subtitle,
                          style: const TextStyle(fontSize: 12.5, color: AppColors.muted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              // 매장 상세 정보(사진·설명 등)는 아직 준비되지 않아 비워둔다.
              const SizedBox(height: 32),
              Align(
                alignment: Alignment.bottomRight,
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FilledButton(
                      onPressed: () => Navigator.of(context).pop(StoreInfoAction.setOrigin),
                      child: const Text('출발'),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.of(context).pop(StoreInfoAction.setDestination),
                      child: const Text('도착'),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
