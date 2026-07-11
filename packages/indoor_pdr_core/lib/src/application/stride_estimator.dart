/// confirmed path에 쓸 step distance를 고른다.
///
/// 우선순위는 Apple distance delta, Apple cadence/pace, fallback stride 순서다.
///
/// 연구 앱 `lib/src/pdr/stride_estimator.dart`에서 그대로 옮겼다(Flutter 비의존).
class StrideEstimator {
  static const double minMeters = 0.35;
  static const double maxMeters = 1.20;
  static const double _maxChangeFraction = 0.20;

  double fallbackMeters = 0.70;
  double iosDistanceM = 0;
  bool distanceAvailable = false;
  double cadenceHz = 0;
  double paceSecPerM = 0;
  bool cadenceAvailable = false;
  bool paceAvailable = false;
  double trackedDistanceM = 0;
  double effectiveMeters = 0.70;
  double lastBatchMeters = 0.70;
  String source = 'fixed';
  String rejectReason = 'none';

  double? _lastNativeDistanceM;
  int? _lastDistanceSteps;

  double autoMeters(int nativeSessionSteps) =>
      nativeSessionSteps > 0 ? iosDistanceM / nativeSessionSteps : 0;

  double get cadenceMeters =>
      paceSecPerM > 0 && cadenceHz > 0 ? 1.0 / (paceSecPerM * cadenceHz) : 0;

  double resolve({
    required int deltaSteps,
    required int cumulativeSteps,
    required int trackedSteps,
    required double? nativeDistanceM,
    required bool nativeDistanceAvailable,
  }) {
    final apple = _appleDistanceStride(
      deltaSteps: deltaSteps,
      cumulativeSteps: cumulativeSteps,
      nativeDistanceM: nativeDistanceM,
      nativeDistanceAvailable: nativeDistanceAvailable,
    );
    final cadence = apple == null ? _cadencePaceStride() : null;
    final measured = apple ?? cadence ?? fallbackMeters;

    lastBatchMeters = measured;
    source = apple != null
        ? 'apple-distance'
        : cadence != null
        ? 'cadence-pace'
        : 'fixed';
    if (apple != null) {
      rejectReason = 'none';
    } else if (cadence != null) {
      rejectReason = 'apple: $rejectReason';
    } else if (rejectReason == 'none') {
      rejectReason = 'fixed fallback';
    }

    effectiveMeters = _smooth(measured, trackedSteps);
    adoptDistanceBaseline(
      cumulativeSteps: cumulativeSteps,
      nativeDistanceM: nativeDistanceM,
      nativeDistanceAvailable: nativeDistanceAvailable,
    );
    return effectiveMeters;
  }

  void adoptDistanceBaseline({
    required int cumulativeSteps,
    required double? nativeDistanceM,
    required bool nativeDistanceAvailable,
  }) {
    if (!nativeDistanceAvailable || nativeDistanceM == null) {
      return;
    }
    _lastNativeDistanceM = nativeDistanceM;
    _lastDistanceSteps = cumulativeSteps;
  }

  void addTrackedDistance(double meters) {
    trackedDistanceM += meters;
  }

  void reset() {
    iosDistanceM = 0;
    distanceAvailable = false;
    cadenceHz = 0;
    paceSecPerM = 0;
    cadenceAvailable = false;
    paceAvailable = false;
    trackedDistanceM = 0;
    effectiveMeters = fallbackMeters;
    lastBatchMeters = fallbackMeters;
    source = 'fixed';
    rejectReason = 'none';
    _lastNativeDistanceM = null;
    _lastDistanceSteps = null;
  }

  static bool valid(double meters) =>
      meters >= minMeters && meters <= maxMeters;

  double? _appleDistanceStride({
    required int deltaSteps,
    required int cumulativeSteps,
    required double? nativeDistanceM,
    required bool nativeDistanceAvailable,
  }) {
    if (!nativeDistanceAvailable || nativeDistanceM == null) {
      rejectReason = 'nil distance';
      return null;
    }
    if (_lastNativeDistanceM == null || _lastDistanceSteps == null) {
      if (cumulativeSteps == deltaSteps && nativeDistanceM > 0) {
        final measured = nativeDistanceM / deltaSteps;
        if (valid(measured)) {
          return measured;
        }
        rejectReason = 'distance out of range';
        return null;
      }
      rejectReason = 'distance baseline';
      return null;
    }
    final distanceStepDelta = cumulativeSteps - _lastDistanceSteps!;
    if (distanceStepDelta != deltaSteps) {
      rejectReason = 'distance span mismatch';
      return null;
    }
    final distanceDelta = nativeDistanceM - _lastNativeDistanceM!;
    if (distanceDelta <= 0) {
      rejectReason = 'zero distance delta';
      return null;
    }
    final measured = distanceDelta / deltaSteps;
    if (!valid(measured)) {
      rejectReason = 'distance out of range';
      return null;
    }
    return measured;
  }

  double? _cadencePaceStride() {
    if (!cadenceAvailable ||
        !paceAvailable ||
        cadenceHz <= 0 ||
        paceSecPerM <= 0) {
      return null;
    }
    final measured = 1.0 / (paceSecPerM * cadenceHz);
    return valid(measured) ? measured : null;
  }

  double _smooth(double measured, int trackedSteps) {
    final previous = effectiveMeters > 0 ? effectiveMeters : measured;
    final lower = previous * (1 - _maxChangeFraction);
    final upper = previous * (1 + _maxChangeFraction);
    final capped = measured.clamp(lower, upper).toDouble();
    final alpha = trackedSteps < 10 ? 0.45 : 0.20;
    return (previous + (capped - previous) * alpha)
        .clamp(minMeters, maxMeters)
        .toDouble();
  }
}
