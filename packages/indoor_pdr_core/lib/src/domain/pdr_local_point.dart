import 'dart:math' as math;

/// 세션 시작점을 원점으로 한 로컬 미터 좌표. +east/+north.
///
/// 연구 앱은 `dart:ui`의 `Offset`(dx=east, dy=north)을 썼다. 코어는 Flutter에
/// 의존하지 않으므로 동일 의미의 순수 값 타입으로 대체한다.
class PdrLocalPoint {
  const PdrLocalPoint(this.eastM, this.northM);

  static const PdrLocalPoint zero = PdrLocalPoint(0, 0);

  final double eastM;
  final double northM;

  PdrLocalPoint operator +(PdrLocalPoint other) =>
      PdrLocalPoint(eastM + other.eastM, northM + other.northM);

  PdrLocalPoint operator -(PdrLocalPoint other) =>
      PdrLocalPoint(eastM - other.eastM, northM - other.northM);

  /// 원점으로부터의 유클리드 거리(m).
  double get distance => math.sqrt(eastM * eastM + northM * northM);

  @override
  bool operator ==(Object other) =>
      other is PdrLocalPoint &&
      other.eastM == eastM &&
      other.northM == northM;

  @override
  int get hashCode => Object.hash(eastM, northM);

  @override
  String toString() =>
      'PdrLocalPoint(${eastM.toStringAsFixed(3)}, ${northM.toStringAsFixed(3)})';
}
