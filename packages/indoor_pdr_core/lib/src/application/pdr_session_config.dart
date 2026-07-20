/// PdrSession 설정. 임계값은 전부 여기로 주입한다(코어에 하드코딩 금지).
///
/// 품질 임계는 잠정치다. Phase 5의 라벨 데이터로 재보정한다(§5).
class PdrSessionConfig {
  const PdrSessionConfig({
    this.fallbackStrideMeters = 0.70,
    this.maxPathPoints = 800,
    this.cautionDivergencePct = 10.0,
    this.nowMs = _defaultNowMs,
  });

  /// Apple distance/cadence를 못 쓸 때의 기본 보폭(m).
  final double fallbackStrideMeters;

  /// green/orange 경로 point 상한(메모리 보호).
  final int maxPathPoints;

  /// 초록·주황 거리 괴리가 이 %를 넘으면 caution(잠정, §5에서 재보정).
  final double cautionDivergencePct;

  /// 수신 시각 clock. 결정적 테스트를 위해 주입 가능.
  final int Function() nowMs;

  static int _defaultNowMs() => DateTime.now().millisecondsSinceEpoch;
}
