import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

/// 건물 정보 Q&A 패널 (design.md 공통 컴포넌트: RagChatPanel).
/// 실제 RAG 응답이 붙기 전까지 하드코딩된 대화 샘플을 보여준다.
class RagChatPanel extends StatelessWidget {
  const RagChatPanel({super.key});

  static const _sampleExchanges = [
    ('화장실 몇 시까지 이용 가능해요?', '본관 화장실은 22시까지 운영합니다.'),
    ('엘리베이터는 어디 있어요?', '정문 로비 안내데스크 옆에 있습니다.'),
  ];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.screen,
          AppSpacing.sm,
          AppSpacing.screen,
          AppSpacing.screen,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.divider,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            const Text('건물 정보 Q&A', style: AppTextStyles.title),
            const SizedBox(height: AppSpacing.sm),
            for (final exchange in _sampleExchanges) ...[
              Align(
                alignment: Alignment.centerRight,
                child: _bubble(
                  exchange.$1,
                  background: AppColors.primarySoft,
                ),
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: _bubble(
                  exchange.$2,
                  background: AppColors.surfaceSubtle,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _bubble(String text, {required Color background}) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: AppSpacing.xxs),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadius.medium),
      ),
      child: Text(text, style: AppTextStyles.body),
    );
  }
}
