# `app/routing` — 경로 탐색 순수 로직

길찾기 그래프(노드·간선)에서 **최단 경로를 계산하는 순수 알고리즘**을 담는다.
FastAPI·SQLAlchemy·Session을 모른다. 노드·간선 목록을 받아 결과만 돌려준다.

> `geo`(좌표/타일)와 별개 도메인이라 `domain`에서 갈라 나왔다.

---

## 구성 파일

| 파일 | 역할 | 핵심 심볼 |
|---|---|---|
| `dijkstra.py` | 다익스트라 최단 경로 | `ShortestPath`, `find_shortest_path` |
| `__init__.py` | 패키지 표식 | — |

---

## `dijkstra.py`

```python
@dataclass(frozen=True)
class ShortestPath:
    node_ids: tuple[str, ...]      # 방문 순서
    edge_ids: tuple[str, ...]      # 사용한 간선 순서
    total_distance_m: float        # 간선 거리 합


def find_shortest_path(nodes, edges, start_node_id, end_node_id) -> ShortestPath | None
```

동작:

- 입력 `nodes`/`edges`는 Iterable. 내부에서 `id → 객체` dict와 인접 리스트(`_build_graph`)로 바꿔 O(1) 조회.
- **표준 다익스트라 + heapq**. 같은 노드가 여러 거리로 큐에 들어갈 수 있어, 이미 더 짧은 거리가 확정된 오래된 후보는 건너뛴다.
- 목적지 확정 시 `_restore_path`가 `previous` 기록을 역추적해 정방향 경로로 복원.

계약(반환/예외):

| 상황 | 결과 |
|---|---|
| 경로 있음 | `ShortestPath` |
| 출발 == 도착 | 간선 없이 거리 0인 `ShortestPath` |
| 연결된 경로 없음 | `None` |
| 없는 출발/도착 노드 | `ValueError` |
| 음수 간선 거리 / 존재하지 않는 노드 참조 | `ValueError` |

- **간선 방향**: `bidirectional`이면 양방향으로 인접 리스트에 등록한다.
- **좌표를 다루지 않는다.** 경로 점을 wgs84로 옮기는 일은 `services/navigation_service.py`(+`geo`)가 한다. 여기서는 노드/간선 ID와 거리만.

---

## 의존성 방향

```
routing/dijkstra.py  ──►  (표준 라이브러리 heapq/math 만. app.models는 타입 힌트만)

services/navigation_service.py  ──►  routing.dijkstra.find_shortest_path
```

- routing은 가장 안쪽 순수 계층. 아무 계층에도 의존하지 않는다.
- `NavigationService`가 Session으로 노드·간선을 조회해 이 함수에 넘기고(N+1 없음), 결과 경로를 좌표로 후처리한다.

---

## 자주 하는 작업

| 하고 싶은 것 | 방법 |
|---|---|
| 알고리즘 교체(A* 등) | `find_shortest_path` 시그니처를 유지한 채 내부만 교체하거나, 같은 계약의 새 함수를 추가 |
| "경로 없음"과 "잘못된 노드" 구분 | `None`(경로 없음) vs `ValueError`(잘못된 입력) |
| 경로를 지도 좌표로 | 이 계층 밖 — `navigation_service` + `geo.tiling.local_points_to_lnglat` |
