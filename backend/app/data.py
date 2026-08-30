import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path


EVENT_ID = "osong-2023"

_FLOOD_POLYGON = {
    "type": "Feature",
    "properties": {"name": "Demo flood extent", "origin": "SIMULATED"},
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[126.965, 37.515], [126.965, 37.535], [127.005, 37.535], [127.005, 37.515], [126.965, 37.515]]],
    },
}

_EVENT = {
    "id": EVENT_ID,
    "name": "서울 도심 홍수 대응 훈련 데이터",
    "location": "서울 한강 인접 지역",
    "started_at": "2022-08-08T18:00:00+09:00",
    "ended_at": "2022-08-09T06:00:00+09:00",
    "origin": "SIMULATED",
    "data_status": "데모 데이터 · 공공 데이터 연결 전",
    "flood_extent": {"type": "FeatureCollection", "features": [_FLOOD_POLYGON]},
}


def _load_observed_seoul_flood_extent() -> dict:
    path = Path(__file__).resolve().parents[2] / "data" / "processed" / "seoul_flood_footprints_2022.geojson"
    if not path.exists():
        return {"type": "FeatureCollection", "features": [_FLOOD_POLYGON]}
    return json.loads(path.read_text(encoding="utf-8"))


_EVENT["flood_extent"] = _load_observed_seoul_flood_extent()
_EVENT["origin"] = "OBSERVED"
_EVENT["data_status"] = "OBSERVED · Seoul official 2022 flood footprint connected"


def _event_polygon(lng: float, lat: float) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Event extent pending source connection", "origin": "SIMULATED"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lng - 0.02, lat - 0.01], [lng - 0.02, lat + 0.01], [lng + 0.02, lat + 0.01], [lng + 0.02, lat - 0.01], [lng - 0.02, lat - 0.01]]],
            },
        }],
    }


EVENTS = [
    {**_EVENT, "id": "seoul-2022", "name": "2022 서울 도시침수", "location": "강남 · 신림", "data_year": 2022, "theme": "도시 집중호우", "focus_feature": "반지하·지하공간", "analysis_flow": "강우 → 배수능력 초과 → 저지대 침수 → 건물·인구·지하공간·취약계층", "source": "서울시 침수흔적도 · 서울시 강우량 정보", "data_status": "OBSERVED footprint acquired · rainfall event window processed"},
    {"id": "pohang-2022", "name": "2022 포항 태풍 침수", "location": "냉천", "data_year": 2022, "theme": "태풍 유발 하천홍수", "focus_feature": "산업시설", "analysis_flow": "태풍 → 냉천 범람 → 공동주택·지하주차장·산업시설", "source": "전국 침수흔적도 후보 · 수문자료 연계 예정", "started_at": "2022-09-06T00:00:00+09:00", "ended_at": "2022-09-07T00:00:00+09:00", "origin": "SIMULATED", "data_status": "scenario catalog · source connection pending", "flood_extent": _event_polygon(129.34, 35.99)},
    {"id": "osong-2023", "name": "2023 오송 지하차도 침수", "location": "미호강 · 궁평2지하차도", "data_year": 2023, "theme": "하천·교통시설", "focus_feature": "지하차도·교통시설", "analysis_flow": "미호강·제방 → 범람 → 지하차도 → 차량·통행자", "source": "행정안전부 재난안전데이터공유플랫폼 · 국토교통부 CODIL · OSM", "started_at": "2023-07-15T00:00:00+09:00", "ended_at": "2023-07-16T00:00:00+09:00", "origin": "SIMULATED", "data_status": "PRIMARY · DEM/인구/OSM acquired · flood footprint and water level API pending", "flood_extent": _event_polygon(127.33, 36.63)},
    {"id": "iksan-2024", "name": "2024 익산 극한호우 침수", "location": "함라", "data_year": 2024, "theme": "초단시간 극한호우", "focus_feature": "농경지", "analysis_flow": "극한강우 → 배수·소하천 용량 초과 → 농촌주거·농경지·도로", "source": "전국 침수흔적도 후보 · 강우·농경지 자료 연계 예정", "started_at": "2024-07-10T00:00:00+09:00", "ended_at": "2024-07-11T00:00:00+09:00", "origin": "SIMULATED", "data_status": "scenario catalog · source connection pending", "flood_extent": _event_polygon(126.96, 36.08)},
    {"id": "andong-uiseong-2026", "name": "2026 안동·의성 복합재난", "location": "귀미 · 구계", "data_year": 2026, "theme": "복합재난", "focus_feature": "임시주거·산불피해지역", "analysis_flow": "산불 피해지역 → 집중호우 → 임시주택·도로·상수도 → 재이재민", "source": "재난안전데이터공유플랫폼 API · 실시간 연계 예정", "started_at": "2026-01-01T00:00:00+09:00", "ended_at": "2026-01-02T00:00:00+09:00", "origin": "SIMULATED", "data_status": "scenario catalog · live source connection pending", "flood_extent": _event_polygon(128.72, 36.55)},
]

EVENTS.sort(key=lambda event: event["id"] != EVENT_ID)

ROADS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "강변대로", "origin": "DERIVED"}, "geometry": {"type": "LineString", "coordinates": [[126.94, 37.53], [127.03, 37.53]]}},
        {"type": "Feature", "properties": {"name": "서초 연결도로", "origin": "DERIVED"}, "geometry": {"type": "LineString", "coordinates": [[126.98, 37.49], [126.98, 37.56]]}},
        {"type": "Feature", "properties": {"name": "동부 우회도로", "origin": "DERIVED"}, "geometry": {"type": "LineString", "coordinates": [[127.01, 37.49], [127.01, 37.56]]}},
    ],
}

