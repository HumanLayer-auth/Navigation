import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../models/poi_search_result.dart';
import '../../routing/app_routes.dart';

const _autoDismissDelay = Duration(seconds: 2);

/// 목적지 도착 화면 (design.md 10.5): Coral 강조는 도착 아이콘에만 최소로 쓴다.
class ArrivalScreen extends StatefulWidget {
  const ArrivalScreen({super.key});

  @override
  State<ArrivalScreen> createState() => _ArrivalScreenState();
}

class _ArrivalScreenState extends State<ArrivalScreen> {
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _autoDismissTimer = Timer(_autoDismissDelay, _startNewSearch);
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    super.dispose();
  }

  void _startNewSearch() {
    _autoDismissTimer?.cancel();
    if (!mounted) return;
    Navigator.of(
      context,
    ).pushNamedAndRemoveUntil(AppRoutes.indoorMap, (route) => route.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final destination =
        ModalRoute.of(context)?.settings.arguments as PoiSearchResult?;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.screen),
          child: Column(
            children: [
              const Spacer(flex: 3),
              Container(
                width: 88,
                height: 88,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.destinationSoft,
                ),
                child: const Icon(
                  Icons.check_rounded,
                  size: 44,
                  color: AppColors.destination,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              const Text('목적지에 도착했어요', style: AppTextStyles.heading2),
              if (destination != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '${destination.name} ${destination.floor}',
                  style: AppTextStyles.body.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
              const Spacer(flex: 4),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _startNewSearch,
                  child: const Text('새 목적지 탐색'),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
            ],
          ),
        ),
      ),
    );
  }
}
