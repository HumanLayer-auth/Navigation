# 백엔드 아키텍처 설계 (Navigation API)

> FastAPI 백엔드를 **어떻게 설계하고 무엇까지 책임지게 할지**를 확정하는 문서.
> 흩어져 있던 백엔드 방향([research/06-tech-stack.md](research/06-tech-stack.md) 3장,
> [research/09-rag-integration.md](research/09-rag-integration.md), [api/README.md](../api/README.md),
> [VERSION.md](../VERSION.md))을 한 곳으로 모으고, M1-002에서 만든 계층 골격을
> 마일스톤별로 어떻게 키울지의 단일 기준을 제공한다.

---

## 0. 이 프로젝트에서 백엔드의 위치

이 서비스의 **기술적 본체는 클라이언트(온디바이스 Dart)** 다. 센서 수집, PDR, Particle Filter,
heading 융합, 실내/외 전환, 경로 계산(A*/Dijkstra)은 전부 앱에서 돈다. 네트워크 없이도 측위가
동작하는 것이 "인프라 0" 차별점의 핵심이기 때문이다. → [research/06-tech-stack.md](research/06-tech-stack.md) 2장.

따라서 백엔드는 **얇게 설계한다.** 측위 연산을 백엔드로 끌어오지 않는다. 백엔드의 존재 이유는
아래 세 가지로 한정한다.

| # | 책임 | 왜 서버여야 하는가 |
|---|---|---|
| B1 | 건물·평면도 GeoJSON 서빙 | 데이터를 앱 번들과 분리해 코드 재배포 없이 교체·확장 |
| B2 | RAG 자연어 질의 (목적지 파싱 / 정보 Q&A) | 임베딩 모델·인덱스를 앱에 넣기 무겁고, 데이터 갱신이 잦음 |
| B3 | (선택) 상황 정보·평가 로그 수집 | 공사/폐쇄 등 운영 데이터, 데모 평가용 로그 취합 |

**하지 않는 것**: 실시간 위치 추적, Particle Filter, 경로 재탐색 루프. 이것들은 앱에 남긴다.

### 설계 원칙

1. **데모 안정성 최우선** — 오프라인/무 API 키로도 동작해야 한다. 외부 LLM API는 있으면 좋은
   기능이지 필수 경로가 아니다. RAG는 항상 폴백(별칭 검색)으로 성립한다.
2. **얇은 수직 슬라이스 우선** — 마일스톤마다 "요청 → 응답 → 화면"이 끝까지 도는 최소 기능을
   먼저 완성하고, 알고리즘 완성도는 뒤로 미룬다.
3. **경계는 넓게, 구현은 좁게** — 저장소·RAG는 인터페이스로 갈라두되(교체 가능), 초기 구현은
   메모리/파일 기반의 가장 단순한 형태로 시작한다.
4. **단일 컨테이너** — RAG를 별도 서비스로 쪼개지 않고 FastAPI 프로세스에 내장한다.
   운영 부담을 줄이고 배포를 하나로 유지한다.

---

## 1. 아키텍처 스타일: 계층형(Layered) + DI

M1-002에서 이미 채택한 **Router → Service → Repository → Domain** 계층 구조를 그대로 유지한다.
팀이 Spring Boot에 익숙하고, 저장소 교체(memory → SQL)를 코드 흐름 변경 없이 할 수 있기 때문이다.

```
HTTP 요청
   │
   ▼
┌───────────────────────────────────────────────────────────┐
│ Router (Controller)   app/routers/                         │
│  - URL ↔ 함수 매핑, 요청 파싱, 에러 → HTTP 상태코드 변환    │
│  - 비즈니스 로직 없음. Service에만 의존                     │
├───────────────────────────────────────────────────────────┤
│ Service               app/services/                        │
│  - 유스케이스 로직. Repository 인터페이스에만 의존          │
│  - 도메인 객체를 조회·가공해 응답 형태로 반환               │
├───────────────────────────────────────────────────────────┤
│ Repository (Protocol) app/repositories/                    │
│  - 저장소 계약. 구현체: Memory → (확장 시) SQL              │
├───────────────────────────────────────────────────────────┤
│ Domain                app/domain/                          │
│  - 순수 파이썬 객체(dataclass). 스키마(Pydantic)와 분리     │
└───────────────────────────────────────────────────────────┘
        ▲
        │  DI wiring  app/core/dependencies.py
```

