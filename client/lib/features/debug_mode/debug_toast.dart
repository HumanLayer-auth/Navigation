import 'package:flutter/material.dart';

/// 지도 내용을 최대한 가리지 않는 compact floating toast.
///
/// ScaffoldMessenger를 사용하므로 화면 전환·접근성 동작은 SnackBar와 같지만,
/// 하단 컨트롤 위에 작은 카드 형태로 떠 일반 배너보다 지도 가림이 적다.
void showDebugToast(
  BuildContext context, {
  required String message,
  double bottomOffset = 112,
  String? actionLabel,
  VoidCallback? onAction,
}) {
  final messenger = ScaffoldMessenger.of(context);
  messenger
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.fromLTRB(28, 0, 28, bottomOffset),
        duration: actionLabel == null
            ? const Duration(milliseconds: 2400)
            : const Duration(seconds: 5),
        elevation: 6,
        backgroundColor: const Color(0xF0212124),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        content: Text(
          message,
          maxLines: 3,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12.5,
            height: 1.35,
            fontWeight: FontWeight.w600,
          ),
        ),
        action: actionLabel == null || onAction == null
            ? null
            : SnackBarAction(
                label: actionLabel,
                textColor: const Color(0xFFAECBFA),
                onPressed: onAction,
              ),
      ),
    );
}
