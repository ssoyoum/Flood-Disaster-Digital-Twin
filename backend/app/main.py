import gzip
import json
import threading
import os
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .agent_tools import (
    execute_agent_tool,
    execute_agent_workflow,
    list_agent_tools,
    list_example_questions,
    plan_agent_intent,
)
from .agent_runner import ask_agent
from .hand_sensitivity import analyze_hand_threshold
from .rate_limit import agent_limiter, client_key
from .llm_planner import LlmPlannerUnavailable, llm_planner_model_id, llm_planner_status, plan_with_llm
from .data import EVENT_ID, EVENT_OBSERVATIONS, OBSERVATIONS, get_event, get_events, get_layers
from .osong_repository import SAFEMAP_WMS_SNAPSHOT, get_osong_data_status, get_osong_reconstruction, get_osong_summary
from .seoul_repository import (
    SEOUL_EVENT_ID,
    analyze_alert_timing,
    analyze_storage_capture,
    get_seoul_reconstruction,
    get_seoul_status,
    get_seoul_summary,
)
from .case_comparison import get_case_lead_times
from .twin import FACILITIES as TWIN_FACILITIES, backtest as twin_backtest, facility_status as twin_facility_status, list_facilities as twin_list_facilities, twin_mode
from . import agent_facility
from .water_level_bridge import readiness as water_level_readiness
from .rise_model import forecast as rise_forecast
from .layer_payload import slim_layers
from .timeline_cases import (
    analyze_response_timing,
    get_timeline_reconstruction,
    get_timeline_status,
    get_timeline_summary,
    is_timeline_case,
)
from .scenario_repository import create_scenario as save_scenario, get_scenario, mark_completed, mark_unavailable
from .schemas import (
    AlertTimingRequest,
    ResponseTimingRequest,
    StorageCaptureRequest,
    ClosureTimingRequest,
    ClosureTimingResult,
    ExposureInventoryResult,
    AgentExampleQuestion,
    AgentAskRequest,
    AgentAskResult,
    AgentIntentPlanRequest,
    AgentIntentPlanResult,
    AgentToolCallRequest,
    AgentToolCallResult,
    AgentToolDescriptor,
    AgentWorkflowRequest,
    AgentWorkflowResult,
    InflowDelayRequest,
    InflowDelayResult,
    HandThresholdRequest,
    HandThresholdResult,
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
    analyze_inflow_delay,
    build_exposure_inventory,
    apply_intervention,
    calculate_baseline,
    run_scenario,
    validate_scenario_buildings,
)


def _require_agent_scope(event_id: str, facility_id: str | None, observation_at: str | None = None) -> None:
    if facility_id is None:
        if observation_at is not None:
            raise HTTPException(status_code=422, detail="Select a facility before setting observation_at.")
        return
    try:
        agent_facility.require_facility(facility_id, event_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown Agent facility")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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


class _GZipExceptLayers:
    """Compress JSON responses, except layers, which are served pre-compressed."""

    def __init__(self, app):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=1024)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].endswith("/layers"):
            await self.app(scope, receive, send)
            return
        await self.gzip(scope, receive, send)


app.add_middleware(_GZipExceptLayers)


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
    if event_id == SEOUL_EVENT_ID:
        return get_seoul_status()
    if is_timeline_case(event_id):
        return get_timeline_status(event_id)
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


