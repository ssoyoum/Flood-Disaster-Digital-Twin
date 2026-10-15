"""Facility registry: operational entries, generated candidates, registration gates and the API gate."""

import copy
import json

import pytest
from fastapi.testclient import TestClient

from app import facility_registry
from app.main import app
from app.twin import FACILITIES

client = TestClient(app)
FACILITY = "gungpyeong2-underpass"


def test_registry_loads_the_operational_facility_with_its_gates():
    operational = facility_registry.operational()
    assert list(operational) == [FACILITY]
    assert FACILITIES is operational  # twin.py keeps the same dict
    entry = operational[FACILITY]
    assert entry["status"] == "OPERATIONAL" and entry["region"] == "충청북도 청주시"
    assert entry["gauge"]["station_id"] == "3011665" and entry["gauge"]["levels_m"]["planned_flood"] == 9.38
    assert entry["control_rule"]["id"] == "river_stage_v1"
    assert entry["gates"]["site_instrumentation"]["status"] == "MISSING"
    assert {g: v["status"] for g, v in entry["gates"].items() if g != "site_instrumentation"} == {"inflow_path": "CONFIRMED", "representative_gauge": "CONFIRMED", "validation_event": "CONFIRMED"}
    assert facility_registry.unmet_gates(entry) == ["site_instrumentation"]
    assert [g["id"] for g in facility_registry.gate_definitions()] == list(facility_registry.GATE_IDS)


def test_candidates_are_all_candidate_status_without_thresholds():
    candidates = facility_registry.candidates()
    assert len(candidates) >= 3
    ids = {c["id"] for c in candidates}
    assert {"cb-519-osong-biopolis", "cb-521-yongam", "cb-523-hakpyeong"} <= ids
    assert FACILITY not in ids
    for c in candidates:
        assert c["status"] == "CANDIDATE" and c["driver"] == "unverified"
        assert c["gauge"] is None and c["control_rule"] is None and c["reference_event"] is None
        assert set(c["gates"]) == set(facility_registry.GATE_IDS)
        assert c["gates"]["validation_event"]["status"] == "UNKNOWN"
        assert "CONFIRMED" not in {g["status"] for g in c["gates"].values()}
        assert facility_registry.get(c["id"]) is c or facility_registry.get(c["id"])["id"] == c["id"]
    # A PENDING representative gauge must be backed by a flood-forecast gauge within 5 km, never by a copied threshold.
    for c in candidates:
        pending = c["gates"]["representative_gauge"]["status"] == "PENDING"
        backed = any(g["flood_forecast_station"] and g["distance_km"] <= 5 for g in c["nearby_gauges"])
        assert pending == backed, c["id"]
    assert facility_registry.get("nope") is None


def test_candidates_file_matches_the_generator_header():
    payload = json.loads(facility_registry.CANDIDATES_FILE.read_text(encoding="utf-8"))
    assert payload["counts"]["candidates"] == len(payload["candidates"]) == len(facility_registry.candidates())
    assert payload["inputs"]["underpass_coordinates.csv"]["rows"] == 938
    assert payload["inputs"]["chungbuk_underpass_candidates.csv"]["rows"] == 32


def test_validator_rejects_an_operational_entry_with_an_unknown_gate():
    bad = copy.deepcopy(facility_registry.operational()[FACILITY])
    bad["gates"]["inflow_path"]["status"] = "UNKNOWN"
    with pytest.raises(ValueError, match=r"gungpyeong2-underpass: gates\.inflow_path"):
        facility_registry.validate_facility(bad)
    missing_level = copy.deepcopy(facility_registry.operational()[FACILITY])
    del missing_level["gauge"]["levels_m"]["severe"]
    with pytest.raises(ValueError, match=r"gauge\.levels_m.*severe"):
        facility_registry.validate_facility(missing_level)


def test_validator_rejects_a_candidate_that_sneaks_in_a_control_rule():
    bad = copy.deepcopy(facility_registry.candidates()[0])
    bad["control_rule"] = copy.deepcopy(facility_registry.operational()[FACILITY]["control_rule"])
    with pytest.raises(ValueError, match=rf"{bad['id']}: control_rule"):
        facility_registry.validate_facility(bad)
    with_gauge = copy.deepcopy(facility_registry.candidates()[0])
    with_gauge["gauge"] = {"station_id": "3011665", "levels_m": {"planned_flood": 9.38}}
    with pytest.raises(ValueError, match=r"gauge"):
        facility_registry.validate_facility(with_gauge)
    with pytest.raises(ValueError, match=r"status"):
        facility_registry.validate_facility({"id": "x", "status": "PILOT"})


def test_registry_api_counts_and_shapes():
    body = client.get("/api/twin/registry").json()
    assert [g["id"] for g in body["gates"]] == list(facility_registry.GATE_IDS)
    assert body["counts"] == {"operational": 1, "candidate": len(facility_registry.candidates())}
    assert len(body["operational"]) == 1 and len(body["candidates"]) == body["counts"]["candidate"]
    op = body["operational"][0]
    assert op["id"] == FACILITY and op["status"] == "OPERATIONAL" and op["event_id"] == "osong-2023"
    assert op["gauge"] == {"station_id": "3011665", "name": "청주시(미호강교)"}
    assert op["unmet_gates"] == ["site_instrumentation"]
    assert "levels_m" not in json.dumps(op)  # thresholds stay behind the per-facility endpoints
    for c in body["candidates"]:
        assert c["status"] == "CANDIDATE" and c["gauge"] is None and c["control_rule"] is None
        assert len(c["unmet_gates"]) == 4


def test_facilities_list_still_only_operational_and_carries_status_and_gates():
    listed = client.get("/api/twin/facilities").json()
    assert [f["id"] for f in listed] == [FACILITY]
    assert listed[0]["status"] == "OPERATIONAL"
    assert listed[0]["gates"]["site_instrumentation"]["status"] == "MISSING"
    assert listed[0]["gauge"]["station_id"] == "3011665"


def test_candidate_id_is_refused_with_409_and_unknown_stays_404():
    response = client.get("/api/twin/facilities/cb-519-osong-biopolis/status")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "FACILITY_NOT_OPERATIONAL" and detail["facility_id"] == "cb-519-osong-biopolis" and detail["status"] == "CANDIDATE"
    assert detail["unmet_gates"] == list(facility_registry.GATE_IDS)
    for route in ("backtest", "criteria-review", "forecast-readiness", "rise-forecast"):
        assert client.get(f"/api/twin/facilities/cb-521-yongam/{route}").status_code == 409, route
        assert client.get(f"/api/twin/facilities/nope/{route}").status_code == 404, route
