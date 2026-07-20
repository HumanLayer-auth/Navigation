import 'package:indoor_pdr_core/indoor_pdr_core.dart';

import '../indoor_navigation/contract/calibration_state.dart';
import '../indoor_navigation/contract/pdr_anchor.dart';

/// 디버그 지도에 마지막 PDR 경로를 유지하기 위한 화면 전용 상태다.
///
/// 센서 종료 시 controller는 calibration을 해제하지만 마지막 snapshot은 보존한다.
/// 지도는 마지막으로 확정된 anchor까지 함께 기억해 종료된 세션의 선을 계속
/// 렌더하고, 사용자가 다음 세션을 시작하는 순간에만 두 값을 비운다.
class DebugPdrTrailState {
  DebugPdrTrailState();

  factory DebugPdrTrailState.fromCurrent({
    PdrSnapshot? snapshot,
    CalibrationStatus? calibration,
  }) {
    final state = DebugPdrTrailState();
    if (snapshot != null) state.recordSnapshot(snapshot);
    if (calibration != null) state.recordCalibration(calibration);
    return state;
  }

  PdrSnapshot? _snapshot;
  PdrAnchor? _anchor;

  PdrSnapshot? get snapshot => _snapshot;
  PdrAnchor? get anchor => _anchor;

  void recordSnapshot(PdrSnapshot snapshot) {
    _snapshot = snapshot;
  }

  void recordCalibration(CalibrationStatus calibration) {
    if (calibration.canRenderPosition) {
      _anchor = calibration.anchor;
    }
  }

  void beginNewSession() {
    _snapshot = null;
    _anchor = null;
  }
}
