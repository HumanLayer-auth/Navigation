# FastAPI 핵심 정리 — Spring Boot/JPA 경험자 기준

> JPA 기본편을 공부한 상태에서 FastAPI + SQLAlchemy 프로젝트를 만들 때 꼭 알아야 하는 것만.
> 스프링에서 넘어올 때 헷갈리는 지점 위주로 정리. (다듬으면서 채워나갈 것)

---

## 0. 큰 그림 — 스프링 대응표

| Spring Boot | FastAPI 생태계 | 비고 |
|---|---|---|
| Spring MVC (@RestController) | FastAPI 라우터 (`APIRouter`) | 데코레이터 기반 |
| Bean 컨테이너 / @Autowired | **`Depends()` 함수 주입** | 컨테이너 없음, 함수 단위 |
| DTO + Bean Validation | **Pydantic 모델** | 검증 + 직렬화 + 문서화 한 번에 |
| JPA / Hibernate | **SQLAlchemy** (ORM) | 같은 Unit of Work 계보 |
| Spring Data JPA | SQLAlchemy 2.0 `select()` + 직접 리포지토리 | 자동 쿼리 생성은 없음 |
| application.yml | pydantic-settings (`BaseSettings`) | 환경변수 기반 |
| Flyway / Liquibase | **Alembic** | 마이그레이션 |
| 내장 톰캣 | **uvicorn** (ASGI 서버) | `uvicorn main:app --reload` |
| springdoc (Swagger) | **자동 내장** — `/docs` | 코드만 쓰면 문서가 나옴 |

---

## 1. SQLAlchemy — JPA 개념이 그대로 이식된다

### 개념 대응표 (⭐ 제일 중요)

| JPA에서 배운 것 | SQLAlchemy | 메모 |
|---|---|---|
| EntityManager / 영속성 컨텍스트 | **`Session`** | identity map = 1차 캐시 |
| `em.persist()` | `session.add()` | 마찬가지로 즉시 INSERT 아님 |
| 쓰기 지연 → flush → commit | `session.flush()` / `session.commit()` | 동일. 쿼리 직전 autoflush도 동일 |
| 변경 감지 (dirty checking) | 동일하게 있음 | 값만 바꾸면 커밋 시 UPDATE |
| `em.find()` 1차 캐시 조회 | `session.get(Model, pk)` | PK 조회만 캐시 먼저 봄 |
| JPQL은 항상 SQL 발사 | `select()` 쿼리도 항상 DB로 | 조립 시 identity map으로 동일성 보장 |
| 지연 로딩 (LAZY) | `relationship(lazy="select")` 기본값 | **N+1 똑같이 터짐** |
| 페치 조인 `join fetch` | **`joinedload()`** | 컬렉션이면 중복 제거에 `.unique()` 필요 |
| `@BatchSize` IN 배치 | **`selectinload()`** | 컬렉션 로딩의 실무 기본값. IN 쿼리 한 방 |
| 컬렉션 페치 조인 + 페이징 금지 | joinedload + limit 동일한 함정 | 컬렉션은 selectinload로 |
| `LazyInitializationException` | **`DetachedInstanceError`** | 세션 닫힌 뒤 lazy 속성 접근 |
| 벌크 연산 (영속성 컨텍스트 무시) | `update()`/`delete()` 문 | 실행 후 세션과 어긋남 주의 (`synchronize_session`) |
| 엔티티 직접 반환 금지 → DTO | 모델 직접 반환 금지 → **Pydantic 스키마** | 이유도 같음 (lazy 폭발, 순환 참조) |

### 꼭 지킬 것

1. **SQLAlchemy 2.0 스타일로 시작** — 검색하면 1.x 문법(`session.query(...)`)이 잔뜩 나오는데, `select()` 기반 2.0 스타일을 쓸 것.

```python
# 2.0 스타일 (이걸로)
stmt = select(Member).where(Member.age > 18).order_by(Member.id)
members = session.execute(stmt).scalars().all()

# 1.x 레거시 (문서/블로그에서 보이면 걸러 읽기)
members = session.query(Member).filter(Member.age > 18).all()
```

