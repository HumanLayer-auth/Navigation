"""
공용 픽스처

세션 범위에서 임시 SQLite에 ORM create_all → seed를 한 번 수행하고,
Query/Service/API 테스트가 같은 시드 DB를 공유한다.
api_client는 FastAPI dependency_overrides로 core.database.get_db만 테스트 Session으로 바꾼다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  # 모든 모델을 Base.metadata에 등록
from app.core.database import get_db
from app.main import create_app
from app.models.base import Base
from scripts.seed_navigation import seed_navigation

# 여러 테스트가 같은 실데이터 식별자를 사용하도록 상수로 공유한다.
BUILDING_ID = "thehyundai-seoul"
FLOOR_NAME = "1F"


@pytest.fixture(scope="session")
def db_engine(tmp_path_factory):
    """임시 SQLite에 스키마 생성 후 실데이터 JSON을 시드 (세션당 1회)."""
    db_path = tmp_path_factory.mktemp("db") / "navigation.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        # TestClient 요청은 스레드풀에서 실행되므로 스레드 검사를 끈다.
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        seed_navigation(session=session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def db_session(session_factory):
    # 각 테스트에 독립 Session을 제공하고 종료 시 닫는다.
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def api_client(session_factory):
    # 실제 앱과 같은 라우터 구성을 사용하되 DB dependency만 시드 DB로 교체한다.
    app = create_app()

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    # 다른 테스트에 override가 남지 않도록 사용 후 초기화한다.
    app.dependency_overrides.clear()
