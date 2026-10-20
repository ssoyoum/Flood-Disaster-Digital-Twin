"""Underpass control-decision twin: replay source, stage rule, backtest and API."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.twin import FACILITIES, ReplaySource, _episode_quality, _history_series, _review_flags, _series_quality, assess, backtest, criteria_review, facility_status, twin_mode

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


def test_history_series_covers_2019_to_2026_and_matches_the_event_csv():
    series = _history_series(FACILITIES[FACILITY]["history_series"])
    assert len(series) == 409152 and series[0][0] == datetime(2019, 1, 1) and series[-1][0] == datetime(2026, 10, 12, 7, 50)
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
    assert len(result["sweep"]) == 12


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


def test_series_quality_flags_gaps_and_steps_without_removing_readings():
    start = datetime(2025, 7, 1)
    levels = [1.0, 1.1, 1.5, 1.1]  # +0.4 m and -0.4 m steps between consecutive 10-minute readings
    series = tuple((start + timedelta(minutes=10 * i), wl) for i, wl in enumerate(levels)) + ((start + timedelta(minutes=70), 1.1),)
    quality = _series_quality(series)
    assert quality["present_slots"] == 5 and quality["expected_slots"] == 8 and quality["missing_slots"] == 3
    assert quality["gaps"] == [{"after": "2025-07-01T00:30:00", "before": "2025-07-01T01:10:00", "missing_slots": 3}]
    assert [s["time"] for s in quality["step_reviews"]] == ["2025-07-01T00:20:00", "2025-07-01T00:30:00"]
    # An episode is flagged when the readings that drove it (one assess window before its start) carry a flag.
    near = {"start": "2025-07-01T02:30:00", "end": "2025-07-01T02:40:00"}  # window from 00:30: the second step and the gap
    far = {"start": "2025-07-01T05:00:00", "end": "2025-07-01T05:30:00"}
    assert _episode_quality(near, quality) == {"step_reviews": 1, "missing_slots": 3}
    assert _episode_quality(far, quality) == {"step_reviews": 0, "missing_slots": 0}


def test_criteria_review_reports_history_quality():
    result = criteria_review(FACILITY)
    quality = result["quality"]
    excluded = sum(q["readings_excluded"] for q in quality["quarantines"])
    assert quality["policy_found"] and quality["present_slots"] == result["coverage"]["rows"] + excluded
    assert quality["expected_slots"] == quality["present_slots"] + quality["missing_slots"]
    assert all(abs(s["change_m"]) >= quality["step_review_threshold_m"] for s in quality["step_reviews"])
    assert all("quality_review_required" in e for e in result["episodes"])
    # The 2023-05-16 step fault (1.51 m -> 11.26 m in 10 minutes, peak 13.28 m) is quarantined, so it never becomes a review episode.
    assert [q["id"] for q in quality["quarantines"]] == ["mihoganggyo_20230516_research_quarantine"] and excluded == 67
    assert not any(e["start"].startswith("2023-05-16") for e in result["episodes"])
    assert any(s["quarantined"] for s in quality["step_reviews"]) and result["other_episode_count"] == 0


def test_decision_request_takes_a_second_checker():
    from app.decision_log import DecisionRecordCreate

    request = DecisionRecordCreate(checked_by=" 상행 당직 ", checked_by_down=" 하행 당직 ", confirmation="CONFIRMED", acknowledged=True)
    assert (request.checked_by, request.checked_by_down) == ("상행 당직", "하행 당직")
    assert DecisionRecordCreate(checked_by="상행", confirmation="NO_ACTION", acknowledged=True).checked_by_down == ""


def test_osong_scorecard_carries_the_official_timeline():
    from app import case_validation as cv

    osong = next(c for c in cv.scorecard()["cases"] if c["id"] == "osong-2023")
    assert [e["at"][11:] for e in osong["official_events"]] == ["17:20", "04:10", "06:34", "06:40", "08:27", "08:40"]
    assert osong["official_events_source"].startswith("https://www.opm.go.kr/")
