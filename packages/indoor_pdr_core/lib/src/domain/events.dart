/// 코어에 들어오는 typed 센서 이벤트.
///
/// 연구 앱은 native EventChannel의 raw `Map`을 `PdrNativeEvent.tryParse`로 파싱했다.
/// 코어는 플랫폼을 모르므로, adapter(플랫폼 계층)가 raw map을 아래 타입으로 변환해
/// 넣는다. 코어에는 `Map<dynamic,dynamic>`이 진입하지 않는다.
library;

/// CoreMotion DeviceMotion 묶음에서 코어가 쓰는 필드.
class HeadingEvent {
  const HeadingEvent({
    required this.motionTimestampMs,
    required this.fusedHeadingDeg,
    this.headingStable,
    this.deviceHeadingDeg,
    this.yawDeg,
    this.gyroHeadingDeg,
    this.pitchDeg,
    this.rollDeg,
    this.walkDirDeg,
    this.walkDirConfidence,
    this.magneticAccuracy,
    this.headingSource,
  });

  /// native step peak timestamp와 같은 시간축. heading history/step 시각 정렬의 기준.
  final int motionTimestampMs;
  final double fusedHeadingDeg;
  final bool? headingStable;
  final double? deviceHeadingDeg;
  final double? yawDeg;
  final double? gyroHeadingDeg;
  final double? pitchDeg;
  final double? rollDeg;
  final double? walkDirDeg;
  final double? walkDirConfidence;
  final String? magneticAccuracy;
  final String? headingSource;
}

/// CMPedometer 배치. iOS가 1~2.5초 단위로 늦게 flush한다.
class PedometerBatchEvent {
  const PedometerBatchEvent({
    required this.steps,
    this.stepSessionId,
    this.sessionStartMs,
    this.timestampMs,
    this.deltaMs,
    this.distanceM,
    this.distanceAvailable,
    this.cadenceHz,
    this.paceSecPerM,
    this.cadenceAvailable,
    this.paceAvailable,
    this.stepPeakTimes,
  });

  final int steps;
  final int? stepSessionId;
  final int? sessionStartMs;
  final double? timestampMs;
  final double? deltaMs;
  final double? distanceM;
  final bool? distanceAvailable;
  final double? cadenceHz;
  final double? paceSecPerM;
  final bool? cadenceAvailable;
  final bool? paceAvailable;
  final List<double>? stepPeakTimes;
}

/// native accel step-peak 카운터 신호. 주황(preview) 경로 전용.
class AccelPeakEvent {
  const AccelPeakEvent({
    required this.count,
    this.latestPeakMs,
    this.motionTimestampMs,
  });

  final int count;
  final int? latestPeakMs;
  final num? motionTimestampMs;
}
