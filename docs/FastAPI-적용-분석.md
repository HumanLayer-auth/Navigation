# FastAPI 학습 내용 적용 분석 — `api/` 코드에서 바꾸어야 하는 부분

> [FastAPI-핵심-정리.md](./FastAPI-핵심-정리.md)를 기준으로 현재 `api/app` 코드를 훑은 결과.
> 잘 하고 있는 것과 고칠 것을 구분. (§ 표기는 핵심 정리 문서의 장 번호)

---

## 1. 이미 문서 원칙대로 잘 되어 있는 것

| 문서의 원칙 | 현재 코드 |
|---|---|
| `yield` 기반 세션(자원) 의존성 | `FastAPIConfig.get_db()` — try/finally로 커넥션 정리 ✅ |
| 동기 드라이버면 핸들러도 `def` (§3) | 모든 라우터가 `def` — `buildingRouter.py` docstring에 이유까지 명시 ✅ |
| `Depends()` 체인으로 DI | `get_db → get_building_repository → get_building_service` ✅ |
| SQL injection 방지 (파라미터 바인딩) | 모든 쿼리 `?` 바인딩, LIKE 패턴도 바인딩 ✅ |
| Router → Service → Repository 계층 | 그대로 구현됨. Repository는 `Protocol` 계약 ✅ |
| 앱 팩토리 패턴 | `create_app()` — 테스트에서 재사용 ✅ |

---

## 2. 바꾸어야 하는 부분 (우선순위순)

### ① 실제 N+1이 이미 존재한다 — `BuildingService._to_building_summary`

`get_all_buildings()`가 건물 목록을 가져온 뒤, **건물마다** `find_floors_by_building()`을 호출한다.
건물 N개면 쿼리 1 + N방. 핵심 정리 §1의 "루프 안 lazy 로딩" 함정과 정확히 같은 패턴이다.

```python
# 현재 (buildingService.py)
return [self._to_building_summary(b) for b in ...find_all_buildings()]
#        └─ 내부에서 건물마다 find_floors_by_building() 호출 → N+1
```

**해결**: 건물 전체의 층을 한 번에 가져와 메모리에서 그룹핑하는 Repository 메서드 추가
(`selectinload`의 IN 쿼리 원리를 raw SQL로 직접 구현하는 셈).
지금은 건물이 1개라 체감이 없지만, 고치는 연습 대상으로 최적.

### ② 응답 스키마(Pydantic)가 없다 — `dict[str, Any]` 반환

Service가 손으로 조립한 dict를 반환하고 라우터에 `response_model`이 없다.

- `/docs` Swagger에 응답 스키마가 안 나온다 (FastAPI 최대 장점을 버리는 중)
- 필드 오타/누락을 런타임까지 모른다 (DTO 없이 Map 반환하는 것과 같음)

**해결**: `app/schemas/` 디렉토리를 만들고 `BuildingSummary`, `FloorMap`, `StoreRead`,
`NodeRead`, `EdgeRead` 등 Pydantic 모델 정의 → 라우터마다 `response_model=` 지정.
Service의 `_to_*_dict()` 수동 변환이 스키마로 대체된다. `from` 같은 예약어 필드는
`Field(alias="from")` + `populate_by_name` 사용.

### ③ 설정이 `os.getenv` 직접 호출 — pydantic-settings로

`get_db_path()`가 `os.getenv("NAV_DB_PATH", ...)`를 매번 호출한다. 설정이 늘어나면
(CORS 출처, RAG 모델 경로 등) 흩어진다.

**해결**: `app/core/config.py`에 `BaseSettings` 기반 `Settings` 클래스 (§0 대응표의
application.yml 자리). `pydantic-settings` 의존성 추가 필요.

### ④ CORS `allow_origins=["*"]` — 운영 전 교체

코드 주석에도 적혀 있듯 개발용. ③의 Settings로 출처 목록을 환경변수화하면
개발/운영 전환이 코드 수정 없이 된다.

### ⑤ SQLAlchemy 도입 여부 — 지금은 하지 말 것 (의도적 보류)

현재 raw `sqlite3` + 수동 매핑(`_to_building` 등)은 핵심 정리 §1의 SQLAlchemy가 해주는 일을
손으로 하는 것. 도입하면 Repository 매핑 코드 대부분이 사라지고 `relationship`으로
building→floors→stores를 선언할 수 있다. 다만:

- 데이터가 읽기 전용 + 단일 건물 + 스키마 안정 → 지금은 ORM 이득이 작다
- **쓰기 API가 생기는 시점**(매장 CRUD, 사용자 데이터)이 도입 적기. 그때 §1의 2.0 스타일
  (`Mapped`/`mapped_column`)로 시작하고, `load_dataset.py`의 스키마 생성을 Alembic으로 이관 (§4)

### ⑥ 파일명 컨벤션 — 파이썬 표준(snake_case)과 어긋남

`FastAPIConfig.py`, `buildingRouter.py`, `sqliteBuildingRepository.py`는 Java 관례.
파이썬은 모듈명 snake_case가 표준(PEP 8): `config.py`, `building_router.py`,
`sqlite_building_repository.py`. import 경로가 바뀌므로 한 번에 일괄 변경할 것.

### ⑦ `get_db`에 커밋/롤백 경계가 없다 — 쓰기 API 추가 시 필수

현재는 전부 읽기라 문제없지만, 쓰기가 생기면 §2의 패턴대로 `yield` 뒤 `commit()`,
`except`에서 `rollback()`을 추가해야 한다 (@Transactional 없음 — 경계를 직접 정한다).

---

## 3. 정리 — 작업 순서 제안

1. **②(스키마)** 부터 — 코드 구조가 잡히고 Swagger 문서가 즉시 좋아짐. Pydantic 연습으로 최적
2. **①(N+1)** — 핵심 정리 §1 학습 내용을 실전으로 확인하는 과제
3. **③+④(Settings/CORS)** — 한 PR로 묶기 좋음
4. **⑥(파일명)** — 다른 PR과 충돌하지 않는 시점에 단독으로
5. **⑤+⑦(ORM/트랜잭션)** — 쓰기 API가 생길 때까지 보류
