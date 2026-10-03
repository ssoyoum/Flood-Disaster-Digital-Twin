"""Timeline-only reconstruction cases: Pohang 2022 and Andong-Uiseong 2026.

These cases have no official flood extent or gauge series connected. They replay reported incident times
and answer one kind of counterfactual: "if this response action had happened at time T, how many minutes
before each later milestone would it have been?" Every time comes from a cited report; nothing estimates
casualties, damage, or flood depth.
"""

import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "data" / "processed"
EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}


def _event(time: str, state: str, label: str, description: str, source: str, url: str, confidence: str = "PRESS_REPORT", role: str = "Incident Record") -> dict[str, Any]:
    return {"time": time, "state": state, "label": label, "description": description, "source": source, "source_url": url, "role": role, "confidence": confidence}


def _same_day(date: str) -> Callable[[int, int], datetime]:
    return lambda hour, minute: datetime.fromisoformat(f"{date}T{hour:02d}:{minute:02d}:00")


def _overnight(evening_date: str, morning_date: str) -> Callable[[int, int], datetime]:
    # Overnight cases: clock times from noon belong to the first night, earlier ones to the next morning.
    return lambda hour, minute: datetime.fromisoformat(f"{evening_date if hour >= 12 else morning_date}T{hour:02d}:{minute:02d}:00")


POHANG = {
    "event": {
        "id": "pohang-2022",
        "name": "2022 Pohang Typhoon Flood",
        "location": "Naengcheon lower reach and Indeok-dong, Pohang",
        "data_year": 2022,
        "theme": "Typhoon + River Flood",
        "focus_feature": "Naengcheon overflow and underground parking",
        "analysis_flow": "Typhoon rainfall -> Naengcheon overflow -> underground parking inflow -> full inundation",
        "source": "Press-reported incident times (POSCO, fire service, police statements), OSM attic 2022-09-06",
        "started_at": "2022-09-06T00:00:00+09:00",
        "ended_at": "2022-09-06T23:59:00+09:00",
        "origin": "TEMPORARY",
        "data_status": "Timeline-only case: incident times are press-reported; no official flood extent or gauge series is connected.",
        "flood_extent": EMPTY_FEATURE_COLLECTION,
    },
    "dir": "pohang_2022",
    "prefix": "pohang",
    "clock": _same_day("2022-09-06"),
    "center": [129.401, 35.988],
    "replay": [
        _event("2022-09-06T04:50:00+09:00", "typhoon_landfall", "Typhoon landfall", "Typhoon Hinnamnor makes landfall near Geoje.", "KMA announcement as reported by Newsis", "https://www.newsis.com/view/NISX20220905_0002003677"),
        _event("2022-09-06T05:20:00+09:00", "first_notice", "Second parking notice", "The apartment manager says a second broadcast asked residents to move cars above ground (manager's own account).", "Daum/press, 2022-09-07", "https://v.daum.net/v/20220907101559164", role="Claimed Record"),
        _event("2022-09-06T06:00:00+09:00", "river_overflow", "Naengcheon overflow", "Naengcheon begins to overflow around 06:00.", "POSCO newsroom", "https://newsroom.posco.com/kr/포스코의-저력을-발휘한-냉천범람-피해복구-대장정/"),
        _event("2022-09-06T06:30:00+09:00", "move_car_broadcast", "Move-car broadcast", "Residents are told to move cars out of the underground parking (time per fire-service call records).", "Kyunghyang Shinmun, 2022-09-06", "https://www.khan.co.kr/article/202209062058025/amp"),
        _event("2022-09-06T06:37:00+09:00", "parking_inflow", "Parking inflow starts", "Water enters the underground parking (vehicle dashcam timing).", "YTN, 2022-09-07", "https://www.ytn.co.kr/_ln/0115_202209072037321420"),
        _event("2022-09-06T06:45:00+09:00", "parking_full", "Parking fully flooded", "Underground parking fully flooded eight minutes after inflow; 14 vehicles left in between.", "YTN, 2022-09-07", "https://www.ytn.co.kr/_ln/0115_202209072037321420"),
        _event("2022-09-06T07:00:00+09:00", "plant_outage", "POSCO power and water cut", "Power, communication and water supply stop at the POSCO Pohang works.", "POSCO newsroom", "https://newsroom.posco.com/kr/포스코의-저력을-발휘한-냉천범람-피해복구-대장정/"),
        _event("2022-09-06T07:40:00+09:00", "missing_report", "Missing persons reported", "Missing persons are reported from the underground parking.", "Kyunghyang Shinmun, 2022-09-06", "https://www.khan.co.kr/article/202209062058025/amp"),
    ],
    "interventions": [
        {
            "id": "parking_entry_ban",
            "name": "지하주차장 진입 금지 안내",
            "question": "차량을 옮기라는 안내 대신 지하주차장 진입 금지 안내를 이 시각에 했다면, 침수 시작·완전 침수까지 몇 분이 있었나?",
            "actual_label": "실제 06:30 안내는 차량 이동 요청이었다(보도)",
            "actual_time": "2022-09-06T06:30:00+09:00",
            "milestones": ["parking_inflow", "parking_full"],
            "presets": ["04:50", "05:20", "06:00"],
            "assumptions": [
                "진입 금지 안내가 내려진 시각만 바꾼다. 안내가 지켜졌는지, 몇 명이 영향을 받았는지는 계산하지 않는다.",
                "06:30 방송, 06:37 침수 시작, 06:45 완전 침수는 소방 신고·블랙박스 기준 보도 시각이다.",
                "05:20 재방송은 관리소장 본인 주장이며 독립 확인되지 않았다.",
            ],
        }
    ],
    "reported_facts": [
        {"label": "주차장 유입 물", "value": "약 4.7만 톤", "source": "소방 추정, 인사이트 보도", "url": "https://www.insight.co.kr/news/410928"},
        {"label": "침수 시작~완전 침수", "value": "8분, 그 사이 차량 14대 탈출", "source": "YTN", "url": "https://www.ytn.co.kr/_ln/0115_202209072037321420"},
        {"label": "냉천 하폭", "value": "상류 약 200 m → 냉천교 94 m", "source": "내일신문", "url": "https://m.naeil.com/news/read/435780"},
        {"label": "복구사업 설계빈도", "value": "200년 빈도, 13.43 km, 770억 원", "source": "매일신문", "url": "https://www.imaeil.com/page/view/2022122714573564138"},
        {"label": "차수판 의무", "value": "포항시 신축 건물 지하주차장 2022-10-24부터", "source": "프레시안", "url": "https://www.pressian.com/pages/articles/2022102414401689388"},
    ],
}

