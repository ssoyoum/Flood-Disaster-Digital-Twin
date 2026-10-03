"""Seoul 2022 Dorimcheon reconstruction: official flood traces, rain gauges, and counterfactual arithmetic.

Everything here is either an observed record (gauges, official flood traces, reported incident times)
or explicit arithmetic on those records. Nothing estimates casualties, damage, or flood depth reduction.
"""

import csv
import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SEOUL_DIR = REPO_ROOT / "data" / "processed" / "seoul_2022"
SEOUL_EVENT_ID = "seoul-2022"
EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}

PRIMARY_GAUGE = "신림P"
EVENT_DAY = "2022-08-08"
FIRST_RESCUE_CALL = "2022-08-08T20:59:00+09:00"
FIRST_PUBLIC_ALERT = "2022-08-08T21:19:00+09:00"
DESIGN_RAINFALL_MM_PER_HOUR = 95.0
DORIMCHEON_TUNNEL_STORAGE_M3 = 400_000

# Times reported in press coverage are marked as such; gauge-derived times come from the processed CSV.
SEOUL_RECONSTRUCTION_EVENTS = [
    {
        "time": "2022-08-08T12:50:00+09:00",
        "label": "Heavy rain warning",
        "state": "rain_warning",
        "description": "Heavy rain advisory upgraded to a warning for southwest Seoul (Gwanak, Dongjak, Yeongdeungpo, Guro and others).",
        "source": "KMA announcement as reported by Edaily, 2022-08-08",
        "source_url": "https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=02633846632425352",
        "role": "Incident Record",
        "confidence": "PRESS_REPORT",
    },
    {
        "time": "2022-08-08T13:09:00+09:00",
        "label": "Rainfall 50 mm/h reached",
        "state": "heavy_rain",
        "description": "Sillim pump station gauge 60-minute rainfall first reaches 50 mm (afternoon burst).",
        "source": "Seoul 10-minute rain gauge 신림P (2302), rolling 60-minute sum",
        "role": "Hydromet Threshold",
        "confidence": "OBSERVED",
    },
    {
        "time": "2022-08-08T20:49:00+09:00",
        "label": "Design rainfall exceeded",
        "state": "design_exceeded",
        "description": "Sillim gauge 60-minute rainfall exceeds the pre-2022 Seoul drainage design target of 95 mm/h.",
        "source": "Seoul 10-minute rain gauge 신림P (2302); design target 95 mm/h (30-year) per Seoul announcement reported by Newsis 2022-08-10",
        "source_url": "https://mobile.newsis.com/view/NISX20220810_0001974708",
        "role": "Hydromet Threshold",
        "confidence": "OBSERVED",
    },
    {
        "time": FIRST_RESCUE_CALL,
        "label": "First rescue call in Sillim",
        "state": "rescue_call",
        "description": (
            "First of eight 112 calls about a flooded semi-basement home in Sillim-dong; the Sillim gauge 60-minute peak (121.5 mm) ends at the same minute. "
            "The official CDSCH situation report (8.9 06:00) records the Gwanak semi-basement case at about 21:07 without saying whether that is the call or the death time."
        ),
        "source": "Hankook Ilbo, 2022-08-09 (district-level only); official report lists 21:07경",
        "official_url": "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000336&nttId=93917",
        "source_url": "https://hankookilbo.com/News/Read/A2022080914150005222",
        "role": "Incident Record",
        "confidence": "PRESS_REPORT",
    },
    {
        "time": FIRST_PUBLIC_ALERT,
        "label": "First low-lying flood alert",
        "state": "public_alert",
        "description": "Seoul Metropolitan Government sends its first emergency text about low-lying area flooding; Gwanak-gu follows at 21:21.",
        "source": "Hankook Ilbo, 2022-08-09",
        "source_url": "https://hankookilbo.com/News/Read/A2022080914150005222",
        "role": "Incident Record",
        "confidence": "PRESS_REPORT",
    },
    {
        "time": "2022-08-08T21:30:00+09:00",
        "label": "National response raised",
        "state": "national_escalation",
        "description": "Central Disaster and Safety Countermeasures Headquarters raised to level 2, crisis alert from caution to alert. The official release says '9시 30분' without a.m./p.m.; level 1 began at 07:30 the same morning.",
        "source": "Ministry of the Interior and Safety press release, 2022-08-08 (a.m./p.m. not stated); Kyunghyang Shinmun",
        "source_url": "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=93918",
        "role": "Incident Record",
        "confidence": "OFFICIAL_AMBIGUOUS",
    },
    {
        "time": "2022-08-08T21:45:00+09:00",
        "label": "Fire service arrives",
        "state": "responders_arrive",
        "description": "Fire service reaches the Sillim-dong rescue site about 46 minutes after the first call.",
        "source": "Hankook Ilbo, 2022-08-09",
        "source_url": "https://hankookilbo.com/News/Read/A2022080914150005222",
        "role": "Incident Record",
        "confidence": "PRESS_REPORT",
    },
]

