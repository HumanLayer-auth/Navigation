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
