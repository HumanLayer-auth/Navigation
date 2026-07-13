# 실행용 라우팅 API 진행 계획 (좌표 스냅 · 좌표 기반 경로 · 목적지 해석)

> 목적: "출발/도착점을 받아 실제로 길찾기를 실행"하는 데 **API 쪽에서 무엇을
> 더 만들어야 하는지**를 코드/데이터로 검증해 정리하고, 착수 전에 **결정이
> 필요한 질문**을 나열한다.
>
> 역할 분담 결정(합의됨): **경로 폴리라인을 그리고 부드럽게(스무딩) 하는 일은
> Flutter 프론트에서 한다.** 따라서 API는 "그래프 상의 경로 좌표열(path_points)"
> 까지만 책임지고, 렌더링/코너 라운딩/스플라인은 클라이언트 몫이다.

---

## 0. 코드 검증 요약 — 지금 이미 되어 있는 것

| 항목 | 상태 | 근거 |
|---|---|---|
| 노드 ID 기반 최단경로 | ✅ 있음 | `GET /buildings/{id}/floors/{floor}/route?start_node_id=&end_node_id=` (`routers/buildings.py`, `navigation_service.py`, `domain/dijkstra.py`) |
| 층 그래프 조회 | ✅ 있음 | `GET .../floors/{floor}/graph` → nodes/edges |
| 매장 검색 | ✅ 있음 | `GET /buildings/{id}/stores?q=` → `StoreResponse` |
| **매장 → 진입 노드 매핑** | ✅ **데이터에 존재** | `Store.entrance_node_id` FK가 시드(`navigation_1f.json`)에 `store_entrance_000…`로 채워져 있음. `StoreResponse`가 `entrance_node_id`, `floor_id`, `entrance_local_m`를 이미 반환 |
| 노드 타입 | corridor / store_entrance / elevator / escalator | `generate_navigation_floors.py` |

**결론:** "도착점"은 매장 검색이 이미 `entrance_node_id + floor_id`를 주므로
정확/부분일치 범위에서는 **추가 구현 없이** 도착 노드를 얻을 수 있다.

## 0-1. 없는 것 (이번에 만들 것)

1. **임의 좌표 → 그래프 스냅** (nearest-node 또는 nearest-edge-point). PDR/GPS가
   주는 `(x_m, y_m)`은 노드가 아니므로 route를 못 태운다.
2. **좌표 기반 route** — 출발 좌표(+도착 노드/좌표)를 받아 내부에서 스냅 후 경로 반환.
3. (선택) **자연어 목적지 해석** — `/query/destination` stub 채우기. RAG 필요, 후순위.

---

## 작업 ① 출발점 좌표 스냅 (nearest 처리)

### 목표
`(x_m, y_m, floor)` → 그래프에서 경로를 시작할 지점.

### 설계 후보
- **A. 최근접 노드(nearest node):** 모든 노드 중 유클리드 거리 최소 노드 반환. 단순.
- **B. 최근접 간선 위 지점(nearest point on edge):** 각 간선 geometry 선분에 수직
  투영 → 가장 가까운 선분 위 점 + 그 간선을 반환. 정확하지만 다익스트라가 노드
  기반이라 "간선 중간에서 출발"을 표현하려면 임시 노드 삽입 또는 양끝 노드 중
  가까운 쪽으로 근사해야 함.

### 검증 결과
- 노드는 복도 loop를 추적해 만든 corridor 노드 + store_entrance 노드로 구성. 촘촘하지만
  균일하진 않음 → **A(최근접 노드)** 만 쓰면 실제 위치와 스냅 지점이 수 m 벌어질 수 있음.
- 좌표계는 건물 전역 `local_m`, **층 단위로 필터**해야 함(`Node.floor_id`).

### 인터페이스(안)
```
GET /buildings/{id}/floors/{floor}/nearest-node?x=..&y=..
→ { node_id, node_point:{x,y}, offset_m }         # offset_m = 실제 좌표와 스냅점 거리
```

### 결정 질문 → Q1, Q2, Q3 (아래 종합)

---

## 작업 ② 좌표 기반 route (by-point)

### 목표
Flutter가 "현재 위치(좌표) → 목적지"를 한 번에 요청.