### 의존 방향 규칙 (반드시 지킨다)

- Router는 **Service만** 의존한다. Repository를 직접 부르지 않는다.
- Service는 **Repository 인터페이스(Protocol)만** 의존한다. 구현체(Memory/SQL)를 몰라야 한다.
- Domain은 아무 계층도 의존하지 않는다. Pydantic 스키마와도 분리한다.
- 구현체 선택과 결선은 **오직 `core/dependencies.py`** 에서만 한다. 여기만 바꾸면 저장소가 교체된다.

이 규칙 덕분에 테스트에서 `app.dependency_overrides`로 가짜 저장소를 꽂아 서비스 로직을 격리 검증할 수 있다.

---

## 2. 목표 디렉토리 구조

현재(M1-002) 구조를 유지하면서 RAG·설정·상황 데이터를 얹는 목표 형태다. 한 번에 다 만들지 않고
마일스톤별로(8장) 필요한 부분만 추가한다.

```
api/
├─ app/
│  ├─ main.py                  # FastAPI 인스턴스, 미들웨어, 라우터 등록, lifespan
│  ├─ core/
│  │  ├─ config.py             # (추가) pydantic-settings 기반 환경설정
│  │  ├─ dependencies.py       # DI 결선 (구현체 선택은 여기서만)
│  │  ├─ errors.py             # (추가) 공통 에러 스키마 / 예외 핸들러
│  │  └─ lifespan.py           # (추가) 시작 시 데이터 로딩·RAG 인덱스 빌드
│  ├─ routers/                 # Controller
│  │  ├─ health.py             # (분리) GET /health
│  │  ├─ buildings.py          # 건물/층/상황
│  │  └─ query.py              # RAG 질의
│  ├─ services/                # 유스케이스 로직
│  │  ├─ building_service.py
│  │  └─ rag/                  # (추가) RAG 서브시스템 (6장)
│  │     ├─ rag_service.py     #   파이프라인 오케스트레이션 (인터페이스)
│  │     ├─ indexer.py         #   POI/문서 → 검색 코퍼스
│  │     ├─ retriever.py       #   별칭 매칭 / 임베딩 유사도
│  │     └─ generator.py       #   (선택) LLM 재랭킹·문장 생성
│  ├─ repositories/            # 저장소 계약 + 구현
│  │  ├─ building_repository.py        # Protocol
│  │  ├─ memory_building_repository.py # 1차 구현 (파일 로딩)
│  │  └─ sql_building_repository.py    # (확장) PostgreSQL/PostGIS
│  ├─ domain/                  # 순수 도메인 객체
│  │  ├─ building.py
│  │  ├─ poi.py                # (추가) POI (RAG·경로 그래프 공용)
│  │  └─ route_graph.py        # (추가) node/edge
│  ├─ schemas/                 # Pydantic 요청/응답 모델
│  │  ├─ building.py
│  │  └─ query.py              # (추가) RAG 요청/응답 스키마
│  └─ data/                    # 1차 데이터 소스 (정적 GeoJSON)
│     └─ sample_building.json
├─ tests/                      # pytest (Given/When/Then, DI override)
├─ Dockerfile                  # (추가) python:3.12-slim
└─ requirements.txt
```

---

## 3. 데이터 소스 전략

**1차: 정적 GeoJSON 파일 → 메모리.** `MemoryBuildingRepository`가 앱 시작 시
`app/data/sample_building.json`을 `Building` 도메인 객체로 읽어 메모리에 보관한다(현재 구현).
`@lru_cache`로 프로세스 수명 동안 재사용한다.

