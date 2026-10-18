"""Facility risk by flood driver: river stage for river-type facilities, local rain totals for pluvial underpasses."""

import pytest

from app import facility_risk as fr

AT = "2023-07-15T06:00:00"


@pytest.fixture(autouse=True)
def replay(monkeypatch):
    monkeypatch.setenv("FLOODOPS_TWIN_MODE", "replay")


def test_river_type_underpasses_meet_the_research_conditions():
    grades = fr.river_type_underpasses()
    assert grades and {g["grade"] for g in grades.values()} <= {"A", "B"}
    assert all(g["same_river_m"] <= fr.SAME_RIVER_KM * 1000 and g["elevation_hint_m"] >= fr.ELEVATION_HINT_MIN_M for g in grades.values())
    assert all(g["years_warning"] >= 1 for g in grades.values() if g["grade"] == "A")


def test_driver_split_keeps_riverside_and_operational_on_the_river():
    catalog = {f["facility_id"]: f for f in fr.nw.facility_catalog()}
    assert fr.driver_of(catalog["gungpyeong2-underpass"])[0] == "river"
    assert fr.driver_of(catalog["underpass_coordinates:933"]) == ("river", "운영 시설과 같은 위치(중복 행)")
    riverside = next(f for f in catalog.values() if f["group"] == "riverside")
    assert fr.driver_of(riverside)[0] == "river"


def test_pluvial_levels_follow_the_kma_heavy_rain_amounts():
    assert fr._pluvial_level({"rain_3h_mm": 95, "rain_1h_mm": 40, "rain_10m_mm": None})[0] == 3
    assert fr._pluvial_level({"rain_3h_mm": 60, "rain_1h_mm": 20, "rain_10m_mm": None})[0] == 2
    assert fr._pluvial_level({"rain_3h_mm": 30, "rain_12h_mm": 120, "rain_1h_mm": 5, "rain_10m_mm": None})[0] == 2
    assert fr._pluvial_level({"rain_3h_mm": None, "rain_1h_mm": 16, "rain_10m_mm": None})[0] == 1
    assert fr._pluvial_level({"rain_3h_mm": 10, "rain_1h_mm": 3, "rain_10m_mm": None})[0] == 0
    assert fr._pluvial_level(None) == (0, "10 km 안 강우 관측 없음")


def test_replay_ranks_river_and_pluvial_facilities_together():
    data = fr.facility_risk(AT, limit=2000)
    rows = data["facilities"]
    assert data["counts"]["total"] == len(rows) and data["counts"]["by_driver"]["pluvial"] > data["counts"]["by_driver"]["river"]
    assert [r["level"] for r in rows] == sorted((r["level"] for r in rows), reverse=True)
    assert rows[0]["facility_id"] == "gungpyeong2-underpass" and rows[0]["level"] == 3
    pluvial = [r for r in rows if r["driver"] == "pluvial" and r["level"] >= 2]
    assert pluvial and all(r["minutes_to_planned_flood"] is None for r in pluvial)
    assert all((r["rain"].get("rain_3h_mm") or 0) >= fr.RAIN_3H_ADVISORY_MM or (r["rain"].get("rain_12h_mm") or 0) >= fr.RAIN_12H_ADVISORY_MM
               for r in pluvial)
    assert fr.facility_risk(AT, driver="pluvial", limit=5)["filter"]["driver"] == "pluvial"


def test_official_warning_lifts_river_type_facilities_and_is_shown():
    data = fr.facility_risk(AT, limit=2000)
    gungpyeong = next(r for r in data["facilities"] if r["facility_id"] == "gungpyeong2-underpass")
    assert gungpyeong["official"]["level"] == "warning" and gungpyeong["official"]["issued_at"] == "2023-07-15T04:10"
    assert gungpyeong["why"].startswith("공식 홍수경보 중(발령 04:10")
    lifted = [r for r in data["facilities"] if r["official"]]
    assert lifted and all(r["driver"] == "river" and r["level"] >= fr.OFFICIAL_LEVEL[r["official"]["level"]] for r in lifted)
    assert data["counts"]["under_official"] == len(lifted) and data["counts"]["official_gauges"]["warning"] >= 2
    mannyeon = next(r for r in lifted if r["official"]["issued_at"] == "2023-07-14T14:20")
    assert "발령 7.14 14:20" in mannyeon["why"]  # a day-old issuance carries its date
    assert not any(r["official"] for r in fr.facility_risk("2023-07-14T12:00:00", limit=2000)["facilities"]
                   if r["facility_id"] == "gungpyeong2-underpass")
