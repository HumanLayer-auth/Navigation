import 'dart:math' as math;

import '../domain/angle_utils.dart';
import '../domain/heading_sample.dart';

/// step batch가 늦게 도착했을 때 해당 시점의 heading을 되찾기 위한 history.
///
/// 연구 앱 `heading_tracker.dart`에서 옮겼다. export 전용 메서드는 제거했다.
class HeadingHistory {
  HeadingHistory({this.maxAgeMs = 20000});

  final int maxAgeMs;
  final List<HeadingSample> _samples = [];

  void add(HeadingSample sample) {
    _samples.add(sample);
    prune(sample.ms);
  }

  HeadingSample? at(int ms) {
    for (var i = _samples.length - 1; i >= 0; i -= 1) {
      if (_samples[i].ms <= ms) {
        return _samples[i];
      }
    }
    return _samples.isEmpty ? null : _samples.first;
  }

  void prune(int nowMs) {
    var drop = 0;
    while (drop < _samples.length && _samples[drop].ms < nowMs - maxAgeMs) {
      drop += 1;
    }
    if (drop > 0) {
      _samples.removeRange(0, drop);
    }
  }

  void clear() => _samples.clear();
}

/// raw heading window로 팔 흔들림인지 실제 회전인지 구분한다.
class SwingDetector {
  final List<({int ms, double deg})> _window = [];

  bool swinging = false;
  double oscillationDeg = 0;

  double get netDeg {
    if (_window.length < 2) {
      return 0;
    }
    return shortestDeltaDegrees(_window.last.deg - _window.first.deg).abs();
  }

  void update(int nowMs, double rawDeg) {
    _window.add((ms: nowMs, deg: rawDeg));
    var drop = 0;
    while (drop < _window.length && _window[drop].ms < nowMs - 1500) {
      drop += 1;
    }
    if (drop > 0) {
      _window.removeRange(0, drop);
    }
    if (_window.length < 6) {
      swinging = false;
      oscillationDeg = 0;
      return;
    }

    var sumSin = 0.0;
    var sumCos = 0.0;
    for (final sample in _window) {
      final r = sample.deg * math.pi / 180;
      sumSin += math.sin(r);
      sumCos += math.cos(r);
    }
    final meanDeg = math.atan2(sumSin, sumCos) * 180 / math.pi;
    var minD = 0.0;
    var maxD = 0.0;
    for (final sample in _window) {
      final d = shortestDeltaDegrees(sample.deg - meanDeg);
      minD = math.min(minD, d);
      maxD = math.max(maxD, d);
    }
    final peakToPeak = maxD - minD;
    oscillationDeg = math.max(0, peakToPeak - netDeg);
    swinging = swinging ? oscillationDeg > 18 : oscillationDeg > 30;
  }

  void reset() {
    _window.clear();
    swinging = false;
    oscillationDeg = 0;
  }
}

/// 팔 흔들림에서 추정한 보행축을 fused heading에 천천히 반영한다.
class WalkOffsetEstimator {
  static const double confidenceThreshold = 0.35;
  static const double _tauSeconds = 2.5;
  static const double _decayTauSeconds = 12.0;
  static const double _maxDeg = 60.0;
  static const double turnGateNetDeg = 20.0;

  double offsetDeg = 0;
  bool active = false;
  int turnHoldUntilMs = 0;

  void update({
    required int nowMs,
    required double dtSeconds,
    required bool swinging,
    required double swingNetDeg,
    required double walkDirDeg,
    required double walkDirConfidence,
    required double fusedHeadingDeg,
  }) {
    if (swingNetDeg > turnGateNetDeg) {
      turnHoldUntilMs = nowMs + 1500;
    }

    if (!swinging) {
      offsetDeg *= math.exp(-dtSeconds / _decayTauSeconds);
      active = false;
      return;
    }
    if (nowMs < turnHoldUntilMs || walkDirConfidence < confidenceThreshold) {
      active = false;
      return;
    }

    final current = normalizeDegrees(fusedHeadingDeg + offsetDeg);
    final branchA = walkDirDeg;
    final branchB = normalizeDegrees(walkDirDeg + 180);
    final target =
        shortestDeltaDegrees(branchA - current).abs() <=
            shortestDeltaDegrees(branchB - current).abs()
        ? branchA
        : branchB;
    final desiredOffset = shortestDeltaDegrees(target - fusedHeadingDeg);
    final alpha = 1 - math.exp(-dtSeconds / _tauSeconds);
    final updated = shortestDeltaDegrees(
      offsetDeg + shortestDeltaDegrees(desiredOffset - offsetDeg) * alpha,
    );
    offsetDeg = updated.clamp(-_maxDeg, _maxDeg);
    active = true;
  }

  void reset() {
    offsetDeg = 0;
    active = false;
    turnHoldUntilMs = 0;
  }
}
