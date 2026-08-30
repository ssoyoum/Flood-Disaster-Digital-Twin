from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_event_and_baseline():
    event = client.get("/api/events").json()[0]
    assert event["id"] == "osong-2023"
    assert event["focus_feature"] == "지하차도·교통시설"
    assert event["origin"] == "SIMULATED"
    baseline = client.get("/api/scenarios/baseline").json()
    assert baseline["result"]["origin"] == "DERIVED"
    assert baseline["result"]["flooded_area_km2"] > 0
    layers = client.get("/api/events/osong-2023/layers").json()
    assert len(layers["buildings"]["features"]) > 0
    assert len(layers["roads"]["features"]) > 0
    assert client.get("/api/events/osong-2023/flood/timeline").json()[0]["timestamp"].startswith("2023-07-15")
    assert client.get("/api/events/seoul-2022").json()["origin"] == "OBSERVED"


def test_scenario_comparison():
    response = client.post("/api/scenarios", json={"name": "대피소 개방 시나리오", "intervention_type": "SHELTER_OPEN"})
    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "SIMULATED"
    assert body["result"]["exposed_population"] <= body["baseline"]["exposed_population"]