### 인터페이스(안)
```
POST /buildings/{id}/floors/{floor}/route/by-point
body: { start: {x, y}, end_node_id: "store_entrance_007" }
      # 또는 end: {x, y}  (도착도 좌표로 줄 경우)
→ RouteResponse 와 동일 + { start_snap:{node_id, offset_m} }
```

### 설계
- 내부적으로 작업①의 스냅으로 `start_node_id`를 구하고 기존
  `NavigationService.get_shortest_path`를 재사용. 새 알고리즘 없음.
- 응답의 `path_points`는 **그래프 노드 기준 폴리라인 그대로** 반환(스무딩 X — 프론트 담당).
- 실제 위치→스냅 노드 사이 "진입 구간"을 path_points 맨 앞에 붙일지는 **결정 질문 Q4**.

### 결정 질문 → Q4, Q5

---

## 작업 ③ 목적지 해석

### 현 상태로 충분한 부분
- 정확/부분일치: `GET /buildings/{id}/stores?q=텍스트` → `entrance_node_id`+`floor_id`.
  Flutter가 이 값을 그대로 `end_node_id`로 사용 가능. **추가 API 불필요.**

### 확장(선택)
- 자연어("편의점 어디야") → `/query/destination` stub을 채워 매장/카테고리 검색 + 노드 반환.
  현재 요청 body에 `floor`가 없고 building 전역이라, **여러 층 결과 중 무엇을 고를지**
  규약이 필요(가까운 층? 같은 층 우선?). RAG(sentence-transformers+FAISS)는 별도 이슈.

### 결정 질문 → Q6

---

## 전체 진행 순서(제안)

1. ① nearest-node 쿼리 + 유닛테스트 (좌표 → 노드, offset 계산)
2. ② by-point route (①을 재사용) + 통합테스트
3. 검증: 시드 DB로 실제 요청 → path_points가 기존 node 기반 route와 일치하는지 대조
4. (선택) ③ 자연어 목적지 — RRAG는 후속 이슈로 분리

각 단계마다 기존 테스트(`tests/integration/test_route_api.py`,
`tests/unit/test_dijkstra.py`) 회귀 확인.

---

## 결정이 필요한 질문 종합

- **Q1. 스냅 대상:** 최근접 "노드"만으로 충분한가, 아니면 "간선 위 지점"까지
  정확히 스냅해야 하나? (정확도 vs 구현 복잡도)
- **Q2. 스냅 노드 종류 제한:** 출발 스냅을 corridor 노드에만 붙일까, store_entrance
  같은 노드에도 붙게 둘까? (엉뚱하게 매장 진입점에서 출발하는 것 방지)
- **Q3. 스냅 실패/과대 offset 처리:** 가장 가까운 노드가 너무 멀면(예: 벽 너머,
  offset > N m) 에러로 볼지, 그냥 반환할지. 임계값 N은?
- **Q4. 진입 구간 포함 여부:** `path_points` 맨 앞에 "실제 좌표 → 스냅 노드" 직선
  구간을 넣을까, 아니면 스냅 노드부터 시작할까? (Flutter가 현재 위치 점을 따로
  그린다면 불필요)
- **Q5. 도착점 입력형:** by-point에서 도착은 `end_node_id`만 받을까(매장 검색 결과
  사용), 좌표도 허용할까?
- **Q6. 자연어 목적지 범위:** 이번에 `/query/destination`을 실제로 채울지, 아니면
  프론트가 `/stores?q=`로 대체하고 자연어/RAG는 후속 이슈로 뺄지?
- **Q7. 다층 경로:** 지금 route는 **단일 층** 전제(간선/노드가 floor_id로 묶임).
  출발-도착이 다른 층이면 엘리베이터/에스컬레이터 환승 경로가 필요한데, 이번
  범위에 포함할지 별도 이슈로 뺄지? (현재 코드엔 층간 연결 로직 없음)

---

## 참고 파일
- `api/app/routers/buildings.py` — 경로/그래프 엔드포인트
- `api/app/services/navigation_service.py` — 경로 조립(`_build_path_points`)
- `api/app/domain/dijkstra.py` — 최단경로
- `api/app/schemas/route.py`, `api/app/schemas/floor_map.py` — 응답 스키마
- `api/app/models/navigation.py`, `api/app/models/place.py` — Node/Edge/Store/Poi
- `api/scripts/generate_navigation_floors.py` — 그래프·간선 geometry 생성(A*+RDP)
