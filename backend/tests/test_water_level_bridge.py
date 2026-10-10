from datetime import datetime, timedelta
import math

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app import twin, water_level_bridge as bridge

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"
STATION = "3011665"
NOW = datetime(2023, 7, 15, 8)


def reading(at, level, station=STATION):
    return {"time": at, "water_level_m": level, "station_id": station}


def test_real_replay_inputs_do_not_call_live_or_produce_forecasts(monkeypatch):
    monkeypatch.setattr(twin, "get_source", lambda: pytest.fail("Explicit replay must not use the configured live source"))
    response = client.get(f"/api/twin/facilities/{FACILITY}/forecast-readiness", params={"at": NOW.isoformat()})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "replay" and data["as_of"] == NOW.isoformat()
    assert data["features"]["wl_t"] == 9.91
    source = {row["time"]: row["water_level_m"] for row in twin.ReplaySource().series(STATION)}
    for point in data["history"]:
        assert point["water_level_m"] == source[NOW - timedelta(hours=point["hours_ago"])]
    assert data["available_input_count"] == 6 and data["required_input_count"] == 22
    assert data["prediction_maxrise_6h_m"] is None and data["prediction_available"] is False
    assert data["control_decision_usable"] is False
    assert data["research"]["evaluation"]["floodops_facility_score"] is None
    assert "ANONYMOUS_STATION_NOT_MAPPED" in data["blockers"]
    assert "radar_reflectivity_mean" in data["missing_features"]
    assert math.isclose(data["research"]["evaluation"]["global_rmse_m"], 0.2215642409082992)


def test_history_anchors_to_the_last_observation_and_ignores_future_and_other_stations():
    rows = [reading(NOW, 4), reading(NOW - timedelta(hours=1), 3),
            reading(NOW + timedelta(minutes=10), 99), reading(NOW, 99, "another")]
    data = bridge.water_inputs(rows, NOW + timedelta(minutes=9), STATION)
    assert data["as_of"] == NOW.isoformat() and data["observation_age_min"] == 9
    assert data["features"]["wl_t"] == 4 and data["features"]["wl_t_minus_1h"] == 3
    assert data["derived_features"]["wl_change_1h"] == 1


def test_live_hourly_delay_still_fetches_the_exact_24_hour_lag(monkeypatch):
    class DelayedHourlySource:
        mode = "live"
        def window(self, station_id, end, minutes):
            anchor = end - timedelta(minutes=90)
            return [{**reading(anchor - timedelta(hours=lag), 4 - lag / 24), "interval": "1H"}
                    for lag in bridge.LAGS if end - timedelta(minutes=minutes) <= anchor - timedelta(hours=lag)]
    monkeypatch.setattr(twin, "twin_mode", lambda: {"mode": "live"})
    monkeypatch.setattr(twin, "get_source", lambda: DelayedHourlySource())
    response = client.get(f"/api/twin/facilities/{FACILITY}/forecast-readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "live" and data["interval"] == "1H"
    assert data["observation_quality"] == "fresh" and data["observation_age_min"] == 90
    assert data["available_input_count"] == 6 and data["features"]["wl_t_minus_24h"] == 3


def test_missing_lags_are_not_zero_filled_carried_or_interpolated():
    rows = [reading(NOW, 4), reading(NOW - timedelta(minutes=59), 9),
            reading(NOW - timedelta(hours=1, minutes=1), 3), reading(NOW - timedelta(hours=24), float("nan"))]
    data = bridge.water_inputs(rows, NOW, STATION)
    assert data["features"]["wl_t_minus_1h"] is None
    assert data["features"]["wl_t_minus_24h"] is None
    assert data["derived_features"] == {}
    assert data["history"][1]["status"] == "MISSING_EXACT_LAG"
    assert bridge.water_inputs([], NOW, STATION)["observation_quality"] == "missing"


def test_conflicting_duplicate_observations_fail_instead_of_picking_arbitrary_values():
    with pytest.raises(ValueError, match="Conflicting"):
        bridge.water_inputs([reading(NOW, 1), reading(NOW, 2)], NOW, STATION)


@pytest.mark.parametrize("interval,age,quality", [("10M", 20, "fresh"), ("10M", 21, "stale"), ("1H", 90, "fresh"), ("1H", 91, "stale")])
def test_freshness_policy(interval, age, quality):
    row = {**reading(NOW - timedelta(minutes=age), 4), "interval": interval}
    assert bridge.water_inputs([row], NOW, STATION)["observation_quality"] == quality


@pytest.mark.parametrize("at", ["2023-07-14T23:00:00Z", "2023-07-14T23:00:00+00:00"])
def test_utc_time_normalizes_to_kst(at):
    assert bridge.parse_time(at) == NOW


def test_errors_and_unknown_facility_are_safe(monkeypatch):
    assert client.get("/api/twin/facilities/nope/forecast-readiness").status_code == 404
    assert client.get(f"/api/twin/facilities/{FACILITY}/forecast-readiness", params={"at": "08:00"}).status_code == 422
    class BrokenSource:
        mode = "live"
        def window(self, *args):
            raise RuntimeError("https://source.invalid/secret-key/readings")
    monkeypatch.setattr(twin, "get_source", lambda: BrokenSource())
    response = client.get(f"/api/twin/facilities/{FACILITY}/forecast-readiness")
    assert response.status_code == 503 and "secret-key" not in response.text
