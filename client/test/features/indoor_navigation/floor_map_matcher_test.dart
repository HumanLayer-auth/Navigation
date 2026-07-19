import 'package:flutter_test/flutter_test.dart';
import 'package:navigation_client/features/indoor_navigation/application/floor_map_matcher.dart';
import 'package:navigation_client/models/floor_graph.dart';
import 'package:indoor_pdr_core/indoor_pdr_core.dart';

FloorGraph _testGraph() => FloorGraph(
  nodes: const [
    GraphNode(id: 'a', type: 'path', xM: 0, yM: 0),
    GraphNode(id: 'b', type: 'path', xM: 10, yM: 0),
    GraphNode(id: 'c', type: 'path', xM: 10, yM: 10),
    GraphNode(id: 'd', type: 'path', xM: 0, yM: 3),
    GraphNode(id: 'e', type: 'path', xM: 10, yM: 3),
  ],
  edges: const [
    GraphEdge(
      id: 'ab',
      fromNodeId: 'a',
      toNodeId: 'b',
      lengthM: 10,
      bidirectional: true,
      geometryLocalM: [LocalPoint(0, 0), LocalPoint(10, 0)],
    ),
    GraphEdge(
      id: 'bc',
      fromNodeId: 'b',
      toNodeId: 'c',
      lengthM: 10,
      bidirectional: true,
      geometryLocalM: [LocalPoint(10, 0), LocalPoint(10, 10)],
    ),
    GraphEdge(
      id: 'de',
      fromNodeId: 'd',
      toNodeId: 'e',
      lengthM: 10,
      bidirectional: true,
      geometryLocalM: [LocalPoint(0, 3), LocalPoint(10, 3)],
    ),
  ],
);

void main() {
  group('FloorMapMatcher', () {
    test('PDR 좌표를 가장 가까운 복도 선분으로 투영한다', () {
      final matched = FloorMapMatcher(
        _testGraph(),
      ).match(const PdrLocalPoint(4, 1.2));

      expect(matched, isNotNull);
      expect(matched!.edgeId, 'ab');
      expect(matched.point.eastM, closeTo(4, 1e-9));
      expect(matched.point.northM, closeTo(0, 1e-9));
      expect(matched.distanceToGraphM, closeTo(1.2, 1e-9));
    });

    test('분기 뒤에는 다음 graph 간선 위로 자연스럽게 전환한다', () {
      final matcher = FloorMapMatcher(_testGraph());
      final path = matcher.matchPath(const [
        PdrLocalPoint(8, 0.3),
        PdrLocalPoint(10.2, 4),
      ]);

      expect(path.map((point) => point.edgeId), ['ab', 'bc']);
      expect(path.last.point.eastM, closeTo(10, 1e-9));
      expect(path.last.point.northM, closeTo(4, 1e-9));
    });

    test('평행 복도 사이의 작은 센서 흔들림은 직전 간선을 유지한다', () {
      final matcher = FloorMapMatcher(_testGraph());
      final path = matcher.matchPath(const [
        PdrLocalPoint(2, 0.2),
        PdrLocalPoint(4, 1.6),
      ]);

      expect(path.map((point) => point.edgeId), ['ab', 'ab']);
      expect(path.last.point.northM, closeTo(0, 1e-9));
    });
  });
}
