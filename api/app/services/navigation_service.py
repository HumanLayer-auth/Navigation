"""최단 경로 탐색 Service.

한 층의 Node·Edge 전체를 각각 한 번씩 조회한 뒤 메모리에서 다익스트라를 실행한다.
탐색 중 ORM 관계(Edge.from_node 등)를 따라가지 않으므로 N+1 쿼리가 없다.
HTTP/FastAPI 타입은 알지 못한다. 상태 코드 변환은 Router가 담당한다.

기존 계약:
- 잘못된 시작/끝 노드 → ValueError (dijkstra가 발생)
- 없는 건물/층 → None
- 경로 없음 → {"path_found": False, ...}
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.dijkstra import ShortestPath, find_shortest_path
from app.domain.tiling import local_points_to_lnglat
from app.models import Edge, Floor, Node
from app.queries.geo_transform import fit_building_geo_transform


class NavigationService:
    def __init__(self, session: Session):
        self._session = session

    def get_shortest_path(
        self,
        building_id: str,
        floor_name: str,
        start_node_id: str,
        end_node_id: str,
    ) -> dict[str, Any] | None:
        floor = self._session.scalars(
            select(Floor).where(
                Floor.building_id == building_id,
                Floor.name == floor_name,
            )
        ).one_or_none()
        if floor is None:
            return None

        nodes = self._session.scalars(
            select(Node).where(Node.floor_id == floor.id)
        ).all()
        edges = self._session.scalars(
            select(Edge).where(Edge.floor_id == floor.id)
        ).all()

        path = find_shortest_path(
            nodes=nodes,
            edges=edges,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
        )

        if path is None:
            return {
                "start_node_id": start_node_id,
                "end_node_id": end_node_id,
                "path_found": False,
            }

        path_points = self._build_path_points(path, nodes, edges)
        transform = fit_building_geo_transform(self._session, building_id)
        path_points_wgs84 = [
            {"lng": lng, "lat": lat}
            for lng, lat in local_points_to_lnglat(path_points, transform)
        ]

        return {
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            "path_found": True,
            "node_ids": list(path.node_ids),
            "edge_ids": list(path.edge_ids),
            "coordinate_system": "local_m",
            "path_points": path_points,
            "path_points_wgs84": path_points_wgs84,
            "total_distance_m": round(path.total_distance_m, 3),
        }

    @staticmethod
    def _build_path_points(
        path: ShortestPath,
        nodes: list[Node],
        edges: list[Edge],
    ) -> list[dict[str, float]]:
        """최단 경로의 간선 geometry를 진행 방향에 맞춰 하나의 선으로 합친다."""
        nodes_by_id = {node.id: node for node in nodes}
        edges_by_id = {edge.id: edge for edge in edges}

        if not path.edge_ids:
            node = nodes_by_id[path.node_ids[0]]
            return [{"x": node.x_m, "y": node.y_m}]

        path_points: list[dict[str, float]] = []

        for index, edge_id in enumerate(path.edge_ids):
            edge = edges_by_id[edge_id]
            from_node_id = path.node_ids[index]
            to_node_id = path.node_ids[index + 1]

            geometry = [dict(point) for point in (edge.geometry or [])]
            if not geometry:
                from_node = nodes_by_id[from_node_id]
                to_node = nodes_by_id[to_node_id]
                geometry = [
                    {"x": from_node.x_m, "y": from_node.y_m},
                    {"x": to_node.x_m, "y": to_node.y_m},
                ]
            elif (
                edge.from_node_id == to_node_id
                and edge.to_node_id == from_node_id
            ):
                # 간선을 역방향으로 지나면 좌표 순서를 뒤집어 진행 방향을 맞춘다.
                geometry.reverse()
            elif not (
                edge.from_node_id == from_node_id
                and edge.to_node_id == to_node_id
            ):
                raise ValueError(
                    f"간선 {edge.id}가 경로 노드 {from_node_id}, {to_node_id}와 연결되지 않습니다."
                )

            if path_points and path_points[-1] == geometry[0]:
                path_points.extend(geometry[1:])
            else:
                path_points.extend(geometry)

        return path_points
