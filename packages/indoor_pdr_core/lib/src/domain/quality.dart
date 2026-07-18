/// 품질 상태. UI는 이 값으로 표시를 결정하고, 로직은 config 임계로 판정한다.
enum PdrQualityState { healthy, caution, degraded }

/// 품질 판정과 future fusion 학습에 공통으로 쓰는 feature 원자료(§5).
///
/// 이 스키마는 fusion 라벨 데이터의 feature와 동일하게 유지한다.
class PdrQualityFeatures {
  const PdrQualityFeatures({
    required this.greenOrangeDistanceDivergencePct,
    required this.orangeStepRatio,
    required this.orangeOvercountLikely,
    required this.pedometerUndercountSuspected,
    required this.pedometerFlaggedSpanS,
    required this.headingStable,
    required this.headingSource,
    required this.magneticAccuracy,
    required this.rotationHeadingAccuracyDeg,
    required this.cadenceHz,
    required this.pitchDeg,
    required this.rollDeg,
    required this.headingReferenceIsMagneticNorth,
    required this.peakRejectHistogram,
  });

  /// |orange−green| / green (초록 거리 대비 주황 거리 괴리, %).
  final double greenOrangeDistanceDivergencePct;

  /// orangeSteps / greenSteps.
  final double orangeStepRatio;

  /// accel 과검출 의심(임계 1.3× — 잠정, Phase 5에서 재보정).
  final bool orangeOvercountLikely;

  /// CMPedometer 침묵 의심(진단 전용. 초록→주황 자동 전환에 쓰지 않는다).
  final bool pedometerUndercountSuspected;
  final double pedometerFlaggedSpanS;

  final bool headingStable;
  final String headingSource;
  final String magneticAccuracy;
  final double rotationHeadingAccuracyDeg;
  final double cadenceHz;
  final double pitchDeg;
  final double rollDeg;

  /// heading reference가 자북 기준인지. false면 arbitrary corrected fallback이다.
  final bool headingReferenceIsMagneticNorth;

  /// accel peak reject 사유별 카운트.
  final Map<String, int> peakRejectHistogram;
}

/// 품질 판정 결과.
class PdrQuality {
  const PdrQuality({
    required this.state,
    required this.warnings,
    required this.features,
  });

  final PdrQualityState state;
  final List<String> warnings;
  final PdrQualityFeatures features;
}
