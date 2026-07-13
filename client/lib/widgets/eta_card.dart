import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

/// 예상 소요 시간·거리 요약 (design.md 5.3): 숫자가 문장보다 먼저 읽히도록
/// `2분 · 180m` 형태로 크게 표시한다.
class EtaCard extends StatelessWidget {
  const EtaCard({super.key, required this.distanceMeters, required this.minutes});

  final double distanceMeters;
  final int minutes;

  @override
  Widget build(BuildContext context) {
    const numberStyle = TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      color: AppColors.textPrimary,
      height: 32 / 24,
    );
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.screen,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.large),
        boxShadow: appShadow,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          Text('$minutes분', style: numberStyle),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: AppSpacing.xs),
            child: Text(
              '·',
              style: TextStyle(fontSize: 20, color: AppColors.textTertiary),
            ),
          ),
          Text('${distanceMeters.round()}m', style: numberStyle),
        ],
      ),
    );
  }
}
