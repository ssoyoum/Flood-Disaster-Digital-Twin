from copy import deepcopy

from .osong_repository import get_osong_event, get_osong_layers, get_osong_observations


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
    _pending_event(
        "seoul-2022",
        "2022 Seoul Urban Flood",
        "Gangnam and Sillim, Seoul",
        2022,
        "Urban Flood",
        "Basement and underground spaces",
        "Rainfall -> drainage exceedance -> lowland flooding -> buildings, population, underground spaces, vulnerable groups",
    ),
    _pending_event(
        "pohang-2022",
        "2022 Pohang Typhoon Flood",
        "Naengcheon, Pohang",
        2022,
        "Typhoon + River Flood",
        "Industrial facilities",
        "Typhoon -> Naengcheon overflow -> apartments, underground parking, industrial facilities",
    ),
    _pending_event(
        "iksan-2024",
        "2024 Iksan Extreme Rainfall Flood",
        "Hamra, Iksan",
        2024,
        "Extreme Rain / Rural",
        "Farmland",
        "Extreme rainfall -> drainage and small stream capacity exceedance -> rural housing, farmland, roads",
    ),
    _pending_event(
        "andong-uiseong-2026",
        "2026 Andong-Uiseong Compound Flood",
        "Gwimi and Gugye, Andong-Uiseong",
        2026,
        "Compound Disaster",
        "Temporary housing and wildfire damaged areas",
        "Wildfire damaged area -> rainfall -> temporary housing, roads, water supply, repeated displacement",
    ),
]


def _legacy_layer(name: str) -> dict:
    return {"type": "FeatureCollection", "features": []}


ROADS = _legacy_layer("roads")
BUILDINGS = _legacy_layer("buildings")
INFRASTRUCTURE = _legacy_layer("infrastructure")
SHELTERS = _legacy_layer("shelters")


EVENT_OBSERVATIONS = {EVENT_ID: get_osong_observations()}
OBSERVATIONS = []


def get_events() -> list[dict]:
    return deepcopy(EVENTS)


def get_event(event_id: str = EVENT_ID) -> dict:
    return deepcopy(next(event for event in EVENTS if event["id"] == event_id))


def get_layers(event_id: str = EVENT_ID, layer_year: int = 2023) -> dict:
    if event_id == EVENT_ID:
        return deepcopy(get_osong_layers(layer_year))
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
