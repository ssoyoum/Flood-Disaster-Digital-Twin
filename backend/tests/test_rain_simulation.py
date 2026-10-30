from fastapi.testclient import TestClient

from app import rain_simulation as rs
from app.main import app

client = TestClient(app)


def test_rain_falls_off_from_the_storm_centre():
    preset = rs.PRESETS["central"]
    centre = rs.rain_at(preset, *preset["center"])
    far = rs.rain_at(preset, 129.0, 35.1)
    assert centre["rain_1h_mm"] == preset["peak_1h_mm"] and centre["rain_3h_mm"] >= 90
    assert far["rain_1h_mm"] < 1


def test_stage_is_only_ever_raised():
    assert rs.lifted_stage("normal", 120.0) == "warning"
    assert rs.lifted_stage("planned_flood", 40.0) == "planned_flood"
    assert rs.lifted_stage("normal", 10.0) == "normal"


def test_route_marks_the_response_as_a_simulation():
    body = client.get("/api/watch/facility-risk?sim=central&limit=2000").json()
    assert body["mode"] == "simulation" and body["simulation"]["id"] == "central"
    assert body["limitations"][0] == rs.LIMITATION
    assert body["counts"]["by_level"]["주의"] + body["counts"]["by_level"]["경계"] + body["counts"]["by_level"]["심각"] > 0
    assert client.get("/api/watch/facility-risk?sim=nowhere").status_code == 422
