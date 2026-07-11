"""자연어 질의 HTTP API 계약 테스트."""

from tests.conftest import BUILDING_ID


def test_목적지_질의_스텁(api_client):
    payload = {"text": "구찌 어디야", "building_id": BUILDING_ID}

    response = api_client.post("/query/destination", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "stub"
    assert body["query"] == payload["text"]
    assert body["result"] is None


def test_정보_질의_스텁(api_client):
    payload = {"text": "화장실 위치", "building_id": BUILDING_ID}

    response = api_client.post("/query/info", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "stub"
    assert body["query"] == payload["text"]
    assert body["result"] is None
