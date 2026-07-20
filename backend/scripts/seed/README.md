# `scripts/seed` — DB 적재/초기화 CLI

개발 SQLite DB를 **비우고 다시 만들고, Studio 데이터를 적재**하는 명령들.
FastAPI 서버 startup에서는 절대 호출하지 않는다 — 초기화는 이 CLI로만 한다.

> `transform/`(파일→파일 순수 변환)과 달리 이 계층은 **DB(Session)를 건드린다.**

---

## 구성 파일

| 파일 | 역할 | 진입점 |
|---|---|---|
| `reset_and_seed.py` | 초기화 + 시드 한 번에 | `python -m scripts.seed.reset_and_seed` |
| `reset_database.py` | 테이블 drop & create | `reset_database()` |
| `studio_adapter.py` | Studio JSON → ORM 적재 | `seed_studio()` / `python -m scripts.seed.studio_adapter` |
| `seed_navigation.py` | 표준 dict → ORM 객체 추가 | `add_dataset`, `add_transfer_edges` |
| `__init__.py` | 패키지 표식 | — |

---

## 실행 흐름

```
reset_and_seed.reset_and_seed_studio()
├─ reset_database()                     # 모든 테이블 drop → ORM 정의대로 create
└─ studio_adapter.seed_studio()         # 전 층 + 층 간 전이 간선을 한 트랜잭션으로 적재
   └─ (층마다) build_seed_dict()        #   transform/vertical_transfers 사용
      └─ seed_navigation.add_dataset()  #   Building·Floor·Node·Edge·Store·Poi 를 Session에 추가
```

- **입력은 `resources/studio/thehyundai-seoul-dabeeo/`의 층 JSON** (`{층}.json`, `stores_{층}.json`, 현재 B6~6F 12개 층). 층 목록은 `studio_adapter.discover_floor_codes`가 디렉토리에서 찾고 기준층(1F)을 맨 앞에 둔다.
- **전 층이 한 좌표 프레임을 공유한다는 것이 전제.** 백엔드는 건물당 `local_m -> wgs84` 변환을 하나만 피팅하므로(`repositories/geo_transform.py`), 층 프레임이 제각각이면 그 피팅이 무의미해진다. `studio_adapter`는 `local_m`을 그대로 두고 wgs84만 기준층 아핀으로 재계산한다.
- **트랜잭션 경계**: `seed_studio`가 전 층을 모아 한 번에 commit/rollback. `seed_navigation`은 `session.add`만 하고 commit은 호출자가.

---

## 의존성 방향

```
seed/reset_and_seed   ──►  seed.reset_database, seed.studio_adapter
seed/studio_adapter   ──►  seed.seed_navigation, transform.floor_alignment, transform.vertical_transfers
seed/reset_database   ──►  app.core.database.engine, app.models
seed/seed_navigation  ──►  app.models
```

- seed는 `app.models`·`app.core`(엔진/세션)와 `scripts.transform`(순수 변환)에 의존한다.
- 런타임 DB 파일 위치는 `app.core.config`(`NAV_DATABASE_URL`)가 정한다.

---

## 자주 하는 작업

| 하고 싶은 것 | 방법 |
|---|---|
| 개발 DB 새로 만들기 | `python -m scripts.seed.reset_and_seed` |
| 적재 요약/정합 잔차 보기 | `python -m scripts.seed.studio_adapter` (층별 nodes/edges/정합 오차 출력) |
| 스키마 바꾼 뒤 반영 | 마이그레이션 없음 → `reset_and_seed`로 drop & create |
| 새 건물 데이터 추가 | `resources/studio/<building>/`에 층 JSON 배치 + `studio_adapter`의 `STUDIO_DIR`/`BUILDING_NAMES` 조정 |
