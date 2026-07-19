import 'dart:math' as math;

import 'package:indoor_pdr_core/indoor_pdr_core.dart';

import '../../../models/floor_graph.dart';

/// PDR의 floor-local 위치를 navigation graph의 통행 가능한 간선 위로 붙인다.
///
/// 센서 위치 자체를 고치는 알고리즘은 아니다. 위치를 그래프 폴리라인의 가장
/// 가까운 선분으로 투영해 지도에는 "벽/매장 내부를 가로지르지 않는" 위치만
/// 보여 준다. 매칭 결과를 시간 순서로 계산하면, 인접하지 않은 복도로 순간
/// 점프하는 경우에는 직전 간선을 약하게 우선해 흔들림도 줄인다.
class FloorMapMatcher {
  FloorMapMatcher(FloorGraph graph, {this.edgeSwitchBiasM = 1.25})
    : _segments = _buildSegments(graph);

  /// 다른 간선으로 바뀌기 위해 필요한 추가 근접도. 평행한 두 복도 사이에서
  /// PDR 오차가 조금 흔들리는 경우, 경로가 프레임마다 번갈아 바뀌지 않게 한다.
  final double edgeSwitchBiasM;
  final List<_GraphSegment> _segments;
  String? _lastEdgeId;

  /// [raw]의 가장 가까운 graph 선분 위 점을 반환한다. 그래프에 유효한 선분이
  /// 없으면 null을 반환해 호출자가 기존 raw 좌표를 보조적으로 쓸 수 있게 한다.
  MapMatchedFloorPoint? match(PdrLocalPoint raw) {
    if (_segments.isEmpty) return null;

    final nearest = _nearestOn(_segments, raw);
    if (nearest == null) return null;

    var selected = nearest;
    final lastEdgeId = _lastEdgeId;
    if (lastEdgeId != null && nearest.edgeId != lastEdgeId) {
      final previousEdge = _nearestOn(
        _segments.where((segment) => segment.edgeId == lastEdgeId),
        raw,
      );
      // 더 가까운 간선이 확실히 유리할 때만 간선을 바꾼다. 교차점·분기점에서는
      // 두 후보 거리가 비슷하므로 직전 간선을 유지하고, 실제로 다음 복도로
      // 걸어 들어가면 거리 차가 커져 자연스럽게 전환된다.
      if (previousEdge != null &&
          nearest.distanceM + edgeSwitchBiasM >= previousEdge.distanceM) {
        selected = previousEdge;
      }
    }
    _lastEdgeId = selected.edgeId;
    return MapMatchedFloorPoint(
      point: selected.point,
      edgeId: selected.edgeId,
      distanceToGraphM: selected.distanceM,
    );
  }

  List<MapMatchedFloorPoint> matchPath(Iterable<PdrLocalPoint> rawPath) => [
    for (final point in rawPath) ?match(point),
  ];

  static List<_GraphSegment> _buildSegments(FloorGraph graph) {
    final nodes = {for (final node in graph.nodes) node.id: node};
    final segments = <_GraphSegment>[];
    for (final edge in graph.edges) {
      final geometry = edge.geometryLocalM.length >= 2
          ? edge.geometryLocalM
          : _edgeEndpoints(edge, nodes);
      for (var index = 1; index < geometry.length; index++) {
        final from = geometry[index - 1];
        final to = geometry[index];
        final dx = to.x - from.x;
        final dy = to.y - from.y;
        if (dx * dx + dy * dy < 1e-8) continue;
        segments.add(_GraphSegment(edge.id, from, to));
      }
    }
    return segments;
  }

  static List<LocalPoint> _edgeEndpoints(
    GraphEdge edge,
    Map<String, GraphNode> nodes,
  ) {
    final from = nodes[edge.fromNodeId];
    final to = nodes[edge.toNodeId];
    if (from == null || to == null) return const [];
    return [LocalPoint(from.xM, from.yM), LocalPoint(to.xM, to.yM)];
  }

  static _SegmentCandidate? _nearestOn(
    Iterable<_GraphSegment> segments,
    PdrLocalPoint raw,
  ) {
    _SegmentCandidate? best;
    for (final segment in segments) {
      final candidate = segment.project(raw);
      if (best == null || candidate.distanceM < best.distanceM) {
        best = candidate;
      }
    }
    return best;
  }
}

/// 지도 렌더링에 쓸 graph 위 좌표와 매칭 진단값.
class MapMatchedFloorPoint {
  const MapMatchedFloorPoint({
    required this.point,
    required this.edgeId,
    required this.distanceToGraphM,
  });

  final PdrLocalPoint point;
  final String edgeId;
  final double distanceToGraphM;
}

class _GraphSegment {
  const _GraphSegment(this.edgeId, this.from, this.to);

  final String edgeId;
  final LocalPoint from;
  final LocalPoint to;

  _SegmentCandidate project(PdrLocalPoint raw) {
    final dx = to.x - from.x;
    final dy = to.y - from.y;
    final lengthSquared = dx * dx + dy * dy;
    final rawT =
        ((raw.eastM - from.x) * dx + (raw.northM - from.y) * dy) /
        lengthSquared;
    final t = rawT.clamp(0.0, 1.0).toDouble();
    final point = PdrLocalPoint(from.x + dx * t, from.y + dy * t);
    final distanceM = math.sqrt(
      math.pow(raw.eastM - point.eastM, 2) +
          math.pow(raw.northM - point.northM, 2),
    );
    return _SegmentCandidate(edgeId, point, distanceM);
  }
}

class _SegmentCandidate {
  const _SegmentCandidate(this.edgeId, this.point, this.distanceM);

  final String edgeId;
  final PdrLocalPoint point;
  final double distanceM;
}
