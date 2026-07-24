# `client` — Flutter 앱 구조

실외(GPS·지도)에서 실내(층 지도·경로 안내)까지 이어지는 내비게이션 앱. **백엔드는
그래프·매장·지도 데이터만 주고, 최단 경로 계산과 실내 측위(PDR)는 앱이 온디바이스로**
수행한다. 서버 왕복 없이 이미 받아둔 그래프로 즉시 반응하기 위해서다.

> 실행법은 루트 [README](../README.md)·[로컬 개발 가이드](../docs/guide/local-development-guide.md).
> 이 문서는 `lib/` 코드 구조를 설명한다.

## 계층

| 디렉토리 | 역할 |
|---|---|
| `main.dart` · `app.dart` | 진입점. 앱 라이프사이클(백/포그라운드 → PDR 세션 제어) |
| `core/` | 전역 배선. `service_locator.dart`(DI 싱글턴), `api_config.dart`(API 주소·키·데모 건물) |
| `routing/` | 라우트 정의(`app_routes.dart`) |
| `screens/` | 화면. 실외·실내 지도, 목적지 검색, 경로 안내, 도착, 디버그 |
| `widgets/` | 재사용 UI. 지도(`floor_plan_view`)·경로선(`route_polyline`)·시트·마커·바 |
| `features/indoor_navigation/` | **PDR 실내 측위**. `application`(컨트롤러·매처) · `contract`(MVI 계약) · `platform`(Android/iOS 센서) · `debug` |
| `features/debug_mode/` | 개발용 오버레이(격자·보정·토스트) |
| `repositories/` | 백엔드·외부 API 접근. **인터페이스 + `Http`/`Mock` 구현** |
| `models/` | 응답 JSON 파싱 DTO(`building`·`floor_graph`·`indoor_route`…) |
| `domain/` | **순수 로직**. `dijkstra`·`floor_router`(경로 계산)·`geo_transform`(좌표 변환) |
| `state/` | `favorites_controller`(장소 즐겨찾기, SharedPreferences) |
| `theme/` | 앱 테마 |

## 계층 의존 (전체 그림)

```mermaid
flowchart TD
    subgraph entry["진입 · 배선"]
        MAIN["main.dart · app.dart<br/>진입점 · 라이프사이클"]
        SL["core/service_locator.dart<br/>전역 DI(싱글턴 주입)"]
        ROUTES["routing/app_routes.dart"]
    end

    subgraph ui["화면 · UI"]
        SCREENS["screens/*<br/>outdoor · indoor · destination<br/>route_guide · arrival"]
        WIDGETS["widgets/*<br/>지도 · 시트 · 마커 · 경로선"]
    end

    subgraph pdr["features/indoor_navigation (PDR)"]
        CTRL["application/<br/>controller · matcher"]
        CONTRACT["contract/ (MVI 계약)"]
        PLATFORM["platform/<br/>android · ios 센서"]
    end

    subgraph data["데이터 · 로직"]
        REPO["repositories/*<br/>interface + Http/Mock"]
        MODELS["models/*<br/>응답 파싱 DTO"]
        DOMAIN["domain/*<br/>dijkstra · floor_router · geo_transform"]
    end

    BE[("백엔드 FastAPI")]
    EXT[("TMAP · VWorld")]

    MAIN --> SL
    MAIN --> ROUTES --> SCREENS
    SL -. "싱글턴 주입" .-> REPO
    SCREENS --> WIDGETS
    SCREENS --> REPO
    SCREENS --> PDR
    REPO --> MODELS
    REPO --> BE
    REPO --> EXT
    REPO -. "navigation_graph" .-> DOMAIN
    SCREENS --> DOMAIN
    PLATFORM --> CTRL --> CONTRACT

    classDef e fill:#264653,color:#fff,stroke:none
    classDef c fill:#2a9d8f,color:#fff,stroke:none
    classDef s fill:#e9c46a,color:#212529,stroke:none
    class MAIN,SL,ROUTES e
    class SCREENS,WIDGETS,REPO,MODELS,DOMAIN,CTRL,CONTRACT,PLATFORM c
    class BE,EXT s
```

핵심은 두 가지다.

- **화면은 백엔드를 직접 모른다.** `repositories/`(인터페이스)만 알고, 실제 HTTP는
  `Http*Repository`가 담당한다. `core/service_locator.dart`가 어떤 구현을 쓸지 한 곳에서 주입한다.
- **경로 계산은 `domain/`이 온디바이스로 한다.** 리포지토리가 받아온 `navigation_graph`를
  `domain/floor_router`(→ `dijkstra`)에 넘겨 경로를 만든다. 서버는 그래프만 준다.