BUILDINGS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "주거 블록 A", "population": 820, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [126.975, 37.525]}},
        {"type": "Feature", "properties": {"name": "주거 블록 B", "population": 410, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [126.992, 37.522]}},
        {"type": "Feature", "properties": {"name": "업무 시설 C", "population": 260, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [127.025, 37.528]}},
        {"type": "Feature", "properties": {"name": "주거 블록 D", "population": 130, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [127.015, 37.542]}},
    ],
}

INFRASTRUCTURE = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "응급의료센터", "kind": "critical", "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [126.987, 37.529]}},
        {"type": "Feature", "properties": {"name": "변전소", "kind": "critical", "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [127.001, 37.52]}},
    ],
}

SHELTERS = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"name": "한강 체육관", "capacity": 540, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [126.97, 37.545]}},
        {"type": "Feature", "properties": {"name": "서초 학교", "capacity": 680, "origin": "DERIVED"}, "geometry": {"type": "Point", "coordinates": [127.02, 37.505]}},
    ],
}


@lru_cache(maxsize=1)
def _load_osong_layers() -> dict[str, dict]:
    path = Path(__file__).resolve().parents[2] / "data" / "raw" / "osong" / "osm_context_2026-08-30.json"
    if not path.exists():
        return {"roads": ROADS, "buildings": BUILDINGS, "infrastructure": INFRASTRUCTURE, "shelters": SHELTERS}

    raw = json.loads(path.read_text(encoding="utf-8"))
    roads: list[dict] = []
    buildings: list[dict] = []
    infrastructure: list[dict] = []
    shelters: list[dict] = []
    shelter_amenities = {"shelter", "school", "community_centre", "social_centre", "hospital"}

    def coordinates(element: dict) -> list[list[float]]:
        if element.get("geometry"):
            return [[point["lon"], point["lat"]] for point in element["geometry"]]
        if "lon" in element and "lat" in element:
            return [[element["lon"], element["lat"]]]
        center = element.get("center")
        return [[center["lon"], center["lat"]]] if center else []

    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        coords = coordinates(element)
        name = tags.get("name") or tags.get("ref") or "OSM feature"
        if tags.get("highway") and len(coords) >= 2:
            roads.append({"type": "Feature", "properties": {"name": name, "kind": tags["highway"], "origin": "OBSERVED"}, "geometry": {"type": "LineString", "coordinates": coords}})
        if tags.get("building") and len(coords) >= 3:
            point = [sum(coord[0] for coord in coords) / len(coords), sum(coord[1] for coord in coords) / len(coords)]
            buildings.append({"type": "Feature", "properties": {"name": name, "building": tags["building"], "population": 0, "origin": "OBSERVED"}, "geometry": {"type": "Point", "coordinates": point}})
        if tags.get("amenity") and coords:
            point = coords[0] if len(coords) == 1 else [sum(coord[0] for coord in coords) / len(coords), sum(coord[1] for coord in coords) / len(coords)]
            feature = {"type": "Feature", "properties": {"name": name, "kind": tags["amenity"], "origin": "OBSERVED"}, "geometry": {"type": "Point", "coordinates": point}}
            infrastructure.append(feature)
            if tags["amenity"] in shelter_amenities:
                shelters.append(feature)
    return {
        "roads": {"type": "FeatureCollection", "features": roads},
        "buildings": {"type": "FeatureCollection", "features": buildings},
        "infrastructure": {"type": "FeatureCollection", "features": infrastructure},
        "shelters": {"type": "FeatureCollection", "features": shelters},
    }


def get_layers(event_id: str = EVENT_ID) -> dict[str, dict]:
    layers = _load_osong_layers() if event_id == "osong-2023" else {"roads": ROADS, "buildings": BUILDINGS, "infrastructure": INFRASTRUCTURE, "shelters": SHELTERS}
    return deepcopy(layers)

OBSERVATIONS = [
    {"timestamp": "2022-08-08T18:00:00+09:00", "observation_type": "rainfall", "station_id": "rain-001", "value": 42.0, "unit": "mm/h", "quality_flag": "GOOD", "origin": "SIMULATED"},
    {"timestamp": "2022-08-08T21:00:00+09:00", "observation_type": "water_level", "station_id": "river-001", "value": 4.8, "unit": "m", "quality_flag": "GOOD", "origin": "SIMULATED"},
    {"timestamp": "2022-08-09T00:00:00+09:00", "observation_type": "water_level", "station_id": "river-001", "value": 5.6, "unit": "m", "quality_flag": "GOOD", "origin": "SIMULATED"},
]

EVENT_OBSERVATIONS = {
    "osong-2023": [
        {"timestamp": "2023-07-15T05:00:00+09:00", "observation_type": "rainfall", "station_id": "rain-demo-osong", "value": 42.0, "unit": "mm/h", "quality_flag": "SIMULATED", "origin": "SIMULATED"},
        {"timestamp": "2023-07-15T09:00:00+09:00", "observation_type": "water_level", "station_id": "river-demo-miho", "value": 4.8, "unit": "m", "quality_flag": "SIMULATED", "origin": "SIMULATED"},
        {"timestamp": "2023-07-15T12:00:00+09:00", "observation_type": "water_level", "station_id": "river-demo-miho", "value": 5.6, "unit": "m", "quality_flag": "SIMULATED", "origin": "SIMULATED"},
    ],
    "seoul-2022": OBSERVATIONS,
}


def get_events() -> list[dict]:
    return deepcopy(EVENTS)


def get_event(event_id: str = EVENT_ID) -> dict:
    return deepcopy(next(event for event in EVENTS if event["id"] == event_id))