2. **모델 선언 — 2.0 방식 (`Mapped` + `mapped_column`)**

```python
class Base(DeclarativeBase):
    pass

class Member(Base):
    __tablename__ = "member"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("team.id"))

    team: Mapped["Team | None"] = relationship(back_populates="members")

class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    members: Mapped[list["Member"]] = relationship(back_populates="team")
```

- `back_populates` = JPA의 mappedBy 양방향 대응. 다만 SQLAlchemy는 **양쪽을 자동 동기화**해줘서 편의 메서드가 필요 없다.
- FK 컬럼(`team_id`)이 모델에 그대로 보이는 게 JPA와 다른 점. 참조(`team`)와 공존한다.

3. **N+1 해결 — 로딩 전략을 쿼리에서 지정**

```python
# 컬렉션: selectinload (JPA의 @BatchSize IN 쿼리와 같은 원리, 실무 기본)
stmt = select(Team).options(selectinload(Team.members))

# N:1 단건: joinedload (JPA의 fetch join)
stmt = select(Member).options(joinedload(Member.team))
```

---

## 2. FastAPI 기본 구조

### 최소 앱 + 계층 구조

```
app/
├── main.py              # FastAPI() 생성, 라우터 등록
├── core/
│   ├── config.py        # Settings (환경변수)
│   └── database.py      # engine, SessionLocal, get_db
├── models/              # SQLAlchemy 모델 (엔티티)
├── schemas/             # Pydantic 스키마 (DTO)
├── routers/             # APIRouter (컨트롤러)
└── services/            # 비즈니스 로직
```

- Router → Service → (Repository) 계층은 그대로 가져가도 됨.
- 단, 스프링처럼 인터페이스+구현체를 미리 쪼개는 건 과설계. 함수/모듈 단위로 가볍게.

### 세션 주입 — 요청당 세션 하나 (EM 쓰고 버리기와 같은 규칙)

```python
# core/database.py
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db          # 요청 처리 동안 사용
        db.commit()       # (또는 라우터에서 명시적으로)
    except:
        db.rollback()
        raise
    finally:
        db.close()        # 요청 끝나면 반납
```

```python
# routers/member.py
router = APIRouter(prefix="/members", tags=["members"])

@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
```

- `Depends(get_db)` = 스프링의 트랜잭션 스코프 + EM 주입을 손으로 하는 것.
- `yield` 기반 의존성 = try/finally로 자원 정리. **@Transactional은 없다** — 커밋/롤백 경계를 직접 정한다.

### Pydantic 스키마 — DTO + 검증 + 문서화

```python
class MemberCreate(BaseModel):          # 요청 DTO
    username: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0)

class MemberRead(BaseModel):            # 응답 DTO
    id: int
    username: str
    age: int

    model_config = ConfigDict(from_attributes=True)  # ORM 모델 → 스키마 변환 허용
```

- `response_model=MemberRead` 를 지정하면 ORM 모델을 반환해도 스키마로 걸러서 나간다.
- `from_attributes=True` (구버전 이름 `orm_mode`) 필수 — 없으면 ORM 객체 변환 에러.
- ⚠️ 응답 스키마에 lazy 관계 필드를 넣으면 **직렬화 시점에 추가 쿼리 발생** — 세션이 이미 닫혔으면 DetachedInstanceError. 관계 필드가 필요하면 쿼리에서 selectinload로 미리 로딩.

---

## 3. async — 처음엔 무리하지 말 것

- FastAPI는 `def` / `async def` 둘 다 지원. **`def` 로 시작해도 전혀 문제 없다** (스레드풀에서 실행됨).
- `async def` 안에서 **동기 SQLAlchemy 세션을 쓰면 이벤트 루프가 통째로 막힌다** — 최악의 조합.
- async DB까지 가려면 `create_async_engine` + `AsyncSession` + asyncpg 드라이버로 세트를 전부 바꿔야 함.
- ✅ 결론: **1차 버전은 동기(def + Session)로.** async는 성능이 실제로 필요해질 때.

---

## 4. 마이그레이션 — Alembic

ddl-auto(create/update)에 해당하는 게 없다. 스키마 변경은 Alembic으로:

```bash
alembic init alembic                                  # 최초 1회
alembic revision --autogenerate -m "add member"       # 모델 diff → 마이그레이션 생성
alembic upgrade head                                  # 적용
```

- `--autogenerate` 는 모델과 DB를 비교해 초안을 만들어줄 뿐, **생성된 파일을 반드시 눈으로 확인** (JPA update 옵션의 함정과 같은 이유).
- 개발 초기에 귀찮으면 `Base.metadata.create_all(engine)` 로 시작해도 되지만(= ddl-auto create), Alembic 도입 전까지만.

---

## 5. 자주 터지는 에러 미리보기

| 증상 | 원인 | 해결 |
|------|------|------|
| `DetachedInstanceError` | 세션 닫힌 뒤 lazy 속성 접근 (JPA의 LazyInitializationException) | 응답에 쓸 관계는 쿼리에서 `selectinload`/`joinedload` |
| 응답은 나오는데 쿼리가 수십 방 | N+1 — 루프 안에서 lazy 로딩 | 로딩 전략 옵션 지정 |
| `MissingGreenlet` | async 함수에서 동기 세션 lazy 로딩 | async 세트로 통일하거나 동기로 회귀 |
| Pydantic `ValidationError` (ORM 변환) | `from_attributes=True` 누락 | 스키마 config 추가 |
| 커밋했는데 값이 안 바뀜 | 벌크 `update()` 후 세션의 옛 객체 사용 | `session.expire_all()` / 재조회 (JPA의 em.clear()와 동일) |
| CORS 에러 | 프론트 붙일 때 미들웨어 미설정 | `CORSMiddleware` 추가 |

---

## 6. 내일 공부 순서 제안

1. FastAPI 공식 튜토리얼의 **SQL (Relational) Databases** 챕터 — 위 구조가 그대로 나옴
2. SQLAlchemy 2.0 공식 문서의 **ORM Quick Start** → **Session Basics**
3. 미니 CRUD 하나 만들기 (Member/Team이면 JPA 실습과 1:1 비교 가능)
4. 일부러 N+1 터뜨리고 `selectinload` 로 잡아보기 — echo=True 로 SQL 로그 켜고
5. Alembic으로 컬럼 하나 추가해보기

```python
# SQL 로그 켜기 (hibernate.show_sql 대응)
engine = create_engine(url, echo=True)
```

---

## 7. 이 프로젝트(`api/`)에 적용 — 바꾸어야 하는 부분

> 위 내용을 기준으로 현재 `api/app` 코드를 훑은 결과. 잘 하고 있는 것과 고칠 것을 구분.

### 7-1. 이미 문서 원칙대로 잘 되어 있는 것

| 문서의 원칙 | 현재 코드 |
|---|---|
| `yield` 기반 세션(자원) 의존성 | `FastAPIConfig.get_db()` — try/finally로 커넥션 정리 ✅ |
| 동기 드라이버면 핸들러도 `def` (§3) | 모든 라우터가 `def` — `buildingRouter.py` docstring에 이유까지 명시 ✅ |
| `Depends()` 체인으로 DI | `get_db → get_building_repository → get_building_service` ✅ |
| SQL injection 방지 (파라미터 바인딩) | 모든 쿼리 `?` 바인딩, LIKE 패턴도 바인딩 ✅ |
| Router → Service → Repository 계층 | 그대로 구현됨. Repository는 `Protocol` 계약 ✅ |
| 앱 팩토리 패턴 | `create_app()` — 테스트에서 재사용 ✅ |

### 7-2. 바꾸어야 하는 부분 (우선순위순)

#### ① 실제 N+1이 이미 존재한다 — `BuildingService._to_building_summary`

`get_all_buildings()`가 건물 목록을 가져온 뒤, **건물마다** `find_floors_by_building()`을 호출한다.
건물 N개면 쿼리 1 + N방. 문서 §1의 "루프 안 lazy 로딩" 함정과 정확히 같은 패턴이다.

```python
# 현재 (buildingService.py)
return [self._to_building_summary(b) for b in ...find_all_buildings()]
#        └─ 내부에서 건물마다 find_floors_by_building() 호출 → N+1
```

