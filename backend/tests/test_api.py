import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_osong_event_is_default():
    response = client.get("/api/events")
    assert response.status_code == 200
    events = response.json()
    assert events[0]["id"] == "osong-2023"
    assert events[0]["origin"] == "DERIVED"


def test_osong_layers_use_processed_files():
    response = client.get("/api/events/osong-2023/layers")
    assert response.status_code == 200
    layers = response.json()
    assert layers["aoi"]["feature_count"] == 1
    assert layers["aoi"]["source_type"] == "OFFICIAL_ADMIN_BOUNDARY"
    assert layers["aoi"]["snapshot"] == "2023"
    assert layers["buildings"]["feature_count"] > 0
    assert layers["buildings"]["source_type"] == "OFFICIAL_BUILDING_INTEGRATED_INFORMATION"
    assert layers["buildings"]["snapshot"] == "2023-07-12"
    assert layers["roads"]["feature_count"] > 0
    assert layers["waterways"]["feature_count"] == 8
    assert layers["waterways"]["source_type"] == "OFFICIAL_RIVER_NETWORK"
    assert layers["waterways"]["snapshot"] == "NOT RECORDED"
    assert layers["terrain"]["feature_count"] == 303
    assert layers["terrain"]["source_type"] == "DEM_TERRAIN_CONTEXT"
    assert layers["approx_flood_envelope"]["status"] == "TEMPORARY"
    assert layers["approx_flood_envelope"]["source_type"] == "DERIVED_APPROXIMATION"
    assert layers["approx_flood_envelope"]["feature_count"] > 0
    assert layers["hand_reconstruction"]["status"] == "TEMPORARY"
    assert layers["hand_reconstruction"]["source_type"] == "DERIVED_APPROXIMATION"
    assert layers["hand_reconstruction"]["feature_count"] > layers["approx_flood_envelope"]["feature_count"]
    assert layers["facilities"]["feature_count"] == 386
    assert layers["underpass"]["feature_count"] == 1
    assert layers["underpass"]["data"]["features"][0]["geometry"]["type"] == "MultiLineString"


def test_osong_layers_ignore_current_osm_for_incident_analysis():
    response = client.get("/api/events/osong-2023/layers?layer_year=2026")
    assert response.status_code == 200
    layers = response.json()
    assert layers["buildings"]["source_type"] == "OFFICIAL_BUILDING_INTEGRATED_INFORMATION"
    assert layers["buildings"]["snapshot"] == "2023-07-12"
    assert layers["waterways"]["source_type"] == "OFFICIAL_RIVER_NETWORK"
    assert layers["waterways"]["snapshot"] == "NOT RECORDED"
    assert layers["waterways"]["feature_count"] == 8
    assert layers["terrain"]["feature_count"] == 303
    assert layers["approx_flood_envelope"]["status"] == "TEMPORARY"
    assert layers["hand_reconstruction"]["status"] == "TEMPORARY"
    assert layers["facilities"]["feature_count"] == 386


def test_osong_status_separates_source_types():
    response = client.get("/api/events/osong-2023/status")
    assert response.status_code == 200
    status = response.json()
    assert status["flood_extent"]["status"] == "TEMPORARY"
    assert status["safemap_floodmarks"]["status"] == "VERIFIED"
    assert status["safemap_floodmarks"]["source_type"] == "OFFICIAL_WMS_SNAPSHOT"
    assert status["safemap_floodmarks"]["data_vintage"] == "2024 collection"
    assert status["rainfall"]["source_type"] == "OBSERVATION"
    assert status["rainfall"]["status"] == "VERIFIED"
    assert status["water_level"]["source_type"] == "OBSERVATION"
    assert status["water_level"]["status"] == "VERIFIED"
    assert status["water_level"]["records"] == 1299
    assert status["population"]["status"] == "VERIFIED"
    assert status["dem"]["source_type"] == "DEM"
    assert status["dem"]["low_elevation_feature_count"] == 303
    assert status["layers"]["approx_flood_envelope"]["status"] == "TEMPORARY"
    assert status["layers"]["hand_reconstruction"]["status"] == "TEMPORARY"


