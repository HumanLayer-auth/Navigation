import 'package:flutter/material.dart';

/// GPS 신호 약함 등 상태를 알리는 pill 배지 (design.md 공통 컴포넌트: StatusBadge).
class StatusBadge extends StatelessWidget {
  const StatusBadge({super.key, required this.label, this.color = Colors.amber});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(16)),
      child: Text(label),
    );
  }
}
