import 'accel_preview_track.dart';
import 'pedometer_batch_processor.dart';

/// 주황(accel preview) 기반 품질 신호 계산.
///
/// 연구 앱 `realtime_candidate_metrics.dart`에서 옮겼다. batch 입력을
/// `Map` 대신 [PedometerBatchRecord]로 읽는다.
class QualityMetrics {
  const QualityMetrics._();

  static bool pedometerUndercountSuspected(
    List<PedometerBatchRecord> pedometerBatches,
  ) =>
      undercountScan(pedometerBatches).flaggedSpanMs >=
      _undercountMinFlaggedSpanMs;

  static String confidence({
    required bool hasFusedHeading,
    required int accelPreviewSteps,
    required int nativeSessionSteps,
    required Map<String, int> accelPreviewRejectReasons,
    required bool pedometerUndercountSuspected,
  }) {
    if (!hasFusedHeading || accelPreviewSteps == 0) {
      return 'low';
    }
    if (accelOvercountLikely(
      nativeSessionSteps: nativeSessionSteps,
      accelPreviewSteps: accelPreviewSteps,
      pedometerUndercountSuspected: pedometerUndercountSuspected,
    )) {
      return 'low';
    }
    final dense = accelPreviewRejectReasons[AccelPreviewTrack.tooDense] ?? 0;
    if (dense > accelPreviewSteps * 0.1) {
      return 'low';
    }
    return 'medium';
  }

  static List<String> warnings({
    required int nativeSessionSteps,
    required int accelPreviewSteps,
    required Map<String, int> accelPreviewRejectReasons,
    required bool pedometerUndercountSuspected,
  }) {
    final warnings = <String>[];
    if (pedometerUndercountSuspected) {
      warnings.add('pedometerUndercountSuspected');
    }
    if (accelOvercountLikely(
      nativeSessionSteps: nativeSessionSteps,
      accelPreviewSteps: accelPreviewSteps,
      pedometerUndercountSuspected: pedometerUndercountSuspected,
    )) {
      warnings.add('distanceInflationLikely');
    }
    final rejects = accelPreviewRejectReasons;
    if ((rejects[AccelPreviewTrack.stepLeadCap] ?? 0) > 0) {
      warnings.add('leadCapExceeded');
    }
    if ((rejects[AccelPreviewTrack.tooDense] ?? 0) > 0) {
      warnings.add('densePeaksRejected');
    }
    return warnings;
  }

  static bool accelOvercountLikely({
    required int nativeSessionSteps,
    required int accelPreviewSteps,
    required bool pedometerUndercountSuspected,
  }) =>
      nativeSessionSteps > 0 &&
      accelPreviewSteps > nativeSessionSteps * _overcountStepRatio &&
      !pedometerUndercountSuspected;

  // CMPedometer undercount 감지 (배치 단위 일치검사).
  //
  // 구조적 근거: accel 이중검출은 pedometer가 세는 걸음 "위에 얹혀" 오므로
  // delta도 함께 크지만(관측 delta/peaks ≈ 0.5), undercount는 pedometer가
  // 침묵해 delta≈0이 된다(관측 ≈ 0.1). 0.4 임계가 두 regime을 가른다.
  //
  // 알려진 오탐 모드: 제자리에서 폰을 흔들거나 에스컬레이터 탑승처럼
  // "비보행 리듬 + pedometer 침묵"인 경우에도 켜질 수 있다. 그래서 이 플래그는
  // 진단 전용이며 green→orange 자동 전환에 절대 쓰지 않는다.
  static ({int flaggedSpanMs, int evaluatedBatches, int flaggedBatches})
  undercountScan(List<PedometerBatchRecord> pedometerBatches) {
    var flaggedSpanMs = 0;
    var evaluated = 0;
    var flagged = 0;
    for (final batch in pedometerBatches) {
      final start = batch.spanStartMs;
      final end = batch.spanEndMs;
      final peaks = batch.stepPeakTimes;
      final delta = batch.deltaSteps;
      if (start == null || end == null || end <= start || peaks == null) {
        continue;
      }
      final inSpan = peaks.where((t) => t > start && t <= end).length;
      if (inSpan < _undercountMinPeaksInSpan) {
        continue;
      }
      evaluated += 1;
      if (delta <= inSpan * _undercountDeltaRatio) {
        flagged += 1;
        flaggedSpanMs += end - start;
      }
    }
    return (
      flaggedSpanMs: flaggedSpanMs,
      evaluatedBatches: evaluated,
      flaggedBatches: flagged,
    );
  }

  static const int _undercountMinPeaksInSpan = 4;
  static const double _undercountDeltaRatio = 0.4;
  static const int _undercountMinFlaggedSpanMs = 10000;
  static const double _overcountStepRatio = 1.3;
}
