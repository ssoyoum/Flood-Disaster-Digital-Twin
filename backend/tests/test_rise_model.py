"""6-hour rise forecast card: feature contract, guards, and the replay endpoint kept apart from the recommendation."""

import math
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import rise_model, twin
from app.main import app

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"
STATION = "3011665"
STATS = {"wl_median": {STATION: 1.5}, "rise_std": {STATION: 0.4}, "rise_q99": {STATION: 2.1}, "wl_fallback": 1.0}


def test_feature_vector_follows_the_training_contract():
    features = {"wl_t": 8.27, "wl_t_minus_1h": 7.57, "wl_t_minus_3h": 6.62, "wl_t_minus_6h": 6.58, "wl_t_minus_12h": 7.02, "wl_t_minus_24h": 6.5}
    x = rise_model.feature_vector(features, {"sfc_rain_1h": 10.0, "sfc_rain_6h": 60.0, "sfc_rain_24h": 150.0}, STATION, STATS)
    assert math.isclose(x["wl_change_1h"], 0.7) and math.isclose(x["wl_change_6h"], 1.69)
    assert math.isclose(x["wl_acceleration_3h"], 0.7 - 1.65 / 3)
    assert math.isclose(x["wl_observed_range_24h"], 8.27 - 6.5)
    assert math.isclose(x["sfc_rain_previous_1_to_6h"], 50.0) and math.isclose(x["sfc_rain_recent_share"], 10 / 61)
    assert math.isclose(x["wl_above_station_median"], 6.77) and x["station_rise_q99"] == 2.1
    # Unknown station: no median → fallback, no rise statistics → NaN (LightGBM treats it as missing).
    y = rise_model.feature_vector(features, {"sfc_rain_1h": None, "sfc_rain_6h": None, "sfc_rain_24h": None}, "0000000", STATS)
    assert math.isclose(y["wl_above_station_median"], 7.27) and math.isnan(y["station_rise_std"]) and math.isnan(y["sfc_rain_6h"])
    with pytest.raises(ValueError):
        rise_model.feature_vector({**features, "wl_t_minus_24h": None}, {}, STATION, STATS)


def test_rain_totals_need_a_complete_hourly_window():
    anchor = datetime(2023, 7, 15, 4, 0)
    rows = [{"time": anchor - timedelta(hours=h), "rainfall_mm": 5.0} for h in range(0, 6)]  # 6 hourly rows ending at the anchor
    totals = rise_model.rain_totals(rows, anchor)
    assert totals["sfc_rain_1h"] == 5.0 and totals["sfc_rain_6h"] == 30.0 and totals["sfc_rain_24h"] is None


def test_missing_lags_or_stale_observations_give_no_prediction(monkeypatch):
    class ShortSource:
        mode = "replay"

        def window(self, station_id, end, minutes):
            return [{"time": end - timedelta(minutes=10), "station_id": station_id, "water_level_m": 4.0}]

        def rain_window(self, station_id, end, minutes):
            return []

    monkeypatch.setattr(twin, "get_source", lambda: ShortSource())
    monkeypatch.setattr(rise_model, "load_model", lambda: (object(), STATS, {}))
    data = rise_model.forecast(FACILITY, "2023-07-15T04:00:00")
    assert data["prediction_available"] is False and data["reason"] == "MISSING_EXACT_LAGS"
    assert data["control_decision_usable"] is False and "recommendation" not in data
    monkeypatch.setattr(rise_model, "load_model", lambda: None)
    assert rise_model.forecast(FACILITY, "2023-07-15T04:00:00")["reason"] == "MODEL_NOT_AVAILABLE"


@pytest.mark.skipif(rise_model.load_model() is None, reason="trained model files or lightgbm not present")
def test_replay_forecast_on_2023_07_15_precedes_the_planned_flood_level(monkeypatch):
    monkeypatch.delenv("HRFCO_API_KEY", raising=False)
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")
    response = client.get(f"/api/twin/facilities/{FACILITY}/rise-forecast", params={"at": "2023-07-15T04:10:00"})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction_available"] is True and data["kind"] == "RESEARCH" and data["control_decision_usable"] is False
    assert data["maxrise_6h_m"] > 0.5 and data["forecast_level_m"] == round(data["inputs"]["water"]["wl_t"] + data["maxrise_6h_m"], 2)
    assert data["reaches_within_6h"]["warning"] is True  # 8.0 m was observed at 05:00; the forecast at 04:10 already says so
    assert data["model"]["stations"] >= 3 and data["inputs"]["rain"]["sfc_rain_6h"] is not None
    # The recommendation at the same time comes from the stage rule alone.
    status = client.get(f"/api/twin/facilities/{FACILITY}/status", params={"at": "2023-07-15T04:10:00"}).json()
    assert status["recommendation"] in {"MONITOR", "CLOSURE_REVIEW"} and "maxrise_6h_m" not in status
    assert client.get("/api/twin/facilities/nope/rise-forecast").status_code == 404