ANDONG = {
    "event": {
        "id": "andong-uiseong-2026",
        "name": "2026 Andong-Uiseong Compound Flood",
        "location": "Iljik-myeon (Andong) and Danchon-myeon (Uiseong)",
        "data_year": 2026,
        "theme": "Compound Disaster",
        "focus_feature": "Wildfire temporary housing villages",
        "analysis_flow": "2025 wildfire -> temporary housing -> July 2026 heavy rain -> stream warning -> evacuation order",
        "source": "Press-reported incident times (Nakdong River Flood Control Office, Korea Forest Service statements), OSM attic 2026-07-17",
        "started_at": "2026-07-18T12:00:00+09:00",
        "ended_at": "2026-07-19T12:00:00+09:00",
        "origin": "TEMPORARY",
        "data_status": "Timeline-only case: incident times are press-reported; no official flood extent or gauge series is connected.",
        "flood_extent": EMPTY_FEATURE_COLLECTION,
    },
    "dir": "andong_uiseong_2026",
    "prefix": "andong",
    "clock": _overnight("2026-07-18", "2026-07-19"),
    "center": [128.705, 36.482],
    "replay": [
        _event("2026-07-18T22:59:00+09:00", "first_isolation", "First isolation", "Three people are isolated by flooding around a church in Sinseok-ri, Andong.", "Newsis, 2026-07-19", "https://mobile.newsis.com/view/NISX20260719_0003713973"),
        _event("2026-07-18T23:40:00+09:00", "flood_warning", "Micheon flood warning", "Nakdong River Flood Control Office issues a flood warning at Unsan-ri (Micheon); stage 3.5 m, warning level 4.7 m.", "Segye Ilbo, 2026-07-19", "https://www.segye.com/newsView/20260719500038"),
        _event("2026-07-18T23:44:00+09:00", "camper_isolation", "Camper isolated", "A camping car is isolated at the Gwangeum-ri resort area.", "Newsis, 2026-07-19", "https://mobile.newsis.com/view/NISX20260719_0003713973"),
        _event("2026-07-19T00:00:00+09:00", "evacuation_order", "Evacuation order", "Evacuation order issued (one outlet reports it as a midnight alert on the 18th).", "Seoul Shinmun, 2026-07-19", "https://m.seoul.co.kr/news/2026/07/19/20260719500010"),
        _event("2026-07-19T00:30:00+09:00", "predicted_warning_level", "Warning level expected", "Time at which the flood control office expected Micheon to reach the warning level (forecast, not an observation).", "Segye Ilbo, 2026-07-19", "https://www.segye.com/newsView/20260719500038", confidence="FORECAST_REPORTED", role="Forecast"),
        _event("2026-07-19T05:40:00+09:00", "warning_lifted", "Flood warning lifted", "Micheon flood warning lifted.", "Newsis, 2026-07-19", "https://www.newsis.com/view/NISX20260719_0003714097"),
        _event("2026-07-19T08:00:00+09:00", "national_landslide_alert", "Landslide alert raised", "Korea Forest Service raises the Gyeongbuk landslide crisis alert from caution to alert.", "Segye Ilbo, 2026-07-19", "https://www.segye.com/newsView/20260719513934"),
    ],
    "interventions": [
        {
            "id": "evacuation_order",
            "name": "대피명령 시각",
            "question": "대피명령을 이 시각에 냈다면, 경보 수위 도달 예측 시각(00:30)까지 몇 분이 있었나?",
            "actual_label": "실제 대피명령은 00:00(보도)",
            "actual_time": "2026-07-19T00:00:00+09:00",
            "milestones": ["predicted_warning_level"],
            "presets": ["22:59", "23:40"],
            "assumptions": [
                "대피명령 시각만 바꾼다. 대피 완료 인원이나 피해 감소는 계산하지 않는다.",
                "00:30은 관측이 아니라 홍수통제소가 발령 당시 내놓은 경보 수위 도달 예측 시각이다.",
                "대피명령 시각은 매체에 따라 7/18 자정 또는 7/19 00:00으로 표기된다. 같은 시각으로 본다.",
                "임시주택 단지별 침수 시각은 확인하지 못해 기준점으로 쓰지 않는다.",
            ],
        },
        {
            "id": "landslide_alert",
            "name": "산사태 위기경보 상향 시각",
            "question": "산림청 산사태 위기경보 '경계' 상향을 이 시각에 했다면, 실제(08:00)보다 몇 분 빨랐나?",
            "actual_label": "실제 상향은 7/19 08:00(보도)",
            "actual_time": "2026-07-19T08:00:00+09:00",
            "milestones": [],
            "presets": ["00:00", "23:40"],
            "assumptions": [
                "00:00경 임하면에 시간당 50 mm 이상 비와 지역 산사태 경보가 보도됐다. 임하면은 분석 범위 동쪽 밖이다.",
                "시각 차이만 계산하며, 산사태 발생이나 피해와의 관계는 추정하지 않는다.",
            ],
        },
    ],
    "reported_facts": [
        {"label": "침수 임시주택", "value": "3개 단지 20동 (귀미1리 11동, 구계리 9~12동 보도)", "source": "세계일보·서울신문·경향신문", "url": "https://www.segye.com/newsView/20260719513934"},
        {"label": "대피", "value": "6개 시군 377가구 564명, 구계리 155명", "source": "세계일보·서울신문", "url": "https://m.seoul.co.kr/news/2026/07/19/20260719500010"},
        {"label": "누적 강우", "value": "안동 남선 230.5 mm, 의성 비안 232.5 mm (7/17~)", "source": "세계일보(중대본 7/19 17시 기준)", "url": "https://www.segye.com/newsView/20260719513934"},
        {"label": "사후 점검", "value": "임시주택 2,084동 점검, 앵커볼트 811개 설치", "source": "경향신문", "url": "https://www.khan.co.kr/article/202607211147001/"},
        {"label": "산사태 취약지역 인근", "value": "65곳 인근 임시주택 141동", "source": "경향신문", "url": "https://www.khan.co.kr/article/202607211147001/"},
    ],
}

