import 'dart:math' as math;

import 'package:indoor_pdr_core/indoor_pdr_core.dart';

/// anchor 확정 근거.
enum AnchorSource { entranceGate, userPin, manualHeadingCal }

/// PDR 로컬 미터 좌표를 floor `local_m` 좌표에 고정하는 데 필요한 데이터(§4).
///
/// 변환은 `floor = axes·R(rotationDeg)·pdr + anchorLocalM`이다.
///
/// PDR 좌표는 언제나 +east/+north지만, 평면도 `local_m`은 데이터셋에 따라
/// +y가 남쪽이거나 축이 회전돼 있을 수 있다. [PdrToFloorAxes]가 이 좌표계
/// 차이를 흡수하고, [rotationDeg]는 자북을 얻지 못한 기기의 수동 heading
/// 보정에만 쓴다.
class PdrAnchor {
  const PdrAnchor({
    required this.floorId,
    required this.anchorLocalM,
    required this.rotationDeg,
    required this.headingReference,
    required this.requiresManualRotationCalibration,
    required this.source,
    required this.confidence,
    this.axes = const PdrToFloorAxes.identity(),
  });

  final String floorId;

  /// PDR 원점(세션 시작점)이 놓이는 floor 좌표(local_m). eastM=x_m, northM=y_m.
  final PdrLocalPoint anchorLocalM;

  /// PDR heading frame → floor frame 회전각(도).
  final double rotationDeg;

  /// heading이 자북 기준인지. arbitrary corrected fallback이면 수동 보정이 필요하다.
  final HeadingReference headingReference;

  /// 서버 자북 정렬각을 못 쓰는 상태(arbitrary reference)라 수동 방향 보정이 필수인지.
  final bool requiresManualRotationCalibration;

  final AnchorSource source;

  /// 0~1. anchor 신뢰도.
  final double confidence;

  /// 이 floor의 local axis 규약. anchor를 확정할 때와 이후 경로를 그릴 때
  /// 반드시 같은 값을 써야, anchor 직전의 센서 이동도 올바르게 상쇄된다.
  final PdrToFloorAxes axes;
}

/// 자북 기준 PDR의 `(east, north)` 증분을 floor `local_m`의 `(x, y)` 증분으로
/// 바꾸는 2×2 선형 변환이다.
///
/// 기본값은 기존 데이터셋과의 호환을 위한 항등이다. 실제 평면도에서는
/// WGS84 대응점으로부터 [fitPdrToFloorAxes]가 계산한 값을 사용한다. 예를 들어
/// 더현대 1F처럼 `+x=동쪽, +y=남쪽`인 경우 `(east, north) -> (east, -north)`가
/// 되어 북쪽 보행이 지도에서 반대로 표시되는 일을 막는다.
class PdrToFloorAxes {
  const PdrToFloorAxes({
    required this.eastToX,
    required this.northToX,
    required this.eastToY,
    required this.northToY,
  });

  const PdrToFloorAxes.identity()
    : eastToX = 1,
      northToX = 0,
      eastToY = 0,
      northToY = 1;

  final double eastToX;
  final double northToX;
  final double eastToY;
  final double northToY;

  PdrLocalPoint apply(PdrLocalPoint point) => PdrLocalPoint(
    eastToX * point.eastM + northToX * point.northM,
    eastToY * point.eastM + northToY * point.northM,
  );
}

/// PDR 좌표를 floor 좌표로 옮기는 순수 변환. UI는 이 결과 좌표만 렌더한다.
///
class FloorCoordinateTransform {
  FloorCoordinateTransform(this.anchor, {PdrToFloorAxes? axes})
    : axes = axes ?? anchor.axes;

  final PdrAnchor anchor;
  final PdrToFloorAxes axes;

  /// PDR 로컬 좌표를 floor local_m 좌표로 변환한다.
  PdrLocalPoint toFloor(PdrLocalPoint pdr) {
    final theta = anchor.rotationDeg * math.pi / 180.0;
    final cosT = math.cos(theta);
    final sinT = math.sin(theta);
    final rotated = PdrLocalPoint(
      pdr.eastM * cosT - pdr.northM * sinT,
      pdr.eastM * sinT + pdr.northM * cosT,
    );
    final floorDelta = axes.apply(rotated);
    return PdrLocalPoint(
      anchor.anchorLocalM.eastM + floorDelta.eastM,
      anchor.anchorLocalM.northM + floorDelta.northM,
    );
  }
}
