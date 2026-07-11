"""최단 경로 API 응답 모델."""

from typing import Literal

from pydantic import BaseModel


class LocalPointResponse(BaseModel):
    x: float
    y: float


class RouteResponse(BaseModel):
    start_node_id: str
    end_node_id: str
    path_found: Literal[True]
    node_ids: list[str]
    edge_ids: list[str]
    coordinate_system: Literal["local_m"]
    path_points: list[LocalPointResponse]
    total_distance_m: float
