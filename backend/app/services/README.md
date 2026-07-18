# `app/services` — 비즈니스 규칙 / 유스케이스 조립

여러 계층을 **조합·계산**하는 흐름을 담는다. 단순 조회로 안 끝나고
"DB에서 읽어 → 순수 알고리즘 실행 → 결과를 좌표로 후처리"처럼 여러 단계를 엮을 때 만든다.

> 단순 조회는 여기 두지 않는다(그건 `repositories/`). 조합·계산이 있을 때만 Service를 만든다.

---

## 구성 파일

| 파일 | 역할 | 핵심 |
|---|---|---|
| `navigation_service.py` | 최단 경로 유스케이스 | `NavigationService.get_shortest_path`, `get_building_shortest_path` |
| `__init__.py` | 패키지 표식 | — |

---

## `NavigationService`

```python
NavigationService(session).get_shortest_path(building_id, floor_name, start, end)
NavigationService(session).get_building_shortest_path(building_id, start, end)
```

한 요청에서 하는 일(조합):

1. **조회** — 층(또는 건물 전체) 범위의 Node·Edge를 각각 한 번씩 `select` (N+1 없음).
2. **탐색** — `routing.dijkstra.find_shortest_path`에 넘겨 순수 계산.
3. **후처리** — 경로 간선의 geometry를 진행 방향에 맞춰 하나의 선으로 잇고(`_build_path_points`), `repositories.geo_transform` + `geo.tiling`으로 wgs84 좌표를 얹는다.

두 메서드 차이:

- `get_shortest_path`: **한 층 안**. `floor_id`로 필터한 간선만.
- `get_building_shortest_path`: **건물 전체**. 층 내부 간선 + `floor_id IS NULL`인 수직 전이 간선을 함께 싣어 층을 넘나든다. 모든 층이 건물 공통 프레임으로 정규화돼 적재되므로(`scripts/transform/floor_alignment`) 건물 변환 하나로 전체 경로를 wgs84로 옮긴다.

계약(반환):

| 상황 | 결과 |
|---|---|
| 경로 있음 | `{"path_found": True, "node_ids", "edge_ids", "path_points", "path_points_wgs84", "total_distance_m", ...}` |
| 없는 건물/층 | `None` (→ 라우터 404) |
| 경로 없음 | `{"path_found": False, ...}` (→ 라우터 404) |
| 잘못된 노드 | `ValueError` (dijkstra가 발생 → 라우터 400) |

- **HTTP/FastAPI 타입을 모른다.** 상태 코드 변환은 `routers/`가 한다.

---

## 의존성 방향

```
services/navigation_service.py
    ──►  models (Node/Edge/Floor 조회)
    ──►  routing.dijkstra (순수 탐색)
    ──►  geo.tiling (경로 점 wgs84 변환)
    ──►  repositories.geo_transform (건물 변환 피팅)

routers/buildings.py  ──►  NavigationService
```

- Service는 아래 계층(models·routing·geo·repositories)을 조합하고, 위(routers)가 Service를 호출한다.

---

## 자주 하는 작업

| 하고 싶은 것 | 방법 |
|---|---|
| 경로 계산 규칙 변경 | `NavigationService` 내부(간선 로딩 범위·후처리). 알고리즘 자체는 `routing/` |
| 새 유스케이스(여러 조회 조합) | 새 Service 메서드/클래스. 단순 1:1 조회면 `repositories/`로 |
| N+1 의심 | 관계 순회 대신 범위 `select` 한 번으로 로딩하는 패턴 유지 |
