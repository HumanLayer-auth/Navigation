# 건물 목록/상세 API 응답 모델.

from pydantic import BaseModel

from app.dto.floor_map import PointResponse


class BuildingSummaryResponse(BaseModel):
    id: str
    name: str
    # 엘리베이터 버튼판 순서(위층 → 아래층). 표시 순서일 뿐 기본 층이 아니다.
    floors: list[str]
    # 앱이 처음 열 층. 목록 순서와 분리해 명시한다.
    default_floor: str | None = None


class BuildingDetailResponse(BuildingSummaryResponse):
    area_m2: float | None
    perimeter_m: float | None
    footprint_local_m: list[PointResponse]
