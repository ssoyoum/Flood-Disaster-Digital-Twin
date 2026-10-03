from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_seoul_event_is_connected_with_official_traces():
    layers = client.get("/api/events/seoul-2022/layers").json()
    assert layers["flood_extent"]["status"] == "VERIFIED"
    assert layers["flood_extent"]["feature_count"] == 10468
    assert layers["buildings"]["feature_count"] == 13015
    trace_props = layers["flood_extent"]["data"]["features"][0]["properties"]
    assert "flood_zone" not in trace_props  # lot-level home addresses are dropped
    building_props = layers["buildings"]["data"]["features"][0]["properties"]
    assert set(building_props) >= {"dong", "main_use", "max_trace_depth_m"}
    assert "A5" not in building_props


def test_seoul_reconstruction_replays_gauge_and_reported_times():
    reconstruction = client.get("/api/events/seoul-2022/reconstruction").json()
    times = [stage["time"][11:16] for stage in reconstruction["replay"]]
    assert times == ["12:50", "13:09", "20:49", "20:59", "21:19", "21:30", "21:45"]
    assert reconstruction["rainfall_peaks"]["신림P"]["max_60min_mm"] == 121.5
    assert reconstruction["exposure"]["traces"]["union_area_in_aoi_km2"] == 2.556


def test_alert_timing_measures_lead_time_before_first_rescue_call():
    result = client.post(
        "/api/events/seoul-2022/analysis/alert-timing",
        json={"thresholds_mm_per_hour": [50, 95], "alert_times": ["12:50"]},
    ).json()
    rows = {row["label"]: row for row in result["scenarios"]}
    assert rows["신림P 60분 강우 50 mm 도달"]["alert_time"].startswith("2022-08-08T13:09")
    assert rows["신림P 60분 강우 95 mm 도달"]["minutes_before_first_rescue_call"] == 10
    assert rows["신림P 60분 강우 95 mm 도달"]["minutes_earlier_than_actual_alert"] == 30
    assert rows["12:50 수동 경보"]["minutes_before_first_rescue_call"] == 489
    assert result["actual_alert_after_rescue_call_min"] == 20


def test_storage_capture_reports_share_and_fill_time():
    result = client.post("/api/events/seoul-2022/analysis/storage-capture", json={}).json()
    assert result["excess_volume_m3"] == 870263
    assert result["captured_share_pct"] == 46.0
    assert result["storage_full_time"].startswith("2022-08-08T20:49")
    halved = client.post("/api/events/seoul-2022/analysis/storage-capture", json={"runoff_coefficient": 0.5}).json()
    assert halved["captured_share_pct"] == 91.9


def test_seoul_analysis_rejects_bad_input_and_other_events():
    assert client.post("/api/events/osong-2023/analysis/alert-timing", json={}).status_code == 404
    assert client.post("/api/events/seoul-2022/analysis/alert-timing", json={"station": "없는역"}).status_code == 422
    assert client.post("/api/events/seoul-2022/analysis/alert-timing", json={"thresholds_mm_per_hour": [0]}).status_code == 422
    assert client.post("/api/events/seoul-2022/analysis/storage-capture", json={"runoff_coefficient": 1.5}).status_code == 422
