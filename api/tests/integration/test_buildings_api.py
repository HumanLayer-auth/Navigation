from fastapi.testclient import TestClient

from app.main import app


def test_buildings_api_returns_summary_without_floor_data():
    client = TestClient(app)

    response = client.get("/buildings")

    assert response.status_code == 200
    buildings = response.json()
    assert isinstance(buildings, list)
    assert buildings[0]["id"] == "bldg-001"
    assert buildings[0]["name"] == "데모 건물"
    assert "floor_data" not in buildings[0]