**확장: SQL(PostgreSQL/PostGIS).** 데이터가 커지거나 다건물·편집이 필요해지면
`BuildingRepository` Protocol을 구현하는 `SqlBuildingRepository`를 추가하고
`dependencies.py`의 결선 한 줄만 바꾼다. **서비스·라우터·테스트는 손대지 않는다.**

```python
# core/dependencies.py — 저장소 교체는 여기서만
@lru_cache
def get_building_repository() -> BuildingRepository:
    return MemoryBuildingRepository()      # 확장 시: SqlBuildingRepository(engine)
```

- 평면도 GeoJSON이 **모든 기능(렌더링·경로·Particle Filter·RAG)의 단일 진실 소스**다.
  스키마는 M2-001에서 확정한다(`wall/corridor/door/poi/node/edge` + POI `aliases`).
- POI의 `aliases`는 그대로 RAG 검색 입력이 되므로, 데이터 단계에서 동의어/다국어 별칭을 채운다.

---

## 4. 도메인 모델

Pydantic 스키마(입출력 검증)와 도메인 객체(내부 로직)를 **분리**한다. SQL 모델이 나중에 생겨도
서비스는 도메인 객체 기준으로 동작하게 하기 위함이다.

| 도메인 객체 | 핵심 필드 | 쓰임새 |
|---|---|---|
| `Building` | `id, name, floors, floor_data, entrances` | 건물 메타 + 층별 GeoJSON |
| `POI` | `id, name, floor, category, aliases, geometry` | 목적지 후보. 경로 그래프·RAG 공용 |
| `RouteGraph` | `nodes, edges(가중치)` | 층 그래프. 서버는 서빙, 계산은 클라이언트 |

> 경로 **계산**은 클라이언트(`route_planner.dart`, M2-003)가 담당한다. 서버는 node/edge를
> GeoJSON으로 **서빙만** 한다. 오프라인에서도 길찾기가 되어야 하므로 계산을 서버에 두지 않는다.

---

## 5. 엔드포인트 계약 (REST)

FastAPI + REST 조합이면 이 규모에 충분하다(GraphQL 불필요). 경로는 자원 중심으로 설계한다.

| 메서드 | 경로 | 설명 | 도입 |
|---|---|---|---|
| GET | `/health` | 서버 생존 확인 | M1 (완료) |
| GET | `/buildings` | 건물 목록(요약, 무거운 floor_data 제외) | M1 (완료) |
| GET | `/buildings/{id}` | 건물 메타 + 입구 좌표 | M1 (완료) |
| GET | `/buildings/{id}/floors/{floor}` | 해당 층 평면도 GeoJSON | M1 (완료) |
| POST | `/query/destination` | 자연어 → 목적지 POI + 후보 | M5 (현재 stub) |
| POST | `/query/info` | 건물 정보 Q&A | M5 (현재 stub) |
| GET | `/buildings/{id}/status` | 공사·폐쇄 등 구간 상황 | M5 (선택) |

### 응답·에러 규약

- 조회 실패(없는 건물/층)는 Service가 `None`을 반환하고, Router가 `404`로 변환한다(현재 패턴 유지).
- 요청 스키마 위반은 FastAPI/Pydantic이 자동으로 `422`를 낸다.
- 에러 응답은 `{"detail": "..."}` 형태로 일관되게 유지한다. 공통 예외 핸들러는 `core/errors.py`에 둔다.
- RAG 응답은 항상 `{ poi, candidates, message }` 3필드 계약을 지킨다(결과 없음도 이 형태로).

```json
// POST /query/destination  요청
{ "text": "3층 화장실 어디야", "building_id": "b001", "current_floor": 2 }

// 응답 (정상)
{ "poi": { "name": "남자화장실", "floor": 3, "x": 12.4, "y": 33.1 },
  "candidates": [],
  "message": "3층 남자화장실로 안내합니다." }

// 응답 (애매 → 후보 반환)
{ "poi": null,
  "candidates": [ { "name": "여자화장실", ... }, { "name": "남자화장실", ... } ],
  "message": "화장실 후보가 여러 개예요. 하나를 선택해주세요." }
```