CASES: dict[str, dict[str, Any]] = {POHANG["event"]["id"]: POHANG, ANDONG["event"]["id"]: ANDONG}

LIMITATIONS = [
    "Incident times are press-reported and need official source pages.",
    "No official flood extent, gauge series, or building register is connected; the map shows an event-date OSM snapshot only.",
    "Lead times are arithmetic between a response time and reported milestones. They do not estimate evacuation, casualties, or damage avoided.",
    "Focus sites are village or bridge centre points, not the exact location of affected homes.",
]


def is_timeline_case(event_id: str) -> bool:
    return event_id in CASES


def _read(case: dict[str, Any], suffix: str) -> dict[str, Any] | None:
    path = PROCESSED / case["dir"] / f"{case['prefix']}_{suffix}"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _layer(case: dict[str, Any], key: str, label: str, suffix: str | None, status: str, source: str) -> dict[str, Any]:
    data = _read(case, suffix) if suffix else None
    if data is None:
        return {"key": key, "label": label, "status": "UNAVAILABLE", "source_type": "NOT_CONNECTED", "source": source, "snapshot": None, "path": None, "feature_count": 0, "geometry_types": [], "data": EMPTY_FEATURE_COLLECTION}
    return {
        "key": key,
        "label": label,
        "status": status,
        "source_type": "OSM_ATTIC" if status == "VERIFIED" else "DERIVED",
        "source": source,
        "snapshot": case["event"]["started_at"][:10],
        "path": f"data/processed/{case['dir']}/{case['prefix']}_{suffix}",
        "feature_count": len(data.get("features", [])),
        "geometry_types": sorted({feature.get("geometry", {}).get("type", "Unknown") for feature in data.get("features", [])}),
        "data": data,
    }


