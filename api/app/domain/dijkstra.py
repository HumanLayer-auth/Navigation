"""길찾기 그래프에서 최단 경로를 계산하는 다익스트라 알고리즘.

이 모듈은 FastAPI, SQLite, Repository를 알지 못한다. Service가 Repository에서
조회한 ``Node``와 ``Edge`` 목록을 전달하면 최단 경로 계산 결과만 반환한다.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import inf
from typing import Iterable

from app.domain.building import Edge, Node

# 인접 리스트에 저장할 한 항목: (다음 노드 ID, 사용 간선 ID, 간선 거리)
type Neighbor = tuple[str, str, float]

# 우선순위 큐에 저장할 한 항목: (출발점부터 누적 거리, 노드 ID)
type QueueItem = tuple[float, str]


@dataclass(frozen=True)
class ShortestPath:
    """다익스트라 최단 경로 계산 결과."""

    # 출발 노드부터 도착 노드까지 방문하는 순서
    node_ids: tuple[str, ...]

    # 위 노드들을 연결할 때 사용한 간선 순서
    edge_ids: tuple[str, ...]

    # 경로에 포함된 모든 간선 거리의 합
    total_distance_m: float


def find_shortest_path(
    nodes: Iterable[Node],
    edges: Iterable[Edge],
    start_node_id: str,
    end_node_id: str,
) -> ShortestPath | None:
    """출발 노드에서 도착 노드까지 거리 합이 가장 짧은 경로를 찾는다.

    Args:
        nodes: 건물에서 조회한 노드 목록.
        edges: 조회한 간선 목록.
        start_node_id: 출발 노드 ID.
        end_node_id: 도착 노드 ID.

    Returns:
        경로가 있으면 ``ShortestPath``, 연결된 경로가 없으면 ``None``.

    Raises:
        ValueError: 출발/도착 노드가 없거나 간선 데이터가 올바르지 않은 경우.
    """

    # Iterable은 한 번만 순회할 수 있으므로 ID를 키로 갖는 dict로 변환한다.
    # 이후 노드 존재 여부를 매번 전체 목록에서 찾지 않고 O(1)로 확인할 수 있다.
    nodes_by_id = {node.id: node for node in nodes}

    # 출발 노드가 그래프에 없으면 경로 탐색 자체가 불가능하다.
    if start_node_id not in nodes_by_id:
        raise ValueError(f"출발 노드 {start_node_id}가 존재하지 않습니다.")

    # 도착 노드도 그래프에 실제로 존재해야 한다.
    if end_node_id not in nodes_by_id:
        raise ValueError(f"도착 노드 {end_node_id}가 존재하지 않습니다.")

    # 출발지와 목적지가 같으면 이동할 간선이 없고 총 거리는 0이다.
    if start_node_id == end_node_id:
        return ShortestPath(
            node_ids=(start_node_id,),
            edge_ids=(),
            total_distance_m=0.0,
        )

    # Edge 목록을 "현재 노드에서 갈 수 있는 이웃 목록" 형태로 변환한다.
    graph = _build_graph(nodes_by_id, edges)

    # 출발점부터 각 노드까지 현재 발견한 최단 거리를 저장한다.
    # 아직 발견하지 못한 노드는 dict에 없으며 조회 시 inf로 취급한다.
    distances = {start_node_id: 0.0}

    # 경로 복원용 기록: 도착 노드 ID -> (직전 노드 ID, 사용한 간선 ID)
    previous: dict[str, tuple[str, str]] = {}

    # heapq는 첫 번째 값인 누적 거리가 가장 작은 항목부터 꺼낸다.
    # 탐색 시작 시에는 출발 노드 하나만 있고 출발점까지의 거리는 0이다.
    queue: list[QueueItem] = [(0.0, start_node_id)]

    # 더 이상 탐색할 후보가 없을 때까지 가장 가까운 노드부터 확인한다.
    while queue:
        # 현재까지 발견한 후보 중 출발점으로부터 가장 가까운 노드를 꺼낸다.
        current_distance, current_node_id = heapq.heappop(queue)

        # 같은 노드가 서로 다른 거리로 큐에 여러 번 들어갈 수 있다.
        # 현재 꺼낸 거리보다 더 짧은 거리가 이미 기록됐다면 오래된 후보이므로 무시한다.
        if current_distance > distances.get(current_node_id, inf):
            continue

        # 가장 짧은 후보로 목적지가 나왔으므로 최단 거리가 확정됐다.
        # previous를 역추적해 실제 노드와 간선 순서를 만들어 반환한다.
        if current_node_id == end_node_id:
            return _restore_path(
                previous=previous,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                total_distance_m=current_distance,
            )

        # 현재 노드에서 직접 이동할 수 있는 모든 이웃 노드를 확인한다.
        for next_node_id, edge_id, length_m in graph[current_node_id]:
            # 현재 노드를 거쳐 다음 노드로 이동했을 때의 전체 누적 거리다.
            next_distance = current_distance + length_m

            # 기존에 발견한 다음 노드까지의 최단 거리보다 짧지 않으면 갱신하지 않는다.
            # 다음 노드를 처음 발견한 경우 get()은 inf를 반환하므로 항상 갱신된다.
            if next_distance >= distances.get(next_node_id, inf):
                continue

            # 더 짧은 경로를 발견했으므로 다음 노드까지의 최단 거리를 교체한다.
            distances[next_node_id] = next_distance

            # 다음 노드에 어떤 노드와 간선을 통해 도착했는지 기록한다.
            # 탐색이 끝난 뒤 이 정보를 도착점부터 거꾸로 따라가 경로를 복원한다.
            previous[next_node_id] = (current_node_id, edge_id)

            # 갱신된 노드를 새로운 거리와 함께 다음 탐색 후보에 추가한다.
            heapq.heappush(queue, (next_distance, next_node_id))

    # 큐가 빌 때까지 목적지를 만나지 못했다면 연결된 경로가 없는 것이다.
    return None


def _build_graph(
    nodes_by_id: dict[str, Node],
    edges: Iterable[Edge],
) -> dict[str, list[Neighbor]]:
    """Edge 목록을 다익스트라가 탐색할 인접 리스트로 변환한다."""

    # 모든 노드에 빈 이웃 목록을 먼저 만든다.
    # 연결된 간선이 하나도 없는 고립 노드도 graph에 포함된다.
    graph: dict[str, list[Neighbor]] = {node_id: [] for node_id in nodes_by_id}

    # DB에서 조회한 간선을 하나씩 인접 리스트에 등록한다.
    for edge in edges:
        # 다익스트라는 음수 가중치를 지원하지 않으므로 잘못된 데이터를 거부한다.
        if edge.length_m < 0:
            raise ValueError(f"간선 {edge.id}의 거리는 음수일 수 없습니다.")

        # 간선의 시작 노드가 nodes 목록에 실제로 존재하는지 검증한다.
        if edge.from_node_id not in nodes_by_id:
            raise ValueError(
                f"간선 {edge.id}가 존재하지 않는 노드 {edge.from_node_id}를 참조합니다."
            )

        # 간선의 도착 노드도 nodes 목록에 실제로 존재해야 한다.
        if edge.to_node_id not in nodes_by_id:
            raise ValueError(
                f"간선 {edge.id}가 존재하지 않는 노드 {edge.to_node_id}를 참조합니다."
            )

        # 기본 진행 방향인 from_node -> to_node 이동 정보를 등록한다.
        graph[edge.from_node_id].append((edge.to_node_id, edge.id, edge.length_m))

        # 양방향 간선이면 반대 방향인 to_node -> from_node 이동도 등록한다.
        if edge.bidirectional:
            graph[edge.to_node_id].append(
                (edge.from_node_id, edge.id, edge.length_m)
            )

    # 완성된 인접 리스트를 다익스트라 탐색 함수에 반환한다.
    return graph


def _restore_path(
    previous: dict[str, tuple[str, str]],
    start_node_id: str,
    end_node_id: str,
    total_distance_m: float,
) -> ShortestPath:
    """직전 노드 기록을 도착점부터 역추적하여 정방향 경로로 복원한다."""

    # 도착점부터 역방향으로 따라갈 것이므로 도착 노드를 먼저 넣는다.
    node_ids = [end_node_id]

    # 도착점까지 사용한 간선도 역순으로 수집한다.
    edge_ids: list[str] = []

    # 현재 역추적 중인 노드는 도착점에서 시작한다.
    current_node_id = end_node_id

    # 출발점에 도달할 때까지 previous 기록을 한 단계씩 거슬러 올라간다.
    while current_node_id != start_node_id:
        # 현재 노드에 도착하기 직전 노드와 사용한 간선을 가져온다.
        previous_node_id, edge_id = previous[current_node_id]

        # 역추적 결과이므로 노드와 간선이 도착점부터 역순으로 쌓인다.
        node_ids.append(previous_node_id)
        edge_ids.append(edge_id)

        # 다음 반복에서는 직전 노드를 기준으로 다시 한 단계 거슬러 올라간다.
        current_node_id = previous_node_id

    # 현재 순서는 도착점 -> 출발점이므로 API에서 사용할 정방향으로 뒤집는다.
    node_ids.reverse()
    edge_ids.reverse()

    # 외부에서 결과가 실수로 변경되지 않도록 tuple 형태로 반환한다.
    return ShortestPath(
        node_ids=tuple(node_ids),
        edge_ids=tuple(edge_ids),
        total_distance_m=total_distance_m,
    )
