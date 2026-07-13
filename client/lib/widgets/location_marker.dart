import 'package:flutter/material.dart';

import '../core/theme/app_theme.dart';

/// 현재 위치 마커 모드. design.md 7.6: 실내외 모두 현재 위치는 Deep Teal이며,
/// 실내(PDR)는 화면 밀도가 높아 한 단계 작게 그린다.
enum LocationMode {
  outdoor(color: AppColors.primary, icon: Icons.navigation, size: 30),
  indoor(color: AppColors.primary, icon: Icons.navigation, size: 26);

  const LocationMode({
    required this.color,
    required this.icon,
    required this.size,
  });

  final Color color;
  final IconData icon;
  final double size;
}

/// 현재 위치 마커 (design.md 7.6): Deep Teal 원형 + 흰색 외곽선 + 방향 화살표.
///
/// [colorOverride]는 GPS 정확도 낮음 등 상태에 따라 기본 모드 색을 덮어써야 할 때 쓴다.
class LocationMarker extends StatelessWidget {
  const LocationMarker({super.key, required this.mode, this.colorOverride});

  final LocationMode mode;
  final Color? colorOverride;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: mode.size,
      height: mode.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorOverride ?? mode.color,
        border: Border.all(color: Colors.white, width: 2.5),
        boxShadow: appShadow,
      ),
      child: Icon(mode.icon, color: Colors.white, size: mode.size * 0.5),
    );
  }
}