def test_osong_timeline_uses_kma_observations():
    response = client.get("/api/events/osong-2023/flood/timeline")
    assert response.status_code == 200
    observations = response.json()
    assert len(observations) == 144
    assert observations[0]["station_id"] == "327"
    assert observations[0]["origin"] == "VERIFIED"
    assert observations[0]["unit"] == "mm"


def test_osong_summary_does_not_calculate_exposure_without_flood_extent():
    response = client.get("/api/events/osong-2023/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["official_population"] is not None
    assert summary["building_count"] > 0
    assert summary["road_count"] > 0
    assert summary["waterway_count"] == 8
    assert summary["terrain_low_elevation_cells"] == 303
    assert summary["terrain_low_elevation_threshold_m"] == 30.03
    assert summary["hand_reconstruction_features"] > 0
    assert summary["rainfall_records"] == 144
    assert summary["rainfall_peak_mm_per_hour"] is not None
    assert summary["water_level_peak_m"] is not None
    assert summary["primary_water_level_peak_m"] is not None
    assert summary["underpass_available"] is True
    assert summary["safemap_floodmarks_available"] is True
    assert summary["model_type"] == "Historical Disaster Reconstruction Digital Twin MVP"
    assert summary["response_window_min"] == 8
    assert summary["time_until_full_inundation_min"] == 13
    assert summary["exposed_population"] == "PENDING_FLOOD_EXTENT"
    assert summary["exposed_buildings"] == "PENDING_FLOOD_EXTENT"


def test_osong_reconstruction_serves_replay_and_rule_based_intervention():
    response = client.get("/api/events/osong-2023/reconstruction")
    assert response.status_code == 200
    reconstruction = response.json()
    assert reconstruction["model_type"] == "Historical Disaster Reconstruction Digital Twin MVP"
    assert len(reconstruction["replay"]) == 7
    assert reconstruction["baseline"]["failure_to_inflow_min"] == 18
    assert reconstruction["baseline"]["inflow_to_unsafe_min"] == 8
    assert reconstruction["intervention"]["type"] == "ROAD_CLOSURE"
    assert reconstruction["intervention"]["trigger"] == "underpass_water_depth >= 0.15 m"
    assert reconstruction["intervention"]["available_response_window_min"] == 8
    assert reconstruction["envelope_comparison"]["source_type"] == "DERIVED_COMPARISON"
    assert len(reconstruction["envelope_comparison"]["rows"]) == 7
    assert reconstruction["envelope_comparison"]["rows"][-1]["hand_area_km2"] > reconstruction["envelope_comparison"]["rows"][-1]["approx_area_km2"]
    assert any("not a calibrated 2D hydraulic model" in item for item in reconstruction["limitations"])


def test_osong_safemap_wms_snapshot_serves_local_png():
    response = client.get("/api/events/osong-2023/flood/safemap-wms-snapshot.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_baseline_uses_pending_exposure_metrics():
    response = client.get("/api/scenarios/baseline?event_id=osong-2023")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["event_id"] == "osong-2023"
    assert result["exposed_population"] == "PENDING_FLOOD_EXTENT"


def test_road_closure_intervention_returns_rule_based_auto_closure():
    response = client.post(
        "/api/scenarios",
        json={"name": "Auto closure", "intervention_type": "ROAD_CLOSURE", "event_id": "osong-2023"},
    )
    assert response.status_code == 200
    scenario = response.json()
    assert scenario["intervention"]["type"] == "ROAD_CLOSURE"
    assert scenario["result"]["intervention_state"] == "Scenario A: water-depth sensor + automatic entrance closure"
    assert scenario["result"]["response_window_min"] == 8
    assert scenario["result"]["exposed_population"] == "PENDING_FLOOD_EXTENT"
    assert any("water-depth sensor" in item for item in scenario["assumptions"])


def test_portfolio_scenario_can_be_created_and_run():
    created = client.post(
        "/api/scenarios",
        json={
            "name": "Osong building response drill",
            "building_ids": [1, 2, 3],
            "interventions": ["flood_barrier", "evacuation_support"],
            "event_id": "osong-2023",
        },
    )
    assert created.status_code == 200
    scenario = created.json()
    assert isinstance(scenario["scenario_id"], int)
    assert scenario["status"] == "DRAFT"
    assert scenario["building_ids"] == [1, 2, 3]

    result_response = client.post(f"/api/scenarios/{scenario['scenario_id']}/run")
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["status"] == "COMPLETED"
    assert result["before_priority_buildings"] >= result["after_priority_buildings"]
    assert 0 <= result["risk_reduction"] <= 1
    assert len(result["priority_building_ids_before"]) <= 3

    fetched = client.get(f"/api/scenarios/{scenario['scenario_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "COMPLETED"


def test_portfolio_scenario_rejects_unknown_building_id():
    response = client.post(
        "/api/scenarios",
        json={"building_ids": [999999], "interventions": ["flood_barrier"]},
    )
    assert response.status_code == 422
    assert "Unknown building_ids" in response.json()["detail"]


def test_closure_timing_whatif_compares_against_observed_timeline():
    response = client.post(
        "/api/events/osong-2023/analysis/closure-timing",
        json={"closure_times": ["08:25", "08:30", "08:35"]},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["analysis"] == "closure_timing_whatif"
    assert result["coverage_status"] == "fallback"
    assert result["detection_trigger_time"] == "2023-07-15T08:27:00+09:00"

    preemptive, at_inflow, at_unsafe = result["scenarios"]
    assert preemptive["classification"] == "BEFORE_UNDERPASS_INFLOW"
    assert preemptive["entry_blocked_before_inflow"] is True
    assert preemptive["minutes_before_underpass_inflow"] == 2
    assert preemptive["minutes_before_full_inundation"] == 15
    assert preemptive["lead_time_vs_detection_trigger_min"] == 2

    assert at_inflow["classification"] == "AFTER_INFLOW_BEFORE_UNSAFE_DRIVING"
    assert at_inflow["entry_blocked_before_inflow"] is False
    assert at_inflow["minutes_before_underpass_inflow"] == -3

    assert at_unsafe["classification"] == "AFTER_UNSAFE_DRIVING"
    assert at_unsafe["minutes_before_unsafe_driving"] == 0
    assert at_unsafe["state_at_closure"] == "unsafe_driving"


def test_closure_timing_does_not_estimate_casualties_or_damage():
    response = client.post("/api/events/osong-2023/analysis/closure-timing", json={})
    assert response.status_code == 200
    result = response.json()
    assert len(result["scenarios"]) == 3
    assert any("not a hydraulic or traffic simulation" in item for item in result["limitations"])
    assert any("casualty" in item for item in result["limitations"])


def test_closure_timing_rejects_unparsable_time():
    response = client.post(
        "/api/events/osong-2023/analysis/closure-timing",
        json={"closure_times": ["25:99"]},
    )
    assert response.status_code == 422
    assert "must be HH:MM" in response.json()["detail"]


def test_closure_timing_requires_connected_reconstruction():
    response = client.post(
        "/api/events/seoul-2022/analysis/closure-timing",
        json={"closure_times": ["08:25"]},
    )
    assert response.status_code == 404
    assert "not connected" in response.json()["detail"]


def test_inflow_delay_whatif_shifts_downstream_milestones():
    response = client.post(
        "/api/events/osong-2023/analysis/inflow-delay",
        json={"delay_minutes": [0, 5, 10]},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["analysis"] == "inflow_delay_whatif"
    assert result["coverage_status"] == "fallback"
    assert result["shifted_states"] == ["underpass_inflow", "unsafe_driving", "full_inundation"]

    baseline, five_min, ten_min = result["scenarios"]
    assert baseline["delay_minutes"] == 0
    assert baseline["milestones"][0]["shifted_time"] == "2023-07-15T08:27:00+09:00"
    assert five_min["delay_minutes"] == 5
    assert five_min["milestones"][0]["shifted_time"] == "2023-07-15T08:32:00+09:00"
    assert five_min["milestones"][2]["shifted_time"] == "2023-07-15T08:45:00+09:00"
    assert five_min["minutes_gained_before_full_inundation"] == 5
    assert ten_min["minutes_gained_before_unsafe_driving"] == 10


def test_inflow_delay_whatif_rejects_unphysical_input_range():
    response = client.post(
        "/api/events/osong-2023/analysis/inflow-delay",
        json={"delay_minutes": [-1]},
    )
    assert response.status_code == 422

    response = client.post(
        "/api/events/osong-2023/analysis/inflow-delay",
        json={"delay_minutes": [181]},
    )
    assert response.status_code == 422


def test_inflow_delay_whatif_requires_connected_reconstruction():
    response = client.post(
        "/api/events/seoul-2022/analysis/inflow-delay",
        json={"delay_minutes": [5]},
    )
    assert response.status_code == 404
    assert "not connected" in response.json()["detail"]


def test_agent_tools_expose_only_registered_domain_tools():
    response = client.get("/api/agent/tools")
    assert response.status_code == 200
    tools = response.json()
    assert [tool["name"] for tool in tools] == [
        "get_event",
        "get_reconstruction",
        "analyze_closure_timing",
        "analyze_inflow_delay",
        "get_exposure_inventory",
    ]
    assert "closure_times" in tools[2]["input_fields"]
    assert "delay_minutes" in tools[3]["input_fields"]
    assert "radii_m" in tools[4]["input_fields"]


def test_agent_tool_dispatches_inflow_delay_with_domain_result():
    response = client.post(
        "/api/agent/tools/analyze_inflow_delay",
        json={"event_id": "osong-2023", "delay_minutes": [5]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_name"] == "analyze_inflow_delay"
    assert payload["result"]["analysis"] == "inflow_delay_whatif"
    assert payload["result"]["scenarios"][0]["delay_minutes"] == 5
    assert payload["result"]["scenarios"][0]["milestones"][0]["shifted_by_min"] == 5


def test_agent_tool_rejects_unknown_tool():
    response = client.post(
        "/api/agent/tools/invent_flood_depth",
        json={"event_id": "osong-2023"},
    )
    assert response.status_code == 404
    assert "Unknown agent tool" in response.json()["detail"]


def test_agent_plan_extracts_closure_timing_without_executing_tools():
    response = client.post(
        "/api/agent/plan",
        json={
            "message": "오송 지하차도 08:25와 08:35 차단 시각을 비교해줘",
            "event_id": "osong-2023",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "READY"
    assert payload["workflow"] == "closure_timing"
    assert payload["parameters"]["closure_times"] == ["08:25", "08:35"]
    assert payload["tool_names"] == [
        "get_event",
        "get_reconstruction",
        "analyze_closure_timing",
    ]


def test_agent_plan_extracts_exposure_radius_and_preserves_boundary():
    response = client.post(
        "/api/agent/plan",
        json={"message": "지하차도 500m, 1000m 반경의 건물과 도로 재고를 보여줘"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "exposure_inventory"
    assert payload["parameters"]["radii_m"] == [500, 1000]
    assert payload["tool_names"] == ["get_event", "get_exposure_inventory"]
    assert any("does not execute" in item for item in payload["limitations"])


def test_agent_plan_requires_clarification_for_multiple_analysis_intents():
    response = client.post(
        "/api/agent/plan",
        json={"message": "차단 시각과 유입 지연을 같이 비교해줘"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "NEEDS_CLARIFICATION"
    assert payload["workflow"] is None
    assert payload["tool_names"] == []


def test_agent_plan_supports_situation_replay_and_rejects_unknown_intent():
    response = client.post(
        "/api/agent/plan",
        json={"message": "오송 침수 상황과 타임라인을 보여줘"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "situation"
    assert payload["tool_names"] == ["get_event", "get_reconstruction"]

    response = client.post(
        "/api/agent/plan",
        json={"message": "내일 강수량을 예측해줘"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "UNSUPPORTED"


def test_agent_situation_workflow_returns_reconstruction_context():
    response = client.post(
        "/api/agent/workflows",
        json={"workflow": "situation"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [call["tool_name"] for call in payload["tool_calls"]] == [
        "get_event",
        "get_reconstruction",
    ]
    assert payload["result"]["event_id"] == "osong-2023"


def test_agent_workflow_chains_context_and_analysis_tools():
    response = client.post(
        "/api/agent/workflows",
        json={
            "workflow": "closure_timing",
            "event_id": "osong-2023",
            "closure_times": ["08:25", "08:35"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "closure_timing"
    assert payload["status"] == "COMPLETED"
    assert [call["tool_name"] for call in payload["tool_calls"]] == [
        "get_event",
        "get_reconstruction",
        "analyze_closure_timing",
    ]
    assert payload["tool_calls"][1]["result_keys"]
    assert payload["result"]["analysis"] == "closure_timing_whatif"
    assert len(payload["result"]["scenarios"]) == 2
    assert payload["provenance"]
    assert payload["coverage_status"] == "fallback"


def test_agent_workflow_chains_inflow_delay_tool():
    response = client.post(
        "/api/agent/workflows",
        json={"workflow": "inflow_delay", "delay_minutes": [10]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [call["tool_name"] for call in payload["tool_calls"]][-1] == "analyze_inflow_delay"
    assert payload["result"]["scenarios"][0]["delay_minutes"] == 10


def test_agent_exposure_inventory_tool_preserves_dq008_boundary():
    response = client.post(
        "/api/agent/tools/get_exposure_inventory",
        json={"event_id": "osong-2023", "radii_m": [500]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["analysis"] == "exposure_inventory"
    assert payload["result"]["rings"][0]["radius_m"] == 500
    assert any("not a flood impact estimate" in item for item in payload["result"]["limitations"])


def test_agent_exposure_inventory_workflow_does_not_use_flood_envelope():
    response = client.post(
        "/api/agent/workflows",
        json={"workflow": "exposure_inventory", "radii_m": [300, 500]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [call["tool_name"] for call in payload["tool_calls"]] == [
        "get_event",
        "get_exposure_inventory",
    ]
    assert payload["result"]["analysis"] == "exposure_inventory"
    assert payload["provenance"]
    assert payload["coverage_status"] == "covered"


def test_exposure_inventory_is_independent_of_flood_envelope():
    response = client.get("/api/events/osong-2023/exposure-inventory")
    assert response.status_code == 200
    result = response.json()
    assert result["analysis"] == "exposure_inventory"
    assert result["coverage_status"] == "covered"
    assert result["focus_feature_layer"] == "underpass"

    radii = [ring["radius_m"] for ring in result["rings"]]
    assert radii == sorted(radii)
    buildings = [ring["buildings"] for ring in result["rings"]]
    roads = [ring["roads_km"] for ring in result["rings"]]
    assert buildings == sorted(buildings)
    assert roads == sorted(roads)
    assert buildings[0] > 0

    assert any("not a flood impact estimate" in item for item in result["limitations"])
    assert any("DQ-008" in item for item in result["limitations"])
    assert {source["key"] for source in result["inventory_sources"]} == {"buildings", "roads", "facilities"}


def test_exposure_inventory_accepts_custom_radii():
    response = client.get("/api/events/osong-2023/exposure-inventory?radii_m=250&radii_m=750")
    assert response.status_code == 200
    assert [ring["radius_m"] for ring in response.json()["rings"]] == [250, 750]


def test_exposure_inventory_rejects_out_of_range_radius():
    response = client.get("/api/events/osong-2023/exposure-inventory?radii_m=10")
    assert response.status_code == 422
    assert "between 50 and 20000" in response.json()["detail"]


def test_exposure_inventory_requires_focus_feature_layer():
    response = client.get("/api/events/seoul-2022/exposure-inventory")
    assert response.status_code == 404
    assert "focus feature" in response.json()["detail"]
