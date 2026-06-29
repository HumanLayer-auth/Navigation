from pydantic import BaseModel
from typing import Any


class POI(BaseModel):
    id: str
    name: str
    type: str
    geometry: dict[str, Any]
    properties: dict[str, Any] = {}


class Floor(BaseModel):
    floor: int
    geojson: dict[str, Any]


class Building(BaseModel):
    id: str
    name: str
    floors: list[int]
