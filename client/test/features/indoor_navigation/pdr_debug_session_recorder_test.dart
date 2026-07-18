import 'package:flutter_test/flutter_test.dart';
import 'package:indoor_pdr_core/indoor_pdr_core.dart';
import 'package:navigation_client/features/indoor_navigation/contract/calibration_state.dart';
import 'package:navigation_client/features/indoor_navigation/contract/pdr_anchor.dart';
import 'package:navigation_client/features/indoor_navigation/debug/pdr_debug_session_recorder.dart';
import 'package:navigation_client/models/floor_graph.dart';

PdrSnapshot _snapshot({
  required int steps,
  required double distanceM,
  required List<PdrLocalPoint> path,
}) => PdrSnapshot(
  position: path.last,
  path: path,
  steps: steps,
  distanceM: distanceM,
  walkingHeadingDeg: 90,
  hasHeading: true,
  preview: PdrPreview(
    position: path.last,
    path: path,
    steps: steps + 1,
    distanceM: distanceM + 0.5,
  ),
  quality: const PdrQuality(
    state: PdrQualityState.caution,
    warnings: ['headingUnstable'],
    features: PdrQualityFeatures(
      greenOrangeDistanceDivergencePct: 10,
      orangeStepRatio: 1.1,
      orangeOvercountLikely: false,
      pedometerUndercountSuspected: false,
      pedometerFlaggedSpanS: 0,
      headingStable: false,
      headingSource: 'sensor_manager/rotation_vector+gyro_hold',
      magneticAccuracy: 'low',
      rotationHeadingAccuracyDeg: -1,
      cadenceHz: 1.5,
      pitchDeg: 4,
      rollDeg: -2,
      headingReferenceIsMagneticNorth: true,
      peakRejectHistogram: {},
    ),
  ),
);

FloorGraph _graph() => const FloorGraph(
  nodes: [
    GraphNode(id: 'a', type: 'path', xM: 0, yM: 0),
    GraphNode(id: 'b', type: 'path', xM: 10, yM: 0),
  ],
  edges: [
    GraphEdge(
      id: 'ab',
      fromNodeId: 'a',
      toNodeId: 'b',
      lengthM: 10,
      bidirectional: true,
      geometryLocalM: [LocalPoint(0, 0), LocalPoint(10, 0)],
    ),
  ],
);

void main() {
  test('확정 PDR 경로·품질·맵매칭 결과만 JSON으로 내보낸다', () {
    final recorder = PdrDebugSessionRecorder(
      startedAt: DateTime.utc(2026, 7, 18, 9),
    );
    recorder.recordCalibration(
      CalibrationStatus(
        phase: CalibrationPhase.calibrated,
        headingReference: HeadingReference.magneticNorth,
        requiresManualRotationCalibration: false,
        anchor: const PdrAnchor(
          floorId: '1F',
          anchorLocalM: PdrLocalPoint.zero,
          rotationDeg: 0,
          headingReference: HeadingReference.magneticNorth,
          requiresManualRotationCalibration: false,
          source: AnchorSource.userPin,
          confidence: 1,
        ),
      ),
    );
    recorder.recordSnapshot(
      _snapshot(
        steps: 4,
        distanceM: 3.1,
        path: const [PdrLocalPoint(0, 0), PdrLocalPoint(4, 1)],
      ),
      at: DateTime.utc(2026, 7, 18, 9, 0, 2),
    );

    final json = recorder.buildJson(
      buildingId: 'thehyundai-seoul',
      selectedFloor: '1F',
      graph: _graph(),
      device: const {'device_name': 'Test device'},
      exportedAt: DateTime.utc(2026, 7, 18, 9, 1),
    );

    final summary = json['summary']! as Map<String, Object?>;
    final paths = json['paths']! as Map<String, Object?>;
    final matched = paths['map_matched_floor_local_m']! as List<Object?>;
    final finalMatched = matched.last! as Map<String, double>;

    expect(json['schema_version'], 1);
    expect(summary['confirmed_steps'], 4);
    expect(
      (summary['quality']! as Map<String, Object?>)['magnetic_accuracy'],
      'low',
    );
    expect(finalMatched['east_m'], closeTo(4, 1e-9));
    expect(finalMatched['north_m'], closeTo(0, 1e-9));
    expect((json['quality_samples_1hz']! as List<Object?>), hasLength(1));
  });
}
