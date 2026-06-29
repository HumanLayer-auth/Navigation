from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/query", tags=["query"])


class DestinationRequest(BaseModel):
    text: str
    building_id: str


class InfoRequest(BaseModel):
    text: str
    building_id: str


@router.post("/destination")
def query_destination(body: DestinationRequest):
    # RAG 구현 예정 (후속 이슈)
    return {"status": "stub", "query": body.text, "result": None}


@router.post("/info")
def query_info(body: InfoRequest):
    # RAG 구현 예정 (후속 이슈)
    return {"status": "stub", "query": body.text, "result": None}
