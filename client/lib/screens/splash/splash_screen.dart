import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/service_locator.dart';
import '../../core/theme/app_theme.dart';
import '../../routing/app_routes.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _requestingPermissions = true;

  @override
  void initState() {
    super.initState();
    _requestPermissions();
  }

  Future<void> _requestPermissions() async {
    var anyDenied = false;
    try {
      final statuses = await requestStartupPermissions();
      anyDenied = statuses.values.any((status) => !status.isGranted);
    } catch (_) {
      // 권한 플러그인을 쓸 수 없는 환경(테스트 등)에서도 앱을 계속 진행한다.
    }

    if (!mounted) return;
    setState(() => _requestingPermissions = false);

    if (anyDenied) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('일부 권한이 거부되어 위치·실내 이동 관련 기능이 제한될 수 있습니다')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            if (_requestingPermissions)
              const LinearProgressIndicator(
                backgroundColor: AppColors.primarySoft,
                minHeight: 2,
              ),
            Expanded(
              // 화면이 아주 낮을 때(가로 모드·작은 창)도 오버플로 없이
              // 스크롤로 내려볼 수 있게 한다.
              child: LayoutBuilder(
                builder: (context, constraints) => SingleChildScrollView(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight,
                    ),
                    child: IntrinsicHeight(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.screen,
                        ),
                        child: Column(
                          children: [
                            const Spacer(flex: 3),
                            Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                color: AppColors.primary,
                                borderRadius: BorderRadius.circular(
                                  AppRadius.sheet,
                                ),
                              ),
                              child: const Icon(
                                Icons.navigation_rounded,
                                color: Colors.white,
                                size: 34,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.lg),
                            const Text(
                              'Navigation',
                              style: AppTextStyles.heading1,
                            ),
                            const SizedBox(height: AppSpacing.xs),
                            Text(
                              '실내에서도 길을 잃지 않게',
                              style: AppTextStyles.body.copyWith(
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const Spacer(flex: 4),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton(
                                onPressed: () {
                                  Navigator.of(
                                    context,
                                  ).pushNamed(AppRoutes.outdoorMap);
                                },
                                child: const Text('시작하기'),
                              ),
                            ),
                            const SizedBox(height: AppSpacing.md),
                            Wrap(
                              alignment: WrapAlignment.center,
                              children: [
                                _DevLink(
                                  label: 'API 상태 확인',
                                  onTap: () => Navigator.of(
                                    context,
                                  ).pushNamed(AppRoutes.debugApiHealth),
                                ),
                                _DevLink(
                                  label: '더현대 평면도',
                                  onTap: () => Navigator.of(
                                    context,
                                  ).pushNamed(AppRoutes.debugFloorMapPreview),
                                ),
                                _DevLink(
                                  label: 'PDR 테스트',
                                  onTap: () => Navigator.of(
                                    context,
                                  ).pushNamed(AppRoutes.pdrSvgTest),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.xs),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 개발용 진입점 링크. 실제 사용자 플로우가 아니므로 tertiary 톤으로 낮춘다.
class _DevLink extends StatelessWidget {
  const _DevLink({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onTap,
      style: TextButton.styleFrom(
        foregroundColor: AppColors.textTertiary,
        textStyle: AppTextStyles.caption,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
        minimumSize: const Size(0, 36),
      ),
      child: Text(label),
    );
  }
}