@lru_cache(maxsize=4)
def get_timeline_layers(event_id: str) -> dict[str, Any]:
    case = CASES[event_id]
    osm = "OpenStreetMap Overpass attic"
    return {
        "aoi": _layer(case, "aoi", "분석 범위", "aoi.geojson", "DERIVED", "FloodOps bbox"),
        "roads": _layer(case, "roads", "도로", "osm_roads.geojson", "VERIFIED", osm),
        "buildings": _layer(case, "buildings", "건축물(OSM, 부분)", "osm_buildings.geojson", "VERIFIED", osm),
        "waterways": _layer(case, "waterways", "하천", "osm_waterways.geojson", "VERIFIED", osm),
        "terrain": _layer(case, "terrain", "지형", None, "UNAVAILABLE", "Not connected"),
        "approx_flood_envelope": _layer(case, "approx_flood_envelope", "근사 범람", None, "UNAVAILABLE", "Not connected"),
        "hand_reconstruction": _layer(case, "hand_reconstruction", "HAND 재구성", None, "UNAVAILABLE", "Not connected"),
        "facilities": _layer(case, "facilities", "초점 지점", "focus_sites.geojson", "DERIVED", "Reported place names, OSM place nodes"),
        "underpass": _layer(case, "underpass", "지하차도", None, "UNAVAILABLE", "Not applicable"),
        "flood_extent": _layer(case, "flood_extent", "공식 침수범위", None, "UNAVAILABLE", "Official flood extent not connected"),
    }


def get_timeline_event(event_id: str) -> dict[str, Any]:
    return dict(CASES[event_id]["event"])


def get_timeline_status(event_id: str) -> dict[str, Any]:
    layers = get_timeline_layers(event_id)
    return {
        "flood_extent": {k: v for k, v in layers["flood_extent"].items()},
        "population": {"status": "UNAVAILABLE"},
        "rainfall": {"status": "UNAVAILABLE", "notes": "KMA AWS series not downloaded yet; reported totals are listed as press facts."},
        "dem": {"status": "UNAVAILABLE"},
        "layers": {key: {k: v for k, v in value.items() if k != "data"} for key, value in layers.items()},
    }


