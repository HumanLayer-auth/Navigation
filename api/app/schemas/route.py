"""최단 경로 API 응답 모델."""

from typing import Literal

from pydantic import BaseModel, Field


class LocalPointResponse(BaseModel):
    x: float
    y: float


class LatLngResponse(BaseModel):
    lat: float
    lng: float


class GraphFloorResponse(BaseModel):
    id: str
    name: str


class GraphNodeResponse(BaseModel):
    id: str
    type: str
    name: str | None
    x_m: float
    y_m: float
    lat: float | None
    lng: float | None


class GraphEdgeResponse(BaseModel):
    id: str
    from_node_id: str = Field(alias="from")
    to_node_id: str = Field(alias="to")
    length_m: float
    bidirectional: bool
    geometry_local_m: list[LocalPointResponse]


class FloorGraphResponse(BaseModel):
    floor: GraphFloorResponse
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class RouteResponse(BaseModel):
    start_node_id: str
    end_node_id: str
    path_found: Literal[True]
    node_ids: list[str]
    edge_ids: list[str]
    coordinate_system: Literal["local_m"]
    path_points: list[LocalPointResponse]
    # 건물에 실좌표 앵커(geo_transform)가 없으면(test-center 등) None.
    # MapLibre 위에 경로선을 그릴 때는 이 값을 쓴다 — local_m을 클라이언트가
    # 직접 위경도로 변환하지 않는다(건물마다 다른 변환 파라미터를 클라이언트가
    # 알 필요가 없게 서버가 대신 계산해서 내려준다).
    path_points_wgs84: list[LatLngResponse] | None
    total_distance_m: float
