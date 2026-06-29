import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_building() -> dict:
    with open(_DATA_DIR / "sample_building.json", encoding="utf-8") as f:
        return json.load(f)


def get_all_buildings() -> list[dict]:
    b = _load_building()
    return [{"id": b["id"], "name": b["name"], "floors": b["floors"]}]


def get_building(building_id: str) -> dict | None:
    b = _load_building()
    if b["id"] != building_id:
        return None
    return {"id": b["id"], "name": b["name"], "floors": b["floors"]}


def get_floor_geojson(building_id: str, floor: int) -> dict | None:
    b = _load_building()
    if b["id"] != building_id:
        return None
    return b["floor_data"].get(str(floor))
