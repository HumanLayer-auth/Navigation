import 'pdr_local_point.dart';
import 'quality.dart';

/// 주황(accel preview) 경로 스냅샷. 독립 거리 관측치이자 품질 신호다.
/// confirmed(초록) 위치·거리·걸음수에는 절대 반영하지 않는다.
class PdrPreview {
  const PdrPreview({
    required this.position,
    required this.path,
    required this.steps,
    required this.distanceM,
  });

  final PdrLocalPoint position;
  final List<PdrLocalPoint> path;
  final int steps;
  final double distanceM;
}

/// 코어가 내보내는 관측 스냅샷. UI는 이것을 구독해 렌더한다.
class PdrSnapshot {
  const PdrSnapshot({
    required this.position,
    required this.path,
    required this.steps,
    required this.distanceM,
    required this.walkingHeadingDeg,
    required this.hasHeading,
    required this.preview,
    required this.quality,
  });

  /// 초록 confirmed 위치(제품 위치). 로컬 미터, 세션 시작점 기준.
  final PdrLocalPoint position;
  final List<PdrLocalPoint> path;
  final int steps;
  final double distanceM;

  /// fused heading + walkOffset 보정이 들어간 실제 보행 방향(자북 기준일 때).
  final double walkingHeadingDeg;
  final bool hasHeading;

  final PdrPreview preview;
  final PdrQuality quality;
}
