"""Validation cases: the stored scorecard and the pieces it is built from."""

from fastapi.testclient import TestClient

from app import case_validation as cv
from app.main import app


def _signal(item, label):
    return next(s for s in item["signals"] if s["signal"] == label)


def test_official_firsts_count_an_issuance_active_at_the_window_start():
    firsts = cv._official_firsts("3011665", "2023-07-15T00:00", "2023-07-15T08:40")
    assert firsts["advisory"]["issued_at"] == "2023-07-14T17:20"  # 주의보 still active at 00:00
    assert firsts["warning"]["issued_at"] == "2023-07-15T04:10"
    assert cv._official_firsts("3009670", "2023-07-14T00:00", "2023-07-14T08:00") == {"advisory": None, "warning": None}


def test_verdict_never_claims_more_than_the_reference_precision():
    assert cv._verdict(71, "upper_bound", "control") == "실제 통제 보도 시각보다 71분 먼저"
    assert cv._verdict(-99, "upper_bound", "control") == "실제 통제 보도 시각보다 99분 늦음, 그 전에 이미 통제 중"
    assert cv._verdict(-30, "approximate", "control") == "실제 통제보다 약 30분 늦음"
    assert cv._verdict(None, "minute", "inflow") == "구간 안에서 울리지 않음(유입까지)"


def test_stored_scorecard_matches_the_cases():
    data = cv.scorecard()
    assert [c["id"] for c in data["cases"]] == [c["id"] for c in cv.CASES]
    assert all("timeline" not in c for c in data["cases"])
    osong = cv.scorecard("osong-2023")
    assert _signal(osong, "공식 홍수경보")["at"] == "2023-07-15T04:10" and _signal(osong, "공식 홍수경보")["lead_min"] == 257
    assert _signal(osong, "궁평2지하차도 경계 이상")["lead_min"] > 0 and osong["timeline"]


def test_daejeon_2023_shows_the_rule_was_later_than_the_real_control():
    item = cv.scorecard("daejeon-2023-07-14")
    assert item["region_at_reference"]["advisory_or_above"] == 0  # 05:30: nothing up yet when the city closed the riverbed roads
    assert _signal(item, "대전 시설 중 첫 주의 이상")["lead_min"] < 0
    assert _signal(item, "공식 홍수주의보")["at"] == "2023-07-14T08:50"


def test_stored_scorecard_still_matches_the_current_rule(monkeypatch):
    """A short replay around the 2024 warning must give the stored first times; rebuild the scorecard if this fails."""
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")
    stored = {s["signal"]: s["at"] for s in cv.scorecard("daejeon-2024-07-10")["signals"]}
    fresh = {s["signal"]: s["at"] for s in cv.compute("daejeon-2024-07-10", start="2024-07-10T05:00", end="2024-07-10T05:30")["signals"]}
    assert fresh["공식 홍수경보"] == stored["공식 홍수경보"] == "2024-07-10T05:20"
    assert fresh["만년지하차도 경계 이상"] == stored["만년지하차도 경계 이상"] == "2024-07-10T05:20"


def test_routes_serve_the_scorecard_and_reject_unknown_cases():
    client = TestClient(app)
    assert client.get("/api/watch/validation-cases").json()["cases"][0]["id"] == "osong-2023"
    assert client.get("/api/watch/validation-cases/daejeon-2020-07-30").json()["reference"]["precision"] == "upper_bound"
    assert client.get("/api/watch/validation-cases/nowhere").status_code == 404