@lru_cache(maxsize=8)
def _layers_json(event_id: str, layer_year: int) -> bytes:
    # get_layers deep-copies ~30 MB of GeoJSON; serialising it once keeps repeat requests from blocking others.
    # Only the properties the consoles read are sent; see layer_payload for what is dropped and why.
    return json.dumps(slim_layers(get_layers(event_id, layer_year)), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@lru_cache(maxsize=8)
def _layers_gzip(event_id: str, layer_year: int) -> bytes:
    # Compressing ~30 MB takes seconds on the 1 vCPU demo server, so do it once per layer set.
    return gzip.compress(_layers_json(event_id, layer_year), compresslevel=6)


@app.on_event("startup")
def _warm_layer_cache() -> None:
    # Build the default layer payload in the background so the first visitor after a restart does not wait.
    threading.Thread(target=_layers_gzip, args=(EVENT_ID, 2023), daemon=True).start()


@app.get("/api/events/{event_id}/layers")
def event_layers(event_id: str, request: Request, layer_year: int = 2023):
    _require_event(event_id)
    if "gzip" in request.headers.get("accept-encoding", "").lower():
        return Response(
            content=_layers_gzip(event_id, layer_year),
            media_type="application/json",
            headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"},
        )
    return Response(content=_layers_json(event_id, layer_year), media_type="application/json")


@app.get("/api/events/{event_id}/summary")
def event_summary(event_id: str):
    _require_event(event_id)
    if event_id == EVENT_ID:
        return get_osong_summary()
    if event_id == SEOUL_EVENT_ID:
        return get_seoul_summary()
    if is_timeline_case(event_id):
        return get_timeline_summary(event_id)
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
    if event_id == SEOUL_EVENT_ID:
        return get_seoul_reconstruction()
    if is_timeline_case(event_id):
        return get_timeline_reconstruction(event_id)
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
            reduction_percent=None,
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
    if result.status == "COMPLETED":
        mark_completed(scenario_id)
    else:
        mark_unavailable(scenario_id)
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


@app.post(
    "/api/events/{event_id}/analysis/inflow-delay",
    response_model=InflowDelayResult,
    tags=["analysis"],
)
def inflow_delay_analysis(event_id: str, request: InflowDelayRequest):
    """What-if B: shift inflow and downstream milestones by an assumed delay."""

    _require_event(event_id)
    try:
        return analyze_inflow_delay(event_id, request.delay_minutes)
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post(
    "/api/events/{event_id}/analysis/hand-threshold",
    response_model=HandThresholdResult,
    tags=["analysis"],
)
def hand_threshold_analysis(event_id: str, request: HandThresholdRequest):
    """Compare temporary HAND cells after an explicit threshold reduction."""

    _require_event(event_id)
    try:
        return analyze_hand_threshold(event_id, request.reduction_m)
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _require_seoul(event_id: str) -> None:
    _require_event(event_id)
    if event_id != SEOUL_EVENT_ID:
        raise HTTPException(status_code=404, detail="This analysis is only connected for seoul-2022")


@app.post("/api/events/{event_id}/analysis/alert-timing", tags=["analysis"])
def alert_timing_analysis(event_id: str, request: AlertTimingRequest):
    """Seoul what-if: alert lead time before the first rescue call under rainfall-threshold or fixed-time alerts."""

    _require_seoul(event_id)
    try:
        return analyze_alert_timing(request.station, request.thresholds_mm_per_hour, request.alert_times)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/events/{event_id}/analysis/storage-capture", tags=["analysis"])
def storage_capture_analysis(event_id: str, request: StorageCaptureRequest):
    """Seoul what-if: rain volume above drainage capacity that an assumed storage tunnel could hold."""

    _require_seoul(event_id)
    try:
        return analyze_storage_capture(
            request.station, request.storage_m3, request.capacity_mm_per_hour, request.catchment_area_km2, request.runoff_coefficient
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/events/{event_id}/analysis/response-timing", tags=["analysis"])
def response_timing_analysis(event_id: str, request: ResponseTimingRequest):
    """Timeline cases: minutes between an assumed response time and the reported milestones that followed."""

    _require_event(event_id)
    if not is_timeline_case(event_id):
        raise HTTPException(status_code=404, detail="Response-timing analysis is connected for pohang-2022 and andong-uiseong-2026")
    try:
        return analyze_response_timing(event_id, request.intervention_id, request.action_times)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/cases/lead-times", tags=["analysis"])
def case_lead_times():
    """Actual versus one registered counterfactual response time for every connected case."""

    return get_case_lead_times()


@app.get("/api/twin/facilities", tags=["twin"])
def twin_facilities():
    """Registered underpasses with their gauges and the current observation mode (replay or live)."""

    return twin_list_facilities()


@app.get("/api/twin/mode", tags=["twin"])
def twin_mode_status():
    return twin_mode()


@app.get("/api/twin/facilities/{facility_id}/status", tags=["twin"])
def twin_status(facility_id: str, at: str | None = Query(default=None, description="ISO time for replay mode; defaults to the configured replay 'now' or the real clock in live mode")):
    """Current stage, minutes to the planned flood level and the closure-review recommendation for one facility."""

    if facility_id not in TWIN_FACILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown facility: {facility_id}")
    try:
        return twin_facility_status(facility_id, at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # live source failure must not hide the facility
        raise HTTPException(status_code=503, detail=f"Observation source unavailable: {exc}") from exc


@app.get("/api/twin/facilities/{facility_id}/backtest", tags=["twin"])
def twin_backtest_route(facility_id: str):
    """Apply the facility's control rule to the stored 2023 series and report when it would have fired."""

    if facility_id not in TWIN_FACILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown facility: {facility_id}")
    return twin_backtest(facility_id)


@app.get("/api/twin/facilities/{facility_id}/forecast-readiness", tags=["twin"])
def twin_forecast_readiness(facility_id: str, at: str | None = None):
    """Real water-level lags and missing inputs for the external research model; not a forecast."""
    if facility_id not in TWIN_FACILITIES:
        raise HTTPException(status_code=404, detail="Unknown facility")
    try:
        return water_level_readiness(facility_id, at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Water-level research inputs unavailable") from exc


@app.get("/api/twin/facilities/{facility_id}/rise-forecast", tags=["twin"])
def twin_rise_forecast(facility_id: str, at: str | None = Query(default=None, description="ISO time; same convention as /status")):
    """6-hour maximum rise predicted by the model retrained on real HRFCO stations. Research card; never feeds the recommendation."""

    if facility_id not in TWIN_FACILITIES:
        raise HTTPException(status_code=404, detail=f"Unknown facility: {facility_id}")
    try:
        return rise_forecast(facility_id, at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Rise forecast unavailable: {exc}") from exc


@app.get("/api/agent/tools", response_model=list[AgentToolDescriptor], tags=["agent"])
def agent_tools(event_id: str = "osong-2023", facility_id: str | None = None):
    """List the deterministic tools currently available to the Agent layer."""

    _require_event(event_id)
    _require_agent_scope(event_id, facility_id)
    return list_agent_tools(event_id, facility_id)


@app.post(
    "/api/agent/tools/{tool_name}",
    response_model=AgentToolCallResult,
    tags=["agent"],
)
def run_agent_tool(tool_name: str, request: AgentToolCallRequest):
    """Execute one registered analysis/data tool without LLM-side invention."""

    _require_event(request.event_id)
    _require_agent_scope(request.event_id, request.facility_id, request.observation_at)
    try:
        result = execute_agent_tool(tool_name, request.event_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AgentToolCallResult(tool_name=tool_name, event_id=request.event_id, result=result)


@app.post(
    "/api/agent/ask",
    response_model=AgentAskResult,
    tags=["agent"],
)
def ask_agent_question(request: AgentAskRequest, http_request: Request):
    """Let Gemini choose registered tools iteratively and explain their evidence."""

    _require_event(request.event_id)
    _require_agent_scope(request.event_id, request.facility_id, request.observation_at)
    agent_limiter.check(client_key(http_request))
    return ask_agent(request)


@app.post(
    "/api/agent/plan",
    response_model=AgentIntentPlanResult,
    tags=["agent"],
)
def plan_agent(request: AgentIntentPlanRequest, http_request: Request):
    """Convert supported natural-language intent into a non-executing plan."""

    _require_event(request.event_id)

    if request.planner in {"auto", "llm"}:
        agent_limiter.check(client_key(http_request))
        try:
            plan = plan_with_llm(request)
        except (LlmPlannerUnavailable, ValueError) as exc:
            failure = str(exc)
        except Exception as exc:  # An SDK or network failure must not break planning.
            failure = f"The LLM planner raised {type(exc).__name__}: {exc}"
        else:
            return {
                **plan,
                "planner_used": "llm",
                "planner_note": (
                    f"Routed by {llm_planner_model_id()}. The model only selected the workflow and "
                    "extracted parameters; every reported value comes from the tool layer."
                ),
            }
        if request.planner == "llm":
            raise HTTPException(status_code=503, detail=f"LLM planner unavailable. {failure}")
        note = f"Fell back to the deterministic planner. {failure}"
    else:
        note = "Deterministic planner was requested."

    return {**plan_agent_intent(request), "planner_used": "deterministic", "planner_note": note}


@app.post(
    "/api/agent/workflows",
    response_model=AgentWorkflowResult,
    tags=["agent"],
)
def run_agent_workflow(request: AgentWorkflowRequest):
    """Run a registered multi-tool analysis workflow."""

    _require_event(request.event_id)
    try:
        return execute_agent_workflow(request)
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/api/events/{event_id}/exposure-inventory",
    response_model=ExposureInventoryResult,
    tags=["analysis"],
)
def exposure_inventory(
    event_id: str,
    radii_m: list[int] = Query(default=[300, 500, 1000, 2000], max_length=10),
):
    """Path A: inventory inside rings around the event focus feature.

    Independent of the reconstruction envelope. See DQ-008 and D-014.
    """

    _require_event(event_id)
    if event_id == SEOUL_EVENT_ID or is_timeline_case(event_id):
        # Seoul and the timeline cases have no single focus feature, and its building layer holds only trace-overlay buildings.
        raise HTTPException(
            status_code=404,
            detail="No focus feature is defined for seoul-2022; use the official flood-trace exposure in /reconstruction instead",
        )
    try:
        return build_exposure_inventory(event_id, radii_m)
    except ReconstructionUnavailable as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get(
    "/api/agent/examples",
    response_model=list[AgentExampleQuestion],
    tags=["agent"],
)
def agent_examples(event_id: str = "osong-2023", facility_id: str | None = None):
    """Starter questions the registered tools can actually answer.

    The UI seeds its chips from here so an empty input box never invites a
    request the system has to refuse.
    """

    _require_event(event_id)
    _require_agent_scope(event_id, facility_id)
    return agent_facility.EXAMPLES if facility_id else list_example_questions(event_id)


@app.get("/api/agent/planner-status", tags=["agent"])
def agent_planner_status():
    """Report whether the LLM planner can run, without calling the API."""

    status = llm_planner_status()
    return {
        **status,
        "model": llm_planner_model_id(),
        "fallback": "deterministic",
        "note": (
            "The LLM only routes a request to a registered workflow and extracts parameters. "
            "Analysis values always come from the deterministic tool layer."
        ),
    }


_static_dir = os.getenv("FLOODOPS_STATIC_DIR")
if _static_dir:
    static_path = Path(_static_dir)
    if not (static_path / "index.html").is_file():
        raise RuntimeError(f"FLOODOPS_STATIC_DIR has no index.html: {static_path}")
    app.mount("/", StaticFiles(directory=static_path, html=True), name="frontend")