## 전형적 사용자 여정 (라우트)

```mermaid
flowchart LR
    OUT["/ (outdoor_map)<br/>실외 지도 · GPS"] --> DEST["/destination<br/>목적지 검색"]
    DEST --> RG["/route-guide<br/>경로 안내"]
    RG --> IN["/indoor-map<br/>실내 지도 · PDR"]
    IN --> ARR["/arrival<br/>도착"]
```

`map_shell`이 지도 화면 셸을 감싸고, `screens/debug/*`는 개발용(헬스체크·층지도 미리보기·PDR 테스트)이다.

## 목적지 검색 → 경로 안내 데이터 흐름

```mermaid
sequenceDiagram
    participant U as 사용자
    participant S as 화면(destination/route_guide)
    participant DR as destinationRepository
    participant BR as buildingRepository
    participant FR as domain/floor_router
    participant BE as 백엔드

    U->>S: 매장 검색어 입력
    S->>DR: searchDestinations(text)
    DR->>BE: POST /query/destination
    BE-->>DR: match{store, entrance_node_id, floor}
    S->>BR: getShortestRoute(floor, start, end)
    BR->>BE: GET /buildings/{id}/floors/{floor}
    Note over BR: 응답의 navigation_graph를 층별 캐시
    BR->>FR: computeShortestRoute(graph, start, end)
    FR-->>BR: IndoorRoute(폴리라인 · 거리)
    BR-->>S: IndoorRoute
    S->>U: route_polyline 렌더
```

## 백엔드·외부 연동 지점

| 리포지토리 | 대상 | 사용 API |
|---|---|---|
| `HttpBuildingRepository` | 백엔드 | `GET /buildings`, `/floors/{floor}`(지도+`navigation_graph`), `/floors/{floor}/graph` |
| `HttpDestinationRepository` | 백엔드 | `POST /query/destination` (경량 검색) |
| `TmapDirectionsRepository` | TMAP | 실외 보행자 경로 |
| `Mock*Repository` | 없음 | 오프라인·위젯 테스트용 대체 구현 |

## DI · 교체 패턴 (`core/service_locator.dart`)

전역 변수로 싱글턴을 주입하고, **테스트·오프라인에서는 그 변수만 Mock으로 교체**한다.

- `buildingRepository = HttpBuildingRepository()` — 오프라인 확인 시 `MockBuildingRepository()`로.
- `destinationRepository = MockDestinationRepository(...)` — 현재 Mock. 백엔드 검색을 붙이려면 `HttpDestinationRepository`로.
- `directionsRepository` — `--dart-define=TMAP_APP_KEY=…`가 있으면 실제 TMAP, 없으면 직선 Mock.
- `pdrMotionSource` / `indoorNavigationDriver` — 화면이 바뀌어도 센서 세션을 유지하는 싱글턴.

API 주소는 `core/api_config.dart`가 플랫폼별 기본값을 고르고(`--dart-define=API_BASE_URL=…`로 덮어씀).

## 온디바이스로 도는 것 (서버에 없음)

- **경로 계산**: `domain/dijkstra.dart`(최단 경로) + `domain/floor_router.dart`(→ 지도용 폴리라인).
- **좌표 변환**: `domain/geo_transform.dart`(`local_m` ↔ WGS84).
- **실내 측위(PDR)**: `features/indoor_navigation/`. 기기 센서로 위치를 추정해 지도 마커·경로에 반영.

## 현재 상태 / 남은 연동

- **목적지 검색은 `/query/destination`(경량)만 사용**한다. FAISS 자연어(`/query/ai`)는 백엔드에
  있으나 미연동 → [AI 질의 인수인계](../docs/backend/native/client-handoff.md).
- **경로는 단일 층 안에서만** 계산된다(`getShortestRoute`가 층별 그래프 사용). 층 간 이동
  (엘리베이터·에스컬레이터)은 미연동 → [층 간 라우팅 인수인계](../docs/backend/navigate/client-handoff.md).

## 자주 하는 작업

| 하고 싶은 것 | 위치 |
|---|---|
| API 주소 바꾸기 | `--dart-define=API_BASE_URL=…` (또는 `core/api_config.dart`) |
| Mock ↔ 실제 백엔드 전환 | `core/service_locator.dart`의 리포지토리 변수 |
| 화면·라우트 추가 | `screens/` + `routing/app_routes.dart` |
| 백엔드 응답 파싱 | `models/` |
| 경로/좌표 로직 | `domain/` |
| 실내 측위(PDR) 손보기 | `features/indoor_navigation/` |
