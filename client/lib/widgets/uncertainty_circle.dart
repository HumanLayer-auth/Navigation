import 'package:flutter/material.dart';

/// 위치 추정 불확실성(Particle Filter 분산 등)을 반투명 원으로 표현한다
/// (design.md 공통 컴포넌트: UncertaintyCircle).
class UncertaintyCircle extends StatelessWidget {
  const UncertaintyCircle({super.key, required this.diameter, required this.color});

  final double diameter;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: diameter,
      height: diameter,
      child: DecoratedBox(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withValues(alpha: 0.2),
        ),
      ),
    );
  }
}
