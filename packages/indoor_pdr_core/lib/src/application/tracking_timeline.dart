/// tracking(pause/resume) 전이를 motion 시간축으로 관리한다.
///
/// CMPedometer batch는 늦게 도착하고 pause/resume 경계를 가로지를 수 있다. 이
/// 타임라인이 tracking이 켜져 있던 동안의 step 비율만 남기게 해 준다.
///
/// 연구 앱 `lib/src/pdr/tracking_timeline.dart`에서 그대로 옮겼다(Flutter 비의존).
typedef TrackedBatchSplit = ({
  int count,
  double fraction,
  int? spanStartMs,
  int? spanEndMs,
  List<double>? peakTimes,
});

class TrackingTimeline {
  TrackingTimeline();

  final List<({int atMs, bool on})> _transitions = [];
  bool _initialOn = true;

  void reset({required bool initialOn}) {
    _transitions.clear();
    _initialOn = initialOn;
  }

  void addTransition({required int atMs, required bool on}) {
    _transitions.add((atMs: atMs, on: on));
  }

  TrackedBatchSplit resolveBatch({
    required int deltaSteps,
    required int? spanStartMs,
    required int? spanEndMs,
    required List<double>? peakTimes,
    required bool currentlyTracking,
  }) {
    final canSplit =
        spanStartMs != null && spanEndMs != null && spanEndMs > spanStartMs;
    if (!canSplit) {
      return (
        count: currentlyTracking ? deltaSteps : 0,
        fraction: currentlyTracking ? 1.0 : 0.0,
        spanStartMs: spanStartMs,
        spanEndMs: spanEndMs,
        peakTimes: peakTimes,
      );
    }

    final a = spanStartMs;
    final b = spanEndMs;
    List<double>? peaksInSpan;
    if (peakTimes != null) {
      peaksInSpan = peakTimes.where((t) => t > a && t <= b).toList()..sort();
    }

    double fraction;
    List<double>? recordablePeaks;
    if (peaksInSpan != null && peaksInSpan.isNotEmpty) {
      recordablePeaks = peaksInSpan
          .where((t) => isTrackingOnAt(t.round()))
          .toList();
      fraction = recordablePeaks.length / peaksInSpan.length;
    } else {
      fraction = _trackedOverlapFraction(a, b);
    }

    final count = (deltaSteps * fraction).round().clamp(0, deltaSteps).toInt();
    if (count >= deltaSteps) {
      return (
        count: deltaSteps,
        fraction: fraction,
        spanStartMs: a,
        spanEndMs: b,
        peakTimes: peakTimes,
      );
    }

    final bounds = _trackedBounds(a, b);
    return (
      count: count,
      fraction: fraction,
      spanStartMs: bounds?.start ?? a,
      spanEndMs: bounds?.end ?? b,
      peakTimes: recordablePeaks ?? peakTimes,
    );
  }

  bool isTrackingOnAt(int tMs) {
    var state = _initialOn;
    for (final transition in _transitions) {
      if (transition.atMs <= tMs) {
        state = transition.on;
      } else {
        break;
      }
    }
    return state;
  }

  double _trackedOverlapFraction(int a, int b) {
    if (b <= a) {
      return isTrackingOnAt(a) ? 1.0 : 0.0;
    }
    var onMs = 0;
    var cursor = a;
    var state = isTrackingOnAt(a);
    for (final transition in _transitions) {
      if (transition.atMs <= a) {
        continue;
      }
      if (transition.atMs >= b) {
        break;
      }
      if (state) {
        onMs += transition.atMs - cursor;
      }
      cursor = transition.atMs;
      state = transition.on;
    }
    if (state) {
      onMs += b - cursor;
    }
    return onMs / (b - a);
  }

  ({int start, int end})? _trackedBounds(int a, int b) {
    int? start;
    int? end;
    var cursor = a;
    var state = isTrackingOnAt(a);
    void mark(int from, int to) {
      start ??= from;
      end = to;
    }

    for (final transition in _transitions) {
      if (transition.atMs <= a) {
        continue;
      }
      if (transition.atMs >= b) {
        break;
      }
      if (state) {
        mark(cursor, transition.atMs);
      }
      cursor = transition.atMs;
      state = transition.on;
    }
    if (state) {
      mark(cursor, b);
    }
    if (start == null || end == null) {
      return null;
    }
    return (start: start!, end: end!);
  }
}