def get_timeline_summary(event_id: str) -> dict[str, Any]:
    layers = get_timeline_layers(event_id)
    return {
        "event_id": event_id,
        "origin": "TEMPORARY",
        "model_type": "Timeline reconstruction with response-timing counterfactuals",
        "official_population": None,
        "building_count": layers["buildings"]["feature_count"],
        "road_count": layers["roads"]["feature_count"],
        "waterway_count": layers["waterways"]["feature_count"],
        "terrain_low_elevation_cells": 0,
        "terrain_low_elevation_threshold_m": None,
        "rainfall_peak_mm_per_hour": None,
        "rainfall_records": None,
        "facility_count": layers["facilities"]["feature_count"],
        "underpass_available": False,
        "flooded_area_km2": "UNAVAILABLE",
        "exposed_population": "UNAVAILABLE",
        "exposed_buildings": "UNAVAILABLE",
        "affected_road_length_km": "UNAVAILABLE",
        "critical_infrastructure": "UNAVAILABLE",
        "affected_shelters": "UNAVAILABLE",
        "data_status": "No exposure counts: official flood extent and building register are not connected for this case.",
    }


def get_timeline_reconstruction(event_id: str) -> dict[str, Any]:
    case = CASES[event_id]
    return {
        "event_id": event_id,
        "title": f"{case['event']['name']} timeline reconstruction",
        "model_type": "Timeline reconstruction with response-timing counterfactuals",
        "event_year": case["event"]["data_year"],
        "status": "READY_FOR_RULE_BASED_REPLAY",
        "case_kind": "timeline",
        "map_center": case["center"],
        "replay": case["replay"],
        "interventions": [
            {key: intervention[key] for key in ("id", "name", "question", "actual_label", "actual_time", "milestones", "presets")}
            | {"endpoint": f"/api/events/{event_id}/analysis/response-timing"}
            for intervention in case["interventions"]
        ],
        "reported_facts": case["reported_facts"],
        "provenance": [
            {"source": "언론 보도 사건 시각", "data_vintage": case["event"]["started_at"][:10], "role": "Incident times", "status": "TEMPORARY"},
            {"source": "OpenStreetMap attic", "data_vintage": case["event"]["started_at"][:10], "role": "Roads, waterways, partial buildings", "status": "VERIFIED"},
        ],
        "limitations": LIMITATIONS,
    }


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:00+09:00")


def _naive(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=None)


def _parse(case: dict[str, Any], value: str) -> datetime:
    text = value.strip()
    if len(text) == 5 and text[2] == ":" and text[:2].isdigit() and text[3:].isdigit():
        hour, minute = int(text[:2]), int(text[3:])
        if hour > 23 or minute > 59:
            raise ValueError(f"Invalid time: {value}")
        return case["clock"](hour, minute)
    try:
        return _naive(text)
    except ValueError as exc:
        raise ValueError(f"Invalid time: {value}. Use HH:MM or ISO-8601.") from exc


def analyze_response_timing(event_id: str, intervention_id: str, action_times: list[str]) -> dict[str, Any]:
    case = CASES[event_id]
    intervention = next((item for item in case["interventions"] if item["id"] == intervention_id), None)
    if intervention is None:
        raise ValueError(f"Unknown intervention for {event_id}: {intervention_id}. Available: {', '.join(item['id'] for item in case['interventions'])}")
    by_state = {item["state"]: item for item in case["replay"]}
    milestones = [{"state": state, "label": by_state[state]["label"], "time": by_state[state]["time"]} for state in intervention["milestones"]]
    actual = _naive(intervention["actual_time"])
    window_start = _naive(case["replay"][0]["time"]) - timedelta(hours=12)
    window_end = _naive(case["replay"][-1]["time"]) + timedelta(hours=12)
    rows = []
    for value in [*(action_times or []), intervention["actual_time"][11:16]]:
        moment = _parse(case, value)
        if not window_start <= moment <= window_end:
            raise ValueError(f"{value} is outside the event window")
        rows.append(
            {
                "action_time": _iso(moment),
                "is_actual": moment == actual,
                "minutes_earlier_than_actual": int((actual - moment).total_seconds() // 60),
                "minutes_before_milestones": {item["state"]: int((_naive(item["time"]) - moment).total_seconds() // 60) for item in milestones},
            }
        )
    unique = {row["action_time"]: row for row in rows}
    return {
        "event_id": event_id,
        "analysis": "response_timing_whatif",
        "origin": "TEMPORARY",
        "intervention_id": intervention_id,
        "intervention_name": intervention["name"],
        "actual_time": intervention["actual_time"],
        "actual_label": intervention["actual_label"],
        "milestones": milestones,
        "scenarios": sorted(unique.values(), key=lambda row: row["action_time"]),
        "assumptions": intervention["assumptions"],
    }
