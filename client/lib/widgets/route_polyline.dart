import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../core/theme/app_theme.dart';

/// 경로 선 스타일 팩토리 (design.md 7.5): Deep Teal 5.5px + 2px 흰색 외곽선.
Polyline buildRoutePolyline(List<LatLng> points) {
  return Polyline(
    points: points,
    color: AppColors.primary,
    strokeWidth: 5.5,
    borderColor: const Color(0xFFFFFFFF),
    borderStrokeWidth: 2,
    strokeCap: StrokeCap.round,
    strokeJoin: StrokeJoin.round,
  );
}
