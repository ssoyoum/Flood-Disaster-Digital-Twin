"""Underpass control-decision twin: replay source, stage rule, backtest and API."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.twin import FACILITIES, ReplaySource, _history_series, _review_flags, assess, backtest, criteria_review, facility_status, twin_mode

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


@pytest.mark.parametrize(("floor", "lead"), [("warning", 60), ("warning", 0), ("advisory", 120)])
def test_series_rule_matches_assess_row_by_row(floor, lead):
    facility = {**FACILITIES[FACILITY], "control_rule": {**FACILITIES[FACILITY]["control_rule"], "stage_floor": floor, "lead_threshold_min": lead}}
    rows = ReplaySource().series("3011665")
    series = tuple((r["time"], r["water_level_m"]) for r in rows)
    flags = _review_flags(series, facility["gauge"]["levels_m"], floor, lead, facility["control_rule"]["rate_window_min"])
    expected = [assess(facility, [r for r in rows if row["time"] - timedelta(minutes=120) <= r["time"] <= row["time"]], row["time"])["recommendation"] == "CLOSURE_REVIEW" for row in rows]
    assert flags == expected


def test_history_series_covers_eight_flood_seasons_and_matches_the_event_csv():
    series = _history_series(FACILITIES[FACILITY]["history_series"])
    assert len(series) == 140544 and series[0][0] == datetime(2019, 6, 1) and series[-1][0].year == 2026
    history = dict(series)
    for row in ReplaySource().series("3011665"):
        assert history[row["time"]] == row["water_level_m"]


def test_criteria_review_current_rule_lead_and_other_seasons():
    result = criteria_review(FACILITY)
    assert result["is_current_rule"] and result["params"] == {"stage_floor": "warning", "stage_floor_label": "경보 수위", "lead_threshold_min": 60, "rate_window_min": 30}
    assert result["first_review"]["time"] == backtest(FACILITY)["first_closure_review"]["time"] == "2023-07-15T05:50:00"
    assert result["lead_minutes"]["underpass_inflow"] == 157 and result["lead_minutes"]["official_requirement_met"] == 50
    assert result["other_episode_count"] == 0
    assert [y["year"] for y in result["by_year"]] == list(range(2019, 2027))
    assert len(result["sweep"]) == 8


def test_earlier_criteria_trade_lead_time_for_a_2025_review_episode():
    planned_only = criteria_review(FACILITY, "warning", 0)
    assert planned_only["first_review"]["time"] == "2023-07-15T06:50:00" and planned_only["lead_minutes"]["underpass_inflow"] == 97
    early = criteria_review(FACILITY, "warning", 120)
    assert early["lead_minutes"]["underpass_inflow"] == 227 and not early["is_current_rule"]
    others = [e for e in early["episodes"] if not e["reference_event"]]
    assert len(others) == 1 and others[0]["start"].startswith("2025-07-17") and others[0]["peak_stage"] == "warning"
    assert next(y for y in early["by_year"] if y["year"] == 2025)["episodes"] == 1


def test_criteria_review_api_validates_parameters():
    url = f"/api/twin/facilities/{FACILITY}/criteria-review"
    body = client.get(url, params={"stage_floor": "advisory", "lead_threshold_min": 180}).json()
    assert body["params"]["stage_floor"] == "advisory" and body["first_review"]["time"] == "2023-07-15T04:10:00"
    assert client.get(url, params={"stage_floor": "severe"}).status_code == 422
    assert client.get(url, params={"lead_threshold_min": 361}).status_code == 422
    assert client.get("/api/twin/facilities/nope/criteria-review").status_code == 404
