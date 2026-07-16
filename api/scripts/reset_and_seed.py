"""개발 DB를 초기화하고 더현대 서울 Studio 1F만 적재하는 CLI.

현재 데이터 원천과 적재 범위는 더현대 서울 Studio 1F다.

실행 방법 (api/ 디렉토리에서):
  python -m scripts.reset_and_seed
"""

from __future__ import annotations

from scripts.reset_database import reset_database
from scripts.studio_adapter import seed_studio


def reset_and_seed_studio() -> None:
    """기존 DB를 비운 뒤 Studio 1F만 적재한다."""
    reset_database()
    seed_studio()


if __name__ == "__main__":
    reset_and_seed_studio()
    print("개발 DB 초기화 및 Studio 데이터 적재 완료: 1f")