---

## 6. RAG 서브시스템 설계

RAG는 백엔드에서 가장 복잡한 부분이므로 **`services/rag/` 안에 격리**하고, 라우터는 내부를 모른 채
`RagService` 인터페이스만 호출한다. 파이프라인은 세 단계다.

```
질의 텍스트
   │
   ▼  Indexer (시작 시 1회)      POI name/aliases/category/floor → 검색 코퍼스
   ▼  Retriever                  코퍼스에서 Top-k 후보 선별
   ▼  Generator (선택)           LLM 재랭킹 / 안내 문장 생성
   ▼
{ poi, candidates, message }
```

### 성능이 아니라 "폴백 사다리"로 설계한다

데모 안정성을 위해 **아래 단계 없이도 위 단계만으로 항상 답이 나오게** 한다. `RAG_MODE` 환경변수로
어디까지 켤지 고른다.

| 모드 | Retriever | Generator | 의존성 | 특징 |
|---|---|---|---|---|
| `lite` (기본) | 별칭 정확/부분 매칭 | 없음(템플릿 문장) | 없음 | 오프라인·무 API 키. **데모 기본값** |
| `embedding` | sentence-transformers 코사인 유사도 + FAISS | 없음 | 모델 파일 | 의미 검색. 오타·유사어 대응 |
| `llm` | 위 + Top-k | Claude Haiku 재랭킹·문장 | API 키 | 최고 품질, 네트워크 필요 |

- 인덱스와 모델은 **시작 시 1회 로딩**(FastAPI `lifespan`)하고 프로세스 내에서 재사용한다.
  요청마다 로딩하지 않는다.
- `embedding`/`llm` 초기화에 실패하면 **자동으로 `lite`로 강등**하고 경고 로그만 남긴다. 서버는 죽지 않는다.
- 벡터 DB는 FAISS를 FastAPI 프로세스에 내장한다(별도 서버 없음). 규모가 커지면 옵션 B(Qdrant)로 확장.

M5-001의 축소 지침("시간이 부족하면 별칭 검색 + 후보 랭킹으로")이 곧 `lite` 모드이며, 이 설계는
그 지침을 아키텍처로 못박은 것이다.

---

## 7. 횡단 관심사 (Cross-cutting)

| 관심사 | 설계 | 위치 |
|---|---|---|
| **설정** | `pydantic-settings`로 환경변수 로딩. `CORS_ORIGINS`, `DATA_DIR`, `RAG_MODE`, `LLM_API_KEY` | `core/config.py` |
| **CORS** | 개발은 `*`, 운영은 앱 도메인으로 좁힘. 설정값으로 주입 | `main.py` |
| **시작 훅** | `lifespan`에서 GeoJSON 로딩 + RAG 인덱스 빌드. 준비 실패 시 안전 강등 | `core/lifespan.py` |
| **에러 처리** | 도메인은 `None`/예외, 라우터·핸들러가 HTTP로 변환. 일관된 `detail` 스키마 | `core/errors.py` |
| **로깅** | 구조화 로그(요청 id·경로·소요). M5-002 평가 로그는 별도 CSV 싱크 | `core/` |
| **보안(데모 범위)** | 인증 없음. 단, `LLM_API_KEY`는 **환경변수로만** 주입하고 코드/리포에 넣지 않는다 | env |

> 데모 범위에서 인증·레이트리밋은 과설계다. "향후 과제"로 남기고 지금은 넣지 않는다.

---

## 8. 마일스톤별 진화 (얇은 수직 슬라이스)

백엔드를 한 번에 완성하지 않는다. 각 단계는 앞 단계의 계약을 깨지 않고 얇게 얹는다.

