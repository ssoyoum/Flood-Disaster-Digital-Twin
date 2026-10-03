from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _timing(event_id: str, intervention_id: str, times: list[str]) -> dict:
    response = client.post(f"/api/events/{event_id}/analysis/response-timing", json={"intervention_id": intervention_id, "action_times": times})
    assert response.status_code == 200
    return {row["action_time"][11:16]: row for row in response.json()["scenarios"]}


def test_pohang_parking_entry_ban_lead_times():
    rows = _timing("pohang-2022", "parking_entry_ban", ["06:00"])
    assert rows["06:00"]["minutes_before_milestones"] == {"parking_inflow": 37, "parking_full": 45}
    assert rows["06:30"]["is_actual"] is True
    assert rows["06:30"]["minutes_before_milestones"]["parking_inflow"] == 7
    assert rows["06:00"]["minutes_earlier_than_actual"] == 30


def test_andong_evacuation_order_crosses_midnight():
    rows = _timing("andong-uiseong-2026", "evacuation_order", ["23:40"])
    assert rows["23:40"]["action_time"].startswith("2026-07-18T23:40")
    assert rows["23:40"]["minutes_before_milestones"] == {"predicted_warning_level": 50}
    assert rows["00:00"]["minutes_before_milestones"] == {"predicted_warning_level": 30}


def test_andong_landslide_alert_only_reports_shift():
    rows = _timing("andong-uiseong-2026", "landslide_alert", ["00:00"])
    assert rows["00:00"]["minutes_earlier_than_actual"] == 480
    assert rows["00:00"]["minutes_before_milestones"] == {}


def test_timeline_cases_serve_layers_without_exposure_counts():
    for event_id in ("pohang-2022", "andong-uiseong-2026"):
        reconstruction = client.get(f"/api/events/{event_id}/reconstruction").json()
        assert reconstruction["case_kind"] == "timeline"
        assert all(stage["source_url"] for stage in reconstruction["replay"])
        layers = client.get(f"/api/events/{event_id}/layers").json()
        assert layers["flood_extent"]["status"] == "UNAVAILABLE"
        assert layers["facilities"]["feature_count"] >= 3
        assert client.get(f"/api/events/{event_id}/summary").json()["exposed_buildings"] == "UNAVAILABLE"


def test_response_timing_rejects_bad_requests():
    assert client.post("/api/events/osong-2023/analysis/response-timing", json={"intervention_id": "x"}).status_code == 404
    assert client.post("/api/events/pohang-2022/analysis/response-timing", json={"intervention_id": "nope"}).status_code == 422
    bad_time = {"intervention_id": "parking_entry_ban", "action_times": ["25:00"]}
    assert client.post("/api/events/pohang-2022/analysis/response-timing", json=bad_time).status_code == 422
    assert client.get("/api/events/iksan-2024/reconstruction").status_code == 404


def test_case_lead_times_reuse_each_case_calculation():
    cases = {item["event_id"]: item for item in client.get("/api/cases/lead-times").json()["cases"]}
    assert cases["osong-2023"]["actual"]["lead_min"] is None
    assert cases["osong-2023"]["counterfactual"]["lead_min"] == 107
    assert (cases["seoul-2022"]["actual"]["lead_min"], cases["seoul-2022"]["counterfactual"]["lead_min"]) == (-20, 10)
    assert (cases["pohang-2022"]["actual"]["lead_min"], cases["pohang-2022"]["counterfactual"]["lead_min"]) == (7, 37)
    assert (cases["andong-uiseong-2026"]["actual"]["lead_min"], cases["andong-uiseong-2026"]["counterfactual"]["lead_min"]) == (30, 50)
