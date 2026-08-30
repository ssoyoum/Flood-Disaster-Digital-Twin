import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data import EVENT_ID, EVENT_OBSERVATIONS, OBSERVATIONS, get_event, get_events, get_layers
from .osong_repository import get_osong_data_status, get_osong_summary
from .schemas import Intervention, ScenarioRequest, ScenarioResult
from .services import apply_intervention, calculate_baseline


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


@app.post("/api/scenarios", response_model=ScenarioResult)
def create_scenario(request: ScenarioRequest):
    _require_event(request.event_id)
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
        name=request.name,
        intervention=intervention,
        baseline=baseline_result,
        result=result,
        reduction_percent=0.0,
        assumptions=assumptions,
    )
