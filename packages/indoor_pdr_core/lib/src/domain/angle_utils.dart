/// PDR 파이프라인에서 같이 쓰는 각도 유틸. 모든 각도 단위는 degree다.
///
/// 연구 앱 `lib/src/pdr/angle_utils.dart`에서 그대로 옮겼다.
library;

/// [degrees]를 [0, 360) 범위로 접는다.
double normalizeDegrees(double degrees) {
  final normalized = degrees % 360;
  return normalized < 0 ? normalized + 360 : normalized;
}

/// [degrees]를 (-180, 180] 범위의 signed 최단각으로 바꾼다.
double shortestDeltaDegrees(double degrees) {
  var delta = degrees % 360;
  if (delta > 180) {
    delta -= 360;
  } else if (delta < -180) {
    delta += 360;
  }
  return delta;
}
