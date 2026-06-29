from fastapi import APIRouter, HTTPException
from app.services import building_service

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("")
def list_buildings():
    return building_service.get_all_buildings()


@router.get("/{building_id}")
def get_building(building_id: str):
    result = building_service.get_building(building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/{building_id}/floors/{floor}")
def get_floor(building_id: str, floor: int):
    result = building_service.get_floor_geojson(building_id, floor)
    if result is None:
        raise HTTPException(status_code=404, detail="Floor not found")
    return result