| 단계 | 백엔드가 하는 일 | 산출물 |
|---|---|---|
| **M1 (완료)** | 계층 골격 + CORS + `/health`, `/buildings/*`, `/query/*` stub | 현재 `api/` |
| **M2-001** | GeoJSON 스키마 확정, 실제 데모 건물 데이터, 세 조회 엔드포인트가 새 스키마 반환 | `data/`, `domain/poi.py`, `route_graph.py` |
| **M2-003** | node/edge를 GeoJSON으로 서빙(계산은 클라이언트) | 스키마 정리 |
| **M5-001** | `/query/destination` stub → 실제 구현(`lite` 우선). `services/rag/` 신설 | RAG 서브시스템 |
| **M5(선택)** | `/query/info`, `/buildings/{id}/status`, 평가 로그 싱크 | 상황 데이터·로그 |

**지금 당장 손댈 코드**: 없음(구조는 이미 맞다). 이 문서는 M2-001부터의 확장을 이 설계에 맞추기
위한 기준선이다.

---

## 9. 배포 · 운영

| 항목 | 결정 |
|---|---|
| 이미지 | `python:3.12-slim` 기반 단일 이미지. RAG 내장(별도 서비스 없음) |
| 실행 | `uvicorn app.main:app` — 포트 `8000` |
| 태그 | `navigation/api:<프로젝트 버전>` ([VERSION.md](../VERSION.md) 규칙) |
| 배포 | 시연용 경량 호스팅(Railway / Fly.io) 또는 로컬 |
| 설정 | 전부 환경변수(`RAG_MODE`, `CORS_ORIGINS`, `LLM_API_KEY`, `DATA_DIR`) |

`embedding`/`llm` 모드는 모델·의존성 때문에 이미지가 무거워지므로, **데모 기본 이미지는 `lite`** 로
빌드하고 필요 시에만 상위 모드를 켠다.

---

## 10. 테스트 전략

M1-002에서 확립한 **pytest + `httpx.TestClient` + DI override + Given/When/Then** 패턴을 유지한다.

- **단위**: 가짜 Repository로 Service 로직 격리 검증. RAG는 fixture POI로 Retriever 랭킹 검증
  (정상 매칭 / 후보 다수 / 결과 없음 세 케이스 — M5-001 수용 기준).
- **계약**: 엔드포인트별 상태코드·응답 스키마 검증. 404(없는 건물/층), 422(스키마 위반) 포함.
- **격리**: 각 테스트는 함수 스코프 fixture로 `dependency_overrides`와 repository 캐시를 비우고 시작·종료한다.

---

## 11. 결정 요약 · 미결정 사항

### 확정

1. 백엔드는 얇게. 측위는 온디바이스, 백엔드는 **데이터 서빙 + RAG**만.
2. 계층형(Router/Service/Repository/Domain) + DI 유지. 저장소 교체는 `dependencies.py`에서만.
3. 데이터: 정적 GeoJSON→메모리 시작, Protocol로 SQL 확장 여지 확보.
4. 경로 **계산은 클라이언트**, 서버는 node/edge 서빙.
5. RAG는 `services/rag/`에 격리, **폴백 사다리(`lite`→`embedding`→`llm`)** 로 항상 오프라인 성립.
6. 단일 컨테이너, 환경변수 설정, 데모 기본 모드 `lite`.

### 아직 정할 것

- SQL 도입 시점 임계치(데이터 규모·다건물 필요 여부).
- `embedding` 모드 임베딩 모델 확정(다국어 MiniLM 계열 후보).
- `/buildings/{id}/status`·평가 로그를 M5 범위에 넣을지(시간에 따라 조정).

---

_이 문서는 백엔드 설계 결정의 단일 기준이다. 결정이 바뀌면 여기를 먼저 고치고,
큰 변경은 [../HISTORY.md](../HISTORY.md)에 한 줄 남긴다. 스택 버전은 [../VERSION.md](../VERSION.md)가 단일 출처다._
</content>
</invoke>
