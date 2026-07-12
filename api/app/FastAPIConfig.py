"""
설정, DI, 팩토리 담당

DB 경로를 환경변수 NAV_DB_PATH 로 주입
DI : get_db > get_building_repository > get_building_service
create_app() : FastAPI 인스턴스 생성, CORS, 라우터 등록, /health, 시드 확인(lifespan)

- get_db는 yield dependency 이다. 핸들러 실행 전에 커넥션을 열고, 응답 전송 후 finally 에서 닫는다.
- 라우터 import는 create_app() 안에서 한다. 라우터가 이 모듈의 get_building_service를 import하므로, 모듈 레벨에서 서로 import하면 순환 import가 발생한다.
"""
import os
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repository.BuildingRepository import BuildingRepository
from app.repository.sqliteBuildingRepository import SqliteBuildingRepository
from app.service.buildingService import BuildingService

# 이 파일 위치를 기준으로 api/ 루트와 기본 DB 경로를 계산한다.
# 실행 디렉토리가 달라져도 같은 navigation.db를 찾기 위한 기준점이다.
API_ROOT = Path(__file__).resolve().parents[1]


def get_db_path() -> str:
    """DB 파일 경로. 운영/테스트에서 NAV_DB_PATH 환경변수로 교체 가능."""
    return os.getenv("NAV_DB_PATH", str(API_ROOT / "data" / "navigation.db"))


def ensure_database_seeded(db_path: str) -> None:
    """DB에 buildings 테이블/데이터가 없으면 기본 데이터셋을 자동 적재한다.

    api/data/는 .gitignore에 걸려 있어 git에 안 올라간다. 새로 클론한 환경이나
    CI, 배포 서버에서 scripts/load_dataset.py를 미리 돌려두지 않은 채로 서버부터
    켜면 get_db()가 빈 파일에 연결만 해줄 뿐 테이블은 안 만들어줘서, /buildings
    계열 엔드포인트가 전부 "no such table" 500으로 죽는다.
    이미 데이터가 있으면(=이미 시드된 실제/운영 DB) 절대 건드리지 않고 그대로 둔다 —
    DROP은 이 함수를 거치지 않고 load_dataset.py를 직접 실행할 때만 일어난다.
    """
    conn = sqlite3.connect(db_path)
    try:
        has_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='buildings'"
        ).fetchone()
        already_seeded = has_table is not None and (
            conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0] > 0
        )
    finally:
        conn.close()

    if already_seeded:
        return

    # 순환 import 방지 + 이미 시드된 경우엔 이 무거운 import 자체를 안 하려고
    # 함수 안에서 지연 import한다(스크립트가 numpy/mapbox_vector_tile 등을 끌어옴).
    from scripts.load_dataset import DEFAULT_JSON, DEFAULT_VECTOR_DIR, load_navigation_db

    print(f"[startup] '{db_path}'에 시드 데이터가 없어 기본 데이터셋을 자동 적재합니다...")
    # 1) thehyundai-seoul — 기본 JSON, 테이블 새로 생성(append=False)
    load_navigation_db(json_path=DEFAULT_JSON, db_path=db_path, vector_path=DEFAULT_VECTOR_DIR)
    # 2) test-center — 위에서 만든 테이블에 건물만 추가 적재
    load_navigation_db(
        json_path=API_ROOT / "app" / "data" / "navigation_test_center_1f.json",
        db_path=db_path,
        vector_path=DEFAULT_VECTOR_DIR,
        append=True,
    )
    print("[startup] 시드 적재 완료.")


def get_db() -> Iterator[sqlite3.Connection]:
    """요청당 SQLite 커넥션. 응답 전송 후 자동으로 닫힌다."""
    # sqlite3는 동기 드라이버이므로 이 커넥션을 사용하는 라우터도 def로 선언한다.
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능한 row
    try:
        yield conn      # ← 여기서 핸들러가 실행된다
    finally:
        conn.close()    # ← 응답 전송 후 실행 (try-with-resources 대응)


def get_building_repository(
    conn: sqlite3.Connection = Depends(get_db),
) -> BuildingRepository:
    # FastAPI가 get_db를 먼저 실행하고 요청 전용 커넥션을 이 함수에 전달한다.
    # 반환 타입은 Protocol이고 실제 구현체는 SQLite Repository다.
    return SqliteBuildingRepository(conn)


def get_building_service(
    repository: BuildingRepository = Depends(get_building_repository),
) -> BuildingService:
    # Service는 SQLite를 직접 알지 않고 BuildingRepository 계약에만 의존한다.
    return BuildingService(repository)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 서버가 요청을 받기 시작하기 전에 한 번만 확인한다. TestClient도 컨텍스트
    # 매니저로 쓰면 이 lifespan을 그대로 타는데, 이미 시드된 DB(dev/CI 공용)는
    # ensure_database_seeded가 즉시 반환하므로 테스트 시간에 영향이 거의 없다.
    ensure_database_seeded(get_db_path())
    yield


def create_app() -> FastAPI:
    """FastAPI 앱 팩토리. main.py와 테스트가 이 함수로 앱을 만든다."""
    # 순환 import 방지를 위해 함수 안에서 import (모듈 docstring 참고)
    from app.router import buildingRouter, queryRouter

    app = FastAPI(title="Navigation API", version="0.2.0", lifespan=_lifespan)

    # 개발 중에는 모든 출처(*) 허용. 운영 배포 시 Flutter 앱 도메인으로 교체 필요
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 기능별 APIRouter를 하나의 FastAPI 앱에 등록한다.
    app.include_router(buildingRouter.router)  # 건물/지도/그래프 API
    app.include_router(queryRouter.router)     # 자연어 질의 API(현재 stub)

    @app.get("/health", tags=["health"])
    def health():
        """서버 생존 확인. Flutter가 서버 연결 전 호출."""
        return {"status": "ok"}

    return app