**해결**: 건물 전체의 층을 한 번에 가져와 메모리에서 그룹핑하는 Repository 메서드 추가
(`selectinload`의 IN 쿼리 원리를 raw SQL로 직접 구현하는 셈).
지금은 건물이 1개라 체감이 없지만, 고치는 연습 대상으로 최적.

#### ② 응답 스키마(Pydantic)가 없다 — `dict[str, Any]` 반환

Service가 손으로 조립한 dict를 반환하고 라우터에 `response_model`이 없다.
- `/docs` Swagger에 응답 스키마가 안 나온다 (FastAPI 최대 장점을 버리는 중)
- 필드 오타/누락을 런타임까지 모른다 (DTO 없이 Map 반환하는 것과 같음)

**해결**: `app/schemas/` 디렉토리를 만들고 `BuildingSummary`, `FloorMap`, `StoreRead`,
`NodeRead`, `EdgeRead` 등 Pydantic 모델 정의 → 라우터마다 `response_model=` 지정.
Service의 `_to_*_dict()` 수동 변환이 스키마로 대체된다. `from` 같은 예약어 필드는
`Field(alias="from")` + `populate_by_name` 사용.

#### ③ 설정이 `os.getenv` 직접 호출 — pydantic-settings로

`get_db_path()`가 `os.getenv("NAV_DB_PATH", ...)`를 매번 호출한다. 설정이 늘어나면
(CORS 출처, RAG 모델 경로 등) 흩어진다.

**해결**: `app/core/config.py`에 `BaseSettings` 기반 `Settings` 클래스 (§0 대응표의
application.yml 자리). `pydantic-settings` 의존성 추가 필요.

#### ④ CORS `allow_origins=["*"]` — 운영 전 교체

코드 주석에도 적혀 있듯 개발용. ③의 Settings로 출처 목록을 환경변수화하면
개발/운영 전환이 코드 수정 없이 된다.

#### ⑤ SQLAlchemy 도입 여부 — 지금은 하지 말 것 (의도적 보류)

현재 raw `sqlite3` + 수동 매핑(`_to_building` 등)은 문서 §1의 SQLAlchemy가 해주는 일을
손으로 하는 것. 도입하면 Repository 매핑 코드 대부분이 사라지고 `relationship`으로
building→floors→stores를 선언할 수 있다. 다만:
- 데이터가 읽기 전용 + 단일 건물 + 스키마 안정 → 지금은 ORM 이득이 작다
- **쓰기 API가 생기는 시점**(매장 CRUD, 사용자 데이터)이 도입 적기. 그때 §1의 2.0 스타일
  (`Mapped`/`mapped_column`)로 시작하고, `load_dataset.py`의 스키마 생성을 Alembic으로 이관 (§4)

#### ⑥ 파일명 컨벤션 — 파이썬 표준(snake_case)과 어긋남

`FastAPIConfig.py`, `buildingRouter.py`, `sqliteBuildingRepository.py`는 Java 관례.
파이썬은 모듈명 snake_case가 표준(PEP 8): `config.py`, `building_router.py`,
`sqlite_building_repository.py`. import 경로가 바뀌므로 한 번에 일괄 변경할 것.

#### ⑦ `get_db`에 커밋/롤백 경계가 없다 — 쓰기 API 추가 시 필수

현재는 전부 읽기라 문제없지만, 쓰기가 생기면 §2의 패턴대로 `yield` 뒤 `commit()`,
`except`에서 `rollback()`을 추가해야 한다 (@Transactional 없음 — 경계를 직접 정한다).

### 7-3. 정리 — 작업 순서 제안

1. **②(스키마)** 부터 — 코드 구조가 잡히고 Swagger 문서가 즉시 좋아짐. Pydantic 연습으로 최적
2. **①(N+1)** — 문서 §1 학습 내용을 실전으로 확인하는 과제
3. **③+④(Settings/CORS)** — 한 PR로 묶기 좋음
4. **⑥(파일명)** — 다른 PR과 충돌하지 않는 시점에 단독으로
5. **⑤+⑦(ORM/트랜잭션)** — 쓰기 API가 생길 때까지 보류
