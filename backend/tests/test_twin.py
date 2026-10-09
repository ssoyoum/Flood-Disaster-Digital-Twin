"""Underpass control-decision twin: replay source, stage rule, backtest and API."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.twin import FACILITIES, ReplaySource, assess, backtest, facility_status, twin_mode

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"


def test_replay_mode_without_keys(monkeypatch):
    monkeypatch.delenv("HRFCO_API_KEY", raising=False)
    monkeypatch.delenv("FLOODOPS_TWIN_MODE", raising=False)
    mode = twin_mode()
    assert mode["mode"] == "replay" and mode["hrfco_key_configured"] is False


def test_stage_rule_before_and_after_the_planned_flood_level():
    facility = FACILITIES[FACILITY]
    source = ReplaySource()
    early = assess(facility, source.window("3011665", datetime(2023, 7, 15, 3, 0), 120), datetime(2023, 7, 15, 3, 0))
    assert early["stage"] == "advisory" and early["recommendation"] == "MONITOR"
    assert early["minutes_to_planned_flood"] and early["minutes_to_planned_flood"] > 60
    late = assess(facility, source.window("3011665", datetime(2023, 7, 15, 8, 0), 120), datetime(2023, 7, 15, 8, 0))
    assert late["stage"] == "planned_flood" and late["recommendation"] == "CLOSURE_REVIEW"
    assert late["minutes_to_planned_flood"] == 0 and late["reference_minutes_to_inflow"] == 27


def test_backtest_fires_before_the_official_requirement_time():
    result = backtest(FACILITY)
    fired = datetime.fromisoformat(result["first_closure_review"]["time"])
    assert fired <= datetime(2023, 7, 15, 6, 50)
    assert result["lead_minutes"]["underpass_inflow"] >= 97
    assert result["lead_minutes"]["levee_failure"] >= 79
    stages = [t["stage"] for t in result["stage_transitions"]]
    assert stages.index("planned_flood") > stages.index("warning") > stages.index("advisory")


def test_twin_api_lists_facility_status_and_backtest():
    listed = client.get("/api/twin/facilities").json()
    assert listed[0]["id"] == FACILITY and listed[0]["gauge"]["station_id"] == "3011665"
    status = client.get(f"/api/twin/facilities/{FACILITY}/status", params={"at": "2023-07-15T06:50:00"}).json()
    assert status["stage"] == "planned_flood" and status["recommendation"] == "CLOSURE_REVIEW"
    assert status["observation"]["water_level_el_m"] == 29.023
    assert status["mode"] in ("replay", "live")
    bt = client.get(f"/api/twin/facilities/{FACILITY}/backtest").json()
    assert bt["first_closure_review"] is not None
    assert client.get("/api/twin/facilities/nope/status").status_code == 404
