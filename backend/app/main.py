import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .data import EVENT_ID, EVENT_OBSERVATIONS, OBSERVATIONS, get_event, get_events, get_layers
from .osong_repository import SAFEMAP_WMS_SNAPSHOT, get_osong_data_status, get_osong_reconstruction, get_osong_summary
from .scenario_repository import create_scenario as save_scenario, get_scenario, mark_completed
from .schemas import (
    ClosureTimingRequest,
    ClosureTimingResult,
    Intervention,
    ScenarioCreateRequest,
    ScenarioIntervention,
    ScenarioRecord,
    ScenarioRequest,
    ScenarioResult,
    ScenarioRunResult,
)
from .services import (
    ReconstructionUnavailable,
    analyze_closure_timing,
    apply_intervention,
    calculate_baseline,
    run_scenario,
    validate_scenario_buildings,
)


app = FastAPI(title="FloodOps API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_event(event_id: str) -> None:
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")


@app.get("/health")
def health():
    return {"status": "ok", "backend": "ok", "database": "demo-in-memory", "postgis": "pending"}


@app.get("/api/events")
def events():
    keys = (
        "id",
        "name",
        "location",
        "data_year",
        "theme",
        "focus_feature",
        "analysis_flow",
        "source",
        "started_at",
        "ended_at",
        "origin",
        "data_status",
    )
    return [{key: event[key] for key in keys} for event in get_events()]


@app.get("/api/events/{event_id}")
def event(event_id: str):
    _require_event(event_id)
    return get_event(event_id)


@app.get("/api/events/{event_id}/status")
def event_status(event_id: str):
    _require_event(event_id)
    if event_id == EVENT_ID:
        return get_osong_data_status()
    return {"status": "UNAVAILABLE", "message": "Processed data is not connected for this event."}


@app.get("/api/events/{event_id}/flood")
def flood(event_id: str):
    _require_event(event_id)
    return get_event(event_id)["flood_extent"]


@app.get("/api/events/{event_id}/flood/safemap-wms-snapshot.png")
def safemap_wms_snapshot(event_id: str):
    _require_event(event_id)
    if event_id != EVENT_ID or not SAFEMAP_WMS_SNAPSHOT.exists():
        raise HTTPException(status_code=404, detail="Safemap WMS snapshot not found")
    return FileResponse(SAFEMAP_WMS_SNAPSHOT, media_type="image/png")


@app.get("/api/events/{event_id}/flood/timeline")
def timeline(event_id: str):
    _require_event(event_id)
    return EVENT_OBSERVATIONS.get(event_id, OBSERVATIONS)


@app.get("/api/events/{event_id}/layers")
def event_layers(event_id: str, layer_year: int = 2023):
    _require_event(event_id)
    return get_layers(event_id, layer_year)


@app.get("/api/events/{event_id}/summary")
def event_summary(event_id: str):
    _require_event(event_id)
    if event_id == EVENT_ID:
        return get_osong_summary()
    return {
        "event_id": event_id,
        "origin": "UNAVAILABLE",
        "data_status": "Processed data is not connected for this event.",
    }


@app.get("/api/events/{event_id}/reconstruction")
def event_reconstruction(event_id: str):
    _require_event(event_id)
    if event_id == EVENT_ID:
        return get_osong_reconstruction()
    raise HTTPException(status_code=404, detail="Reconstruction is not connected for this event")


@app.post("/api/integrations/safety-data/test")
async def test_safety_data_api(payload: dict):
    service_key = str(payload.get("service_key", "")).strip()
    if not service_key:
        raise HTTPException(status_code=400, detail="service_key is required")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://www.safetydata.go.kr/V2/api/DSSP-IF-00007", params={"serviceKey": service_key})
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Safety Data API request failed: {exc}") from exc
    header = body.get("header", {})
    result_code = str(header.get("resultCode", ""))
    return {
        "connected": result_code in {"00", "200"},
        "result_code": result_code,
        "message": header.get("resultMsg") or header.get("errorMsg") or "Safety Data API response received",
    }


@app.get("/api/events/{event_id}/infrastructure")
def event_infrastructure(event_id: str):
    _require_event(event_id)
    return get_layers(event_id)["facilities"]["data"]


@app.get("/api/infrastructure")
def infrastructure():
    return get_layers(EVENT_ID)["facilities"]["data"]


@app.get("/api/shelters")
def shelters():
    return {"type": "FeatureCollection", "features": []}


@app.get("/api/roads")
def roads():
    return get_layers(EVENT_ID)["roads"]["data"]


@app.get("/api/buildings")
def buildings():
    return get_layers(EVENT_ID)["buildings"]["data"]


@app.get("/api/scenarios/baseline")
def baseline(event_id: str = EVENT_ID):
    _require_event(event_id)
    return {"scenario_id": "baseline", "name": "Baseline Scenario", "result": calculate_baseline(event_id), "origin": "DERIVED"}


@app.post("/api/scenarios", response_model=ScenarioRecord | ScenarioResult, tags=["scenarios"])
def create_scenario(request: ScenarioCreateRequest):
    """Create a portfolio scenario without running it.

    The original single-intervention MVP payload remains supported for the
    existing UI. New clients should send ``building_ids`` and ``interventions``
    and then call ``POST /api/scenarios/{scenario_id}/run``.
    """

    _require_event(request.event_id)
    legacy_intervention_map: dict[str, ScenarioIntervention] = {
        "EVACUATION": "evacuation_support",
        "ROAD_CLOSURE": "road_closure",
        "SHELTER_OPEN": "evacuation_support",
        "TEMPORARY_BARRIER": "flood_barrier",
        "LEVEE_IMPROVEMENT": "levee_improvement",
        "INFRASTRUCTURE_PROTECTION": "infrastructure_protection",
    }

    # Backward-compatible path for the original UI and API contract.
    if not request.building_ids and not request.interventions and request.intervention_type:
        labels = {
            "EVACUATION": "Evacuation priority",
            "ROAD_CLOSURE": "Road closure",
            "SHELTER_OPEN": "Shelter opening",
            "TEMPORARY_BARRIER": "Temporary barrier",
            "LEVEE_IMPROVEMENT": "Levee improvement",
            "INFRASTRUCTURE_PROTECTION": "Infrastructure protection",
        }
        intervention = {
            "type": request.intervention_type,
            "label": labels[request.intervention_type],
            "description": "Future scenario metadata retained until official Flood Extent is connected.",
        }
        result, assumptions = apply_intervention(Intervention(**intervention), request.event_id)
        baseline_result = calculate_baseline(request.event_id)
        return ScenarioResult(
            scenario_id=f"scenario-{request.intervention_type.lower()}",
            name=request.name or f"{labels[request.intervention_type]} scenario",
            intervention=intervention,
            baseline=baseline_result,
            result=result,
            reduction_percent=0.0,
            assumptions=assumptions,
        )

    interventions = list(request.interventions)
    if request.intervention_type:
        interventions.append(legacy_intervention_map[request.intervention_type])
    if not request.building_ids:
        raise HTTPException(status_code=422, detail="building_ids must contain at least one building ID")
    if not interventions:
        raise HTTPException(status_code=422, detail="interventions must contain at least one intervention")
    try:
        validate_scenario_buildings(request.event_id, request.building_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return save_scenario(
        name=request.name,
        event_id=request.event_id,
        building_ids=request.building_ids,
        interventions=interventions,
    )


@app.get("/api/scenarios/{scenario_id}", response_model=ScenarioRecord, tags=["scenarios"])
def scenario(scenario_id: int):
    scenario_record = get_scenario(scenario_id)
    if not scenario_record:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario_record


@app.post("/api/scenarios/{scenario_id}/run", response_model=ScenarioRunResult, tags=["scenarios"])
def run_created_scenario(scenario_id: int):
    scenario_record = get_scenario(scenario_id)
    if not scenario_record:
        raise HTTPException(status_code=404, detail="Scenario not found")
    try:
        result = run_scenario(scenario_record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    mark_completed(scenario_id)
    return result


@app.post(
    "/api/events/{event_id}/analysis/closure-timing",
    response_model=ClosureTimingResult,
    tags=["analysis"],
)
def closure_timing_analysis(event_id: str, request: ClosureTimingRequest):
    """What-if A: compare underpass closure times against the observed timeline."""

    _require_event(event_id)
    try:
        return analyze_closure_timing(event_id, request.closure_times)
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
