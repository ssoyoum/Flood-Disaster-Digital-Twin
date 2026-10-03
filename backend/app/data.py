from copy import deepcopy

from .osong_repository import get_osong_event, get_osong_layers, get_osong_observations
from .timeline_cases import get_timeline_event, get_timeline_layers, is_timeline_case
from .seoul_repository import SEOUL_EVENT_ID, get_seoul_event, get_seoul_layers, get_seoul_observations


EVENT_ID = "osong-2023"

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}


def _pending_event(event_id: str, name: str, location: str, data_year: int, theme: str, focus_feature: str, analysis_flow: str) -> dict:
    return {
        "id": event_id,
        "name": name,
        "location": location,
        "data_year": data_year,
        "theme": theme,
        "focus_feature": focus_feature,
        "analysis_flow": analysis_flow,
        "source": "Scenario catalog only; processed layer connection pending",
        "started_at": f"{data_year}-01-01T00:00:00+09:00",
        "ended_at": f"{data_year}-01-02T00:00:00+09:00",
        "origin": "TEMPORARY",
        "data_status": "Catalog placeholder. Offline processed layers are not connected for this event yet.",
        "flood_extent": EMPTY_FEATURE_COLLECTION,
    }


EVENTS = [
    get_osong_event(),
    get_seoul_event(),
    get_timeline_event("pohang-2022"),
    _pending_event(
        "iksan-2024",
        "2024 Iksan Extreme Rainfall Flood",
        "Sanbukcheon basin (Nangsan, Mangseong), Iksan",
        2024,
        "Extreme Rain / Rural",
        "Farmland",
        "Extreme rainfall -> drainage and small stream capacity exceedance -> rural housing, farmland, roads",
    ),
    get_timeline_event("andong-uiseong-2026"),
]


def _legacy_layer(name: str) -> dict:
    return {"type": "FeatureCollection", "features": []}


ROADS = _legacy_layer("roads")
BUILDINGS = _legacy_layer("buildings")
INFRASTRUCTURE = _legacy_layer("infrastructure")
SHELTERS = _legacy_layer("shelters")


EVENT_OBSERVATIONS = {EVENT_ID: get_osong_observations(), SEOUL_EVENT_ID: get_seoul_observations()}
OBSERVATIONS = []


def get_events() -> list[dict]:
    return deepcopy(EVENTS)


def get_event(event_id: str = EVENT_ID) -> dict:
    return deepcopy(next(event for event in EVENTS if event["id"] == event_id))


def get_layers(event_id: str = EVENT_ID, layer_year: int = 2023) -> dict:
    if event_id == EVENT_ID:
        return deepcopy(get_osong_layers(layer_year))
    if event_id == SEOUL_EVENT_ID:
        return deepcopy(get_seoul_layers())
    if is_timeline_case(event_id):
        return deepcopy(get_timeline_layers(event_id))
    return {
        "aoi": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "roads": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "buildings": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "waterways": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "terrain": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "facilities": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "underpass": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
        "flood_extent": {"data": EMPTY_FEATURE_COLLECTION, "status": "UNAVAILABLE", "feature_count": 0},
    }
