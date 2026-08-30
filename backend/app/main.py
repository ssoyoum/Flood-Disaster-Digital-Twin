import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data import BUILDINGS, EVENT_ID, EVENT_OBSERVATIONS, INFRASTRUCTURE, OBSERVATIONS, ROADS, SHELTERS, get_event, get_events, get_layers
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "backend": "ok", "database": "demo-in-memory", "postgis": "pending"}


@app.get("/api/events")
def events():
    return [{key: event[key] for key in ("id", "name", "location", "data_year", "theme", "focus_feature", "analysis_flow", "source", "started_at", "ended_at", "origin", "data_status")} for event in get_events()]


@app.get("/api/events/{event_id}")
def event(event_id: str):
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return get_event(event_id)


@app.get("/api/events/{event_id}/flood")
def flood(event_id: str):
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return get_event(event_id)["flood_extent"]


@app.get("/api/events/{event_id}/flood/timeline")
def timeline(event_id: str):
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return EVENT_OBSERVATIONS.get(event_id, OBSERVATIONS)


@app.get("/api/events/{event_id}/layers")
def event_layers(event_id: str):
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return get_layers(event_id)


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
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return get_layers(event_id)["infrastructure"]


@app.get("/api/infrastructure")
def infrastructure():
    return INFRASTRUCTURE


@app.get("/api/shelters")
def shelters():
    return SHELTERS


@app.get("/api/roads")
def roads():
    return ROADS


@app.get("/api/buildings")
def buildings():
    return BUILDINGS


@app.get("/api/scenarios/baseline")
def baseline(event_id: str = EVENT_ID):
    if event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"scenario_id": "baseline", "name": "Baseline Scenario", "result": calculate_baseline(event_id), "origin": "DERIVED"}


@app.post("/api/scenarios", response_model=ScenarioResult)
def create_scenario(request: ScenarioRequest):
    if request.event_id not in {event["id"] for event in get_events()}:
        raise HTTPException(status_code=404, detail="Event not found")
    labels = {
        "EVACUATION": "대피 우선 배치",
        "ROAD_CLOSURE": "침수 도로 통제",
        "SHELTER_OPEN": "추가 대피소 개방",
        "TEMPORARY_BARRIER": "임시 방어시설",
        "LEVEE_IMPROVEMENT": "제방 개선",
        "INFRASTRUCTURE_PROTECTION": "핵심 시설 보호",
    }
    intervention = {
        "type": request.intervention_type,
        "label": labels[request.intervention_type],
        "description": "Baseline 조건에 개입을 적용한 데모 시나리오",
    }
    result, assumptions = apply_intervention(Intervention(**intervention), request.event_id)
    baseline_result = calculate_baseline(request.event_id)
    reduction = round((baseline_result.exposed_population - result.exposed_population) / baseline_result.exposed_population * 100, 1) if baseline_result.exposed_population else 0.0
    return ScenarioResult(
        scenario_id=f"scenario-{request.intervention_type.lower()}",
        name=request.name,
        intervention=intervention,
        baseline=baseline_result,
        result=result,
        reduction_percent=reduction,
        assumptions=assumptions,
    )
