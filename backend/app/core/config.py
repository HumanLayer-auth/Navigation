# 환경변수 기반 애플리케이션 설정.

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


API_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(API_ROOT / 'data' / 'navigation.db').as_posix()}"


# 프로세스 단위로 재사용하는 설정값.
class Settings(BaseSettings):
    database_url: str = DEFAULT_DATABASE_URL
    # 개발 중 실제 SQL/파라미터를 sql/queries.sql에 남긴다. 기본은 비활성화한다.
    sql_echo: bool = False
    # Flutter 등 클라이언트가 API로 보낸 JSON과 JSON 응답을 args/에 남긴다.
    http_capture: bool = False
    # 기동 직후 백그라운드로 임베딩 모델을 올려 첫 /query/ai의 로드 대기를 없앤다.
    # 기본은 비활성 — 켜면 앱을 만드는 모든 프로세스(테스트 포함)가 torch를 로드하고
    # 400MB대 메모리를 상주시킨다. 배포 이미지에서만 켠다.
    warm_embedding: bool = False

    model_config = SettingsConfigDict(env_prefix="NAV_", case_sensitive=False)


settings = Settings()