LIMITATIONS = [
    "Official flood traces record where flooding happened after the event; they carry no timestamps, so the map cannot animate flood growth.",
    "Rainfall thresholds use one gauge (신림P) as the trigger; other gauges in the corridor peaked at different minutes.",
    "Lead times are arithmetic between an alert time and recorded incident times. They do not estimate evacuation, casualties, or damage avoided.",
    "Storage capture is rain volume arithmetic over an assumed catchment area and runoff coefficient. It is not a sewer or tunnel hydraulic model.",
    "Building stock comes from a 2026-08-09 register snapshot filtered to use-approval dates on or before 2022-08-08; buildings demolished before 2026 are missing.",
    "Incident times other than gauge thresholds come from press coverage and need official source pages.",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _summary() -> dict[str, Any]:
    path = SEOUL_DIR / "seoul_dorimcheon_summary.json"
    return _read_json(path) if path.exists() else {}


@lru_cache(maxsize=1)
def _rainfall_rows() -> list[dict[str, Any]]:
    path = SEOUL_DIR / "seoul_rainfall_dorimcheon_2022-08-08.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        rows = []
        for row in csv.DictReader(stream):
            rows.append(
                {
                    "station_name": row["station_name"],
                    "station_code": row["station_code"],
                    "observed_at": datetime.fromisoformat(row["observed_at"]),
                    "rainfall_10min_mm": float(row["rainfall_10min_mm"]),
                    "rainfall_60min_mm": float(row["rainfall_60min_mm"]) if row["rainfall_60min_mm"] else None,
                }
            )
        return rows


def gauge_names() -> list[str]:
    return sorted({row["station_name"] for row in _rainfall_rows()})


def _gauge_series(station: str) -> list[dict[str, Any]]:
    rows = [row for row in _rainfall_rows() if row["station_name"] == station]
    if not rows:
        raise ValueError(f"Unknown rain gauge: {station}. Available: {', '.join(gauge_names())}")
    return sorted(rows, key=lambda row: row["observed_at"])


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:00+09:00")


def _minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _parse_clock(value: str) -> datetime:
    text = value.strip()
    if len(text) == 5 and text[2] == ":":
        hour, minute = int(text[:2]), int(text[3:])
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError(f"Invalid time: {value}")
        return datetime.fromisoformat(f"{EVENT_DAY}T{text}:00")
    return datetime.fromisoformat(text).replace(tzinfo=None)


def _event_time(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=None)


def _layer(key: str, label: str, filename: str | None, *, status: str, source_type: str, source: str, snapshot: str | None) -> dict[str, Any]:
    path = SEOUL_DIR / filename if filename else None
    if path is None or not path.exists():
        return {
            "key": key, "label": label, "status": "UNAVAILABLE", "source_type": source_type, "source": source,
            "snapshot": snapshot, "path": None, "feature_count": 0, "geometry_types": [], "data": EMPTY_FEATURE_COLLECTION,
        }
    data = _read_json(path)
    return {
        "key": key,
        "label": label,
        "status": status,
        "source_type": source_type,
        "source": source,
        "snapshot": snapshot,
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "feature_count": len(data.get("features", [])),
        "geometry_types": sorted({feature.get("geometry", {}).get("type", "Unknown") for feature in data.get("features", [])}),
        "data": data,
    }


@lru_cache(maxsize=1)
def get_seoul_layers() -> dict[str, Any]:
    unavailable = lambda key, label: _layer(key, label, None, status="UNAVAILABLE", source_type="NOT_APPLICABLE", source="Not used for the Seoul urban case", snapshot=None)  # noqa: E731
    return {
        "aoi": _layer("aoi", "도림천 유역 분석 범위", "seoul_dorimcheon_aoi.geojson", status="DERIVED", source_type="ANALYSIS_EXTENT", source="FloodOps bbox", snapshot=None),
        "roads": _layer("roads", "도로", "seoul_osm_roads_2022.geojson", status="VERIFIED", source_type="OSM_ATTIC", source="OpenStreetMap Overpass attic", snapshot="2022-08-08"),
        "buildings": _layer(
            "buildings", "침수흔적과 겹친 건축물", "seoul_buildings_trace_overlay_2022.geojson", status="DERIVED", source_type="OFFICIAL_OVERLAY",
            source="국토교통부 GIS건물통합정보 x 서울시 침수흔적도", snapshot="2026-08-09 (사용승인 2022-08-08 이전)",
        ),
        "waterways": _layer("waterways", "하천", "seoul_osm_waterways_2022.geojson", status="VERIFIED", source_type="OSM_ATTIC", source="OpenStreetMap Overpass attic", snapshot="2022-08-08"),
        "terrain": unavailable("terrain", "지형"),
        "approx_flood_envelope": unavailable("approx_flood_envelope", "근사 범람"),
        "hand_reconstruction": unavailable("hand_reconstruction", "HAND 재구성"),
        "facilities": _layer("facilities", "시설", "seoul_osm_facilities_2022.geojson", status="VERIFIED", source_type="OSM_ATTIC", source="OpenStreetMap Overpass attic", snapshot="2022-08-08"),
        "underpass": unavailable("underpass", "지하차도"),
        "flood_extent": _layer(
            "flood_extent", "서울시 침수흔적도 2022", "seoul_flood_traces_2022_dorimcheon.geojson", status="VERIFIED", source_type="OFFICIAL_FLOOD_TRACE",
            source="서울시 침수흔적도 (공공데이터포털 15133406)", snapshot="2022-08-08~17 호우",
        ),
    }


def get_seoul_event() -> dict[str, Any]:
    return {
        "id": SEOUL_EVENT_ID,
        "name": "2022 Seoul Urban Flood",
        "location": "Dorimcheon corridor (Sillim, Sindaebang, Daerim), Seoul",
        "data_year": 2022,
        "theme": "Urban Flood",
        "focus_feature": "Dorimcheon corridor low-lying neighbourhoods",
        "analysis_flow": "Rainfall -> drainage design exceeded -> low-lying flooding -> rescue calls -> public alert",
        "source": "Seoul rain gauges, Seoul official flood traces 2022, GIS building register, OSM attic 2022-08-08, press-reported incident times",
        "started_at": "2022-08-08T00:00:00+09:00",
        "ended_at": "2022-08-09T23:59:00+09:00",
        "origin": "VERIFIED",
        "data_status": "Official flood traces and gauge records connected; incident times beyond gauge thresholds are press-reported.",
        # The traces are served through /layers; repeating 7 MB here would slow the catalog.
        "flood_extent": EMPTY_FEATURE_COLLECTION,
    }


def get_seoul_status() -> dict[str, Any]:
    layers = get_seoul_layers()
    summary = _summary()
    return {
        "flood_extent": {key: value for key, value in layers["flood_extent"].items() if key != "data"} | {"data": EMPTY_FEATURE_COLLECTION},
        "population": {"status": "UNAVAILABLE", "notes": "Population is not connected for the Seoul case."},
        "rainfall": {
            "status": "VERIFIED",
            "source": "서울시 강우량 10분 자료",
            "source_type": "OBSERVED",
            "period": "2022-08-08 ~ 2022-08-09",
            "unit": "mm/10min",
            "records": len(_rainfall_rows()),
            "notes": "동작구청 gauge stops after 2022-08-08 23:12; its 08-09 rows are missing.",
        },
        "dem": {"status": "UNAVAILABLE", "notes": "Terrain is not used; the official flood traces replace a terrain-based envelope."},
        "layers": {key: {k: v for k, v in value.items() if k != "data"} for key, value in layers.items()},
        "summary_created_at": summary.get("created_at"),
    }


def get_seoul_summary() -> dict[str, Any]:
    summary = _summary()
    traces = summary.get("traces", {})
    buildings = summary.get("buildings", {})
    roads = summary.get("roads", {})
    peak = summary.get("rainfall_peaks", {}).get(PRIMARY_GAUGE, {})
    layers = get_seoul_layers()
    return {
        "event_id": SEOUL_EVENT_ID,
        "origin": "VERIFIED",
        "model_type": "Urban flood reconstruction with official flood traces",
        "official_population": None,
        "building_count": buildings.get("stock_at_event", 0),
        "road_count": layers["roads"]["feature_count"],
        "waterway_count": layers["waterways"]["feature_count"],
        "terrain_low_elevation_cells": 0,
        "terrain_low_elevation_threshold_m": None,
        "rainfall_peak_mm_per_hour": peak.get("max_60min_mm"),
        "rainfall_peak_timestamp": peak.get("max_60min_end"),
        "rainfall_peak_station_name": PRIMARY_GAUGE,
        "rainfall_records": len(_rainfall_rows()),
        "facility_count": layers["facilities"]["feature_count"],
        "underpass_available": False,
        "flooded_area_km2": traces.get("union_area_in_aoi_km2", "UNAVAILABLE"),
        "exposed_population": "UNAVAILABLE",
        "exposed_buildings": buildings.get("trace_intersecting", "UNAVAILABLE"),
        "affected_road_length_km": roads.get("osm_road_km_in_traces", "UNAVAILABLE"),
        "critical_infrastructure": "UNAVAILABLE",
        "affected_shelters": "UNAVAILABLE",
        "data_status": "Counts overlay the official 2022 flood traces; they are recorded flooding, not modelled.",
    }


def get_seoul_observations() -> list[dict[str, Any]]:
    return [
        {
            "timestamp": _iso(row["observed_at"]),
            "observation_type": "rainfall",
            "station_id": row["station_code"],
            "value": row["rainfall_10min_mm"],
            "unit": "mm/10min",
            "quality_flag": "OK",
            "origin": "VERIFIED",
        }
        for row in _gauge_series(PRIMARY_GAUGE)
    ] if _rainfall_rows() else []


def get_seoul_reconstruction() -> dict[str, Any]:
    summary = _summary()
    series = _gauge_series(PRIMARY_GAUGE) if _rainfall_rows() else []
    window = [row for row in series if datetime.fromisoformat(f"{EVENT_DAY}T06:00:00") <= row["observed_at"] <= datetime.fromisoformat(f"{EVENT_DAY}T23:59:00")]
    return {
        "event_id": SEOUL_EVENT_ID,
        "title": "2022 Seoul Dorimcheon flood reconstruction",
        "model_type": "Urban flood reconstruction + counterfactual alert and storage arithmetic",
        "event_year": 2022,
        "status": "READY_FOR_RULE_BASED_REPLAY",
        "replay": SEOUL_RECONSTRUCTION_EVENTS,
        "primary_gauge": PRIMARY_GAUGE,
        "gauges": gauge_names(),
        "rainfall_series": [
            {"time": _iso(row["observed_at"]), "rainfall_10min_mm": row["rainfall_10min_mm"], "rainfall_60min_mm": row["rainfall_60min_mm"]}
            for row in window
        ],
        "rainfall_peaks": summary.get("rainfall_peaks", {}),
        "design_rainfall_mm_per_hour": DESIGN_RAINFALL_MM_PER_HOUR,
        "exposure": {
            "aoi_area_km2": summary.get("aoi_area_km2"),
            "traces": summary.get("traces", {}),
            "buildings": summary.get("buildings", {}),
            "roads": summary.get("roads", {}),
        },
        "interventions": [
            {
                "id": "alert_timing",
                "name": "강우 임계 기반 저지대 경보",
                "question": "신림 강우계가 임계를 넘은 순간 저지대 경보를 보냈다면, 첫 구조 신고까지 몇 분이 있었나?",
                "endpoint": f"/api/events/{SEOUL_EVENT_ID}/analysis/alert-timing",
            },
            {
                "id": "storage_capture",
                "name": "도림천 대심도 빗물터널",
                "question": "계획 저류량(40만 m3) 터널이 있었다면, 설계강우를 넘은 빗물 중 얼마를 담고 언제 가득 찼나?",
                "endpoint": f"/api/events/{SEOUL_EVENT_ID}/analysis/storage-capture",
            },
        ],
        "provenance": [
            {"source": "서울시 강우량 10분 자료", "data_vintage": "2022-08", "role": "Observed rainfall", "status": "VERIFIED"},
            {"source": "서울시 침수흔적도 2022", "data_vintage": "2022 호우", "role": "Observed flood extent", "status": "VERIFIED"},
            {"source": "국토교통부 GIS건물통합정보", "data_vintage": "2026-08-09 (사용승인 2022-08-08 이전 필터)", "role": "Building stock", "status": "DERIVED"},
            {"source": "OpenStreetMap attic", "data_vintage": "2022-08-08", "role": "Roads, waterways, facilities", "status": "VERIFIED"},
            {"source": "언론 보도(한국일보·경향신문·이데일리·뉴시스)", "data_vintage": "2022-08", "role": "Incident times", "status": "TEMPORARY"},
        ],
        "limitations": LIMITATIONS,
    }


def _threshold_crossing(series: list[dict[str, Any]], threshold: float) -> datetime | None:
    for row in series:
        if row["rainfall_60min_mm"] is not None and row["rainfall_60min_mm"] >= threshold:
            return row["observed_at"]
    return None


def analyze_alert_timing(station: str = PRIMARY_GAUGE, thresholds_mm_per_hour: list[float] | None = None, alert_times: list[str] | None = None) -> dict[str, Any]:
    series = _gauge_series(station)
    rescue = _event_time(FIRST_RESCUE_CALL)
    actual_alert = _event_time(FIRST_PUBLIC_ALERT)
    scenarios = []
    for threshold in thresholds_mm_per_hour or []:
        crossing = _threshold_crossing(series, threshold)
        scenarios.append(_alert_row(f"{station} 60분 강우 {threshold:g} mm 도달", "rainfall_threshold", crossing, rescue, actual_alert, threshold))
    for value in alert_times or []:
        scenarios.append(_alert_row(f"{value} 수동 경보", "manual_time", _parse_clock(value), rescue, actual_alert, None))
    return {
        "event_id": SEOUL_EVENT_ID,
        "analysis": "alert_timing_whatif",
        "origin": "TEMPORARY",
        "station": station,
        "first_rescue_call": FIRST_RESCUE_CALL,
        "actual_first_alert": FIRST_PUBLIC_ALERT,
        "actual_alert_after_rescue_call_min": _minutes(rescue, actual_alert),
        "scenarios": scenarios,
        "assumptions": [
            "경보 시각은 선택한 강우계의 60분 누적 강우가 임계에 처음 닿은 10분 관측 시각이다.",
            "첫 구조 신고 20:59와 첫 저지대 침수 문자 21:19는 언론 보도 시각이다.",
            "선행 시간은 시각 차이일 뿐이며 대피 성공·인명 피해 감소를 뜻하지 않는다.",
            "낮은 임계는 일찍 울리지만 그 뒤 강우가 잦아든 구간이 길어, 경보 피로를 고려해야 한다.",
        ],
    }


def _alert_row(label: str, kind: str, alert: datetime | None, rescue: datetime, actual_alert: datetime, threshold: float | None) -> dict[str, Any]:
    if alert is None:
        return {
            "label": label, "kind": kind, "threshold_mm_per_hour": threshold, "alert_time": None, "reached": False,
            "minutes_before_first_rescue_call": None, "minutes_earlier_than_actual_alert": None,
        }
    return {
        "label": label,
        "kind": kind,
        "threshold_mm_per_hour": threshold,
        "alert_time": _iso(alert),
        "reached": True,
        "minutes_before_first_rescue_call": _minutes(alert, rescue),
        "minutes_earlier_than_actual_alert": _minutes(alert, actual_alert),
    }


def analyze_storage_capture(
    station: str = PRIMARY_GAUGE,
    storage_m3: float = DORIMCHEON_TUNNEL_STORAGE_M3,
    capacity_mm_per_hour: float = DESIGN_RAINFALL_MM_PER_HOUR,
    catchment_area_km2: float | None = None,
    runoff_coefficient: float = 1.0,
) -> dict[str, Any]:
    series = _gauge_series(station)
    area_km2 = catchment_area_km2 if catchment_area_km2 is not None else float(_summary().get("aoi_area_km2") or 0)
    if area_km2 <= 0:
        raise ValueError("catchment_area_km2 must be positive")
    capacity_per_step = capacity_mm_per_hour / 6
    cumulative_m3 = 0.0
    first_excess = None
    full_at = None
    timeline = []
    for row in series:
        excess_mm = max(0.0, row["rainfall_10min_mm"] - capacity_per_step)
        if excess_mm > 0 and first_excess is None:
            first_excess = row["observed_at"]
        cumulative_m3 += excess_mm / 1000 * area_km2 * 1_000_000 * runoff_coefficient
        if full_at is None and cumulative_m3 >= storage_m3:
            full_at = row["observed_at"]
        if excess_mm > 0:
            timeline.append({"time": _iso(row["observed_at"]), "excess_mm": round(excess_mm, 2), "cumulative_excess_m3": round(cumulative_m3)})
    captured = min(storage_m3, cumulative_m3)
    rescue = _event_time(FIRST_RESCUE_CALL)
    return {
        "event_id": SEOUL_EVENT_ID,
        "analysis": "storage_capture_whatif",
        "origin": "TEMPORARY",
        "station": station,
        "storage_m3": storage_m3,
        "capacity_mm_per_hour": capacity_mm_per_hour,
        "catchment_area_km2": round(area_km2, 3),
        "runoff_coefficient": runoff_coefficient,
        "excess_volume_m3": round(cumulative_m3),
        "captured_volume_m3": round(captured),
        "captured_share_pct": round(captured / cumulative_m3 * 100, 1) if cumulative_m3 else None,
        "first_excess_time": _iso(first_excess) if first_excess else None,
        "storage_full_time": _iso(full_at) if full_at else None,
        "storage_full_minutes_before_first_rescue_call": _minutes(full_at, rescue) if full_at else None,
        "excess_timeline": timeline,
        "assumptions": [
            "초과량은 10분 강우가 처리 능력(시간당 값의 1/6)을 넘은 몫만 더한 값이다.",
            "면적 기본값은 분석 범위 bbox 면적이며 도림천 실제 유역면적이 아니다.",
            "유출계수 1.0은 내린 비가 모두 유출된다는 상한 가정이다.",
            "터널 저류량 40만 m3는 2025-11-20 서울시 도시계획위원회 통과안 보도값(한국일보)이다. 신월 저류시설은 32만 m3다.",
            "저류 몫은 부피 산술이며 침수 면적·침수심 감소를 계산하지 않는다.",
        ],
    }
