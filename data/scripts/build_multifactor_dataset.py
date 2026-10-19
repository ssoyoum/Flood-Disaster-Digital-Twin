"""Build a provenance-preserving multi-factor dataset for FloodOps.

The first panel is the Osong external-flood case. It joins the 10-minute Miho
River stage, nearby HRFCO rainfall, upstream/downstream gauge context, and
official flood-control-office alert issuances. Missing site instrumentation is
kept empty and described in feature_readiness.csv; no operational control rule
is inferred from this dataset.

Run from any directory:
    python data/scripts/build_multifactor_dataset.py
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "multifactor"
FACILITY_ID = "gungpyeong2-underpass"
EVENT_ID = "osong-2023"

INPUTS = {
    "facility_links": ROOT / "data/processed/facilities/facility_gauge_links.csv",
    "underpass_inventory": ROOT / "data/processed/facilities/underpass_inventory.csv",
    "registry": ROOT / "data/facilities/registry.json",
    "station_catalog": ROOT / "data/manifests/hrfco-stations.json",
    "kma_aws_stations": ROOT / "data/processed/kma/aws_stations.json",
    "water_primary": ROOT / "data/processed/hrfco/waterlevel_3011665_10M.csv",
    "water_upstream": ROOT / "data/processed/hrfco/waterlevel_3011635_10M.csv",
    "water_downstream": ROOT / "data/processed/hrfco/waterlevel_3011685_10M.csv",
    "rain_primary": ROOT / "data/processed/hrfco/rainfall_30114070_10M.csv",
    "flood_alerts": ROOT / "data/processed/flood_forecast/flood_forecast_issuances.csv",
    "history_manifest": ROOT / "data/manifests/hrfco-history.json",
    "osong_event_rain": ROOT / "data/processed/osong/osong_kma_aws_rainfall_2023-07-14_17.csv",
}

PMO_SOURCE = "https://www.opm.go.kr/opm/news/press-release.do?articleNo=154431&attachNo=136402&mode=download"
KMA_WARNING_SOURCE = "https://www.weather.go.kr/w/forecast/guide/standard.do"
MOIS_DEPTH_SOURCE = "https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=125943"

FACILITY_COLUMNS = [
    "facility_id", "facility_name", "facility_source", "facility_kind", "longitude", "latitude",
    "inflow_path_class", "inflow_path_status", "inflow_path_evidence",
    "catalog_record_id", "catalog_grade", "catalog_grade_status", "catalog_structure",
    "river_station_id", "river_station_name", "river_station_distance_km", "river_station_within_5km",
    "river_attention_m", "river_advisory_m", "river_warning_m", "river_planned_flood_m",
    "rain_station_id", "rain_station_name", "rain_station_distance_km", "rain_station_within_5km",
    "lowest_inlet_elevation_m", "lowest_inlet_elevation_status", "water_surface_gap_m", "water_surface_gap_status",
    "pump_capacity_m3s", "pump_capacity_status", "pump_inflow_ratio", "pump_inflow_ratio_status",
    "site_depth_sensor_status", "facility_specific_control_depth_cm", "facility_control_depth_status",
    "profile_source_status",
]

PANEL_COLUMNS = [
    "timestamp_kst", "facility_id", "event_id",
    "river_primary_station_id", "river_primary_stage_m", "river_primary_trend_30m_m_per_h",
    "river_trend_30m_qc_status", "river_minutes_to_warning_linear", "river_minutes_to_planned_flood_linear", "river_primary_data_status",
    "river_primary_stage_step_10m_m", "river_primary_step_qc_status",
    "river_upstream_station_id", "river_upstream_stage_m", "river_upstream_trend_30m_m_per_h",
    "river_downstream_station_id", "river_downstream_stage_m", "river_downstream_trend_30m_m_per_h",
    "rain_station_id", "rain_station_distance_km", "rain_station_within_5km", "rain_10m_mm",
    "rain_1h_mm", "rain_1h_valid_bins", "rain_3h_mm", "rain_3h_valid_bins",
    "rain_12h_mm", "rain_12h_valid_bins", "rain_data_status",
    "rain_3h_advisory_reference_exceeded", "rain_3h_warning_reference_exceeded",
    "rain_12h_advisory_reference_exceeded", "rain_12h_warning_reference_exceeded",
    "official_flood_alert_state", "official_flood_alert_kind", "official_flood_alert_issued_at",
    "official_flood_alert_age_min", "official_flood_forecast_level_m", "official_flood_forecast_at",
    "rainfall_threshold_interpretation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def maybe_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def show_number(value: float | None, places: int = 3) -> str:
    if value is None:
        return ""
    return f"{value:.{places}f}".rstrip("0").rstrip(".")


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M")


def station_rows(catalog: dict[str, Any], kind: str) -> dict[str, dict[str, Any]]:
    entries = catalog.get("kinds", {}).get(kind, {}).get("stations", [])
    return {str(row.get("code")): row for row in entries}


def load_value_series(path: Path, value_field: str) -> tuple[dict[str, float | None], list[str]]:
    rows = read_csv(path)
    values = {row["timestamp_kst"]: maybe_float(row.get(value_field)) for row in rows}
    return values, [row["timestamp_kst"] for row in rows]


def build_profiles() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    links = read_csv(INPUTS["facility_links"])
    catalog = json.loads(INPUTS["station_catalog"].read_text(encoding="utf-8-sig"))
    water_stations = station_rows(catalog, "waterlevel")
    by_facility: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in links:
        by_facility[row["facility_id"]].append(row)

    inventory_rows = read_csv(INPUTS["underpass_inventory"])
    inventory_by_id = {row["source_record_id"]: row for row in inventory_rows if row.get("source_record_id")}
    # This explicit crosswalk is recorded in the registry note: the Osong
    # underpass is source record 15124755:518 in the national asset catalogue.
    catalogue_crosswalk = {FACILITY_ID: "15124755:518"}
    registry = json.loads(INPUTS["registry"].read_text(encoding="utf-8-sig"))
    registry_by_id = {row.get("id"): row for row in registry.get("facilities", [])}

    profiles: list[dict[str, Any]] = []
    for facility_id, facility_links in sorted(by_facility.items()):
        facility_links.sort(key=lambda row: (row.get("kind", ""), int(row.get("rank") or 999)))
        first = facility_links[0]
        river = next((r for r in facility_links if r.get("kind") == "waterlevel" and r.get("rank") == "1"), {})
        rain = next((r for r in facility_links if r.get("kind") == "rainfall" and r.get("rank") == "1"), {})
        registered = registry_by_id.get(facility_id, {})
        inflow_gate = registered.get("gates", {}).get("inflow_path", {})
        inflow_confirmed = inflow_gate.get("status") == "CONFIRMED"

        catalog_id = catalogue_crosswalk.get(facility_id, facility_id)
        catalog = inventory_by_id.get(catalog_id, {})
        raw_attributes = catalog.get("source_attributes_json", "")
        try:
            attributes = json.loads(raw_attributes) if raw_attributes else {}
        except json.JSONDecodeError:
            attributes = {}
        grade = attributes.get("종별", "")
        grade_status = catalog.get("status", "") if grade else "NOT_AVAILABLE"

        profiles.append({
            "facility_id": facility_id,
            "facility_name": first.get("facility_name", ""),
            "facility_source": first.get("facility_source", ""),
            "facility_kind": "underpass" if catalog or registered.get("kind") == "underpass" or facility_id == FACILITY_ID else "unclassified",
            "longitude": first.get("facility_lon", ""),
            "latitude": first.get("facility_lat", ""),
            "inflow_path_class": ("external_river_levee_breach" if facility_id == FACILITY_ID else registered.get("driver", "")) if inflow_confirmed else "",
            "inflow_path_status": inflow_gate.get("status", "UNKNOWN"),
            "inflow_path_evidence": inflow_gate.get("note", ""),
            "catalog_record_id": catalog_id if catalog else "",
            "catalog_grade": grade,
            "catalog_grade_status": grade_status,
            "catalog_structure": catalog.get("structure_raw", ""),
            "river_station_id": river.get("station_code", ""),
            "river_station_name": river.get("station_name", ""),
            "river_station_distance_km": river.get("distance_km", ""),
            "river_station_within_5km": river.get("within_max_km", ""),
            "river_attention_m": show_number(maybe_float(water_stations.get(river.get("station_code", ""), {}).get("attwl")), 3),
            "river_advisory_m": river.get("advisory_m", ""),
            "river_warning_m": river.get("warning_m", ""),
            "river_planned_flood_m": river.get("planned_flood_m", ""),
            "rain_station_id": rain.get("station_code", ""),
            "rain_station_name": rain.get("station_name", ""),
            "rain_station_distance_km": rain.get("distance_km", ""),
            "rain_station_within_5km": rain.get("within_max_km", ""),
            "lowest_inlet_elevation_m": "",
            "lowest_inlet_elevation_status": "NOT_AVAILABLE",
            "water_surface_gap_m": "",
            "water_surface_gap_status": "NOT_CALCULABLE_WITHOUT_SITE_ELEVATION",
            "pump_capacity_m3s": "",
            "pump_capacity_status": "NOT_AVAILABLE",
            "pump_inflow_ratio": "",
            "pump_inflow_ratio_status": "NOT_AVAILABLE",
            "site_depth_sensor_status": "NOT_AVAILABLE",
            "facility_specific_control_depth_cm": "",
            "facility_control_depth_status": "NOT_CONFIRMED",
            "profile_source_status": "PARTIAL" if (inflow_confirmed or grade) else "CANDIDATE",
        })

    return profiles, {
        "candidate_facility_count": len(profiles),
        "inflow_path_confirmed_count": sum(row["inflow_path_status"] == "CONFIRMED" for row in profiles),
        "catalog_grade_available_count": sum(bool(row["catalog_grade"]) for row in profiles),
        "facility_grade_note": "Catalog fields are preserved with their catalogue status; a catalogue listing is not a site inspection.",
    }


def build_threshold_reference(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    stations = station_rows(catalog, "waterlevel")
    primary = stations["3011665"]
    rows: list[dict[str, Any]] = []
    for key, label in (("attwl", "attention"), ("wrnwl", "advisory"), ("almwl", "warning"), ("pfh", "planned_flood")):
        rows.append({
            "threshold_id": f"hrfco_3011665_{label}", "route": "river", "level": label,
            "metric": "water_level_m", "value": show_number(maybe_float(primary.get(key)), 3), "unit": "m",
            "source_name": "HRFCO water-level station catalogue", "source_url": "https://api.hrfco.go.kr/",
            "source_record": "data/manifests/hrfco-stations.json · station 3011665",
            "source_vintage": "2026-10-10 station catalogue snapshot", "use_status": "CURRENT_STATION_REFERENCE",
            "interpretation": "The current station metadata may differ from historical site-specific criteria; do not treat it as a historical truth without checking the event-year source.",
        })
    for window, levels in (("3h", (("advisory", 60), ("warning", 90))), ("12h", (("advisory", 110), ("warning", 180)))):
        for level, value in levels:
            rows.append({
                "threshold_id": f"kma_heavy_rain_{level}_{window}", "route": "rain", "level": level,
                "metric": f"expected_rainfall_{window}_mm", "value": str(value), "unit": "mm",
                "source_name": "KMA weather warning criteria", "source_url": KMA_WARNING_SOURCE,
                "source_record": "KMA weather warning criteria page", "source_vintage": "checked 2026-10-19",
                "use_status": "FORECAST_THRESHOLD_REFERENCE",
                "interpretation": "Official criterion is based on expected precipitation. Comparing observed rainfall to it is a retrospective reference screen, not a KMA alert or an operational trigger.",
            })
    rows.append({
        "threshold_id": "mois_underpass_depth_reference_5cm", "route": "field_confirmation",
        "level": "immediate_control_reference", "metric": "observed_water_depth_cm", "value": "5", "unit": "cm",
        "source_name": "Ministry of the Interior and Safety underpass control guidance", "source_url": MOIS_DEPTH_SOURCE,
        "source_record": "2026 guidance on underpass water-depth control", "source_vintage": "checked 2026-10-19",
        "use_status": "POLICY_REFERENCE_SITE_APPLICABILITY_PENDING",
        "interpretation": "The source describes immediate vehicle restriction above 5 cm and stricter thresholds at high-risk sites. Confirm the applicable facility plan; this is not an observed depth or a universal per-site value.",
    })
    return rows


def build_readiness() -> list[dict[str, str]]:
    return [
        {"feature": "representative_river_stage", "route": "river", "status": "ACQUIRED", "coverage": "3011665 · 2019-01 through latest observed row; 10-minute", "source": "HRFCO waterlevel 10M", "limitation": "The gauge is 1.17 km from the underpass; gauge-to-site hydrologic representativeness still needs facility review."},
        {"feature": "upstream_and_downstream_stage", "route": "river", "status": "ACQUIRED", "coverage": "3011635 and 3011685 · seasonal 10-minute records, 2019-06 through 2026-09", "source": "HRFCO waterlevel 10M", "limitation": "Use as observed context; station-to-site travel time has not been calibrated."},
        {"feature": "official_flood_forecast_issuance", "route": "river", "status": "ACQUIRED", "coverage": "Historical issue/change/release records for gauge 3011665", "source": "HRFCO flood forecast issuance CSV", "limitation": "This is river flood forecasting, not KMA heavy-rain forecast issuance."},
        {"feature": "rainfall_1_3_12h", "route": "rain", "status": "ACQUIRED_WITH_DISTANCE_CAVEAT", "coverage": "30114070 · 10-minute, 2019-06 through 2026-09; 5.38 km from the facility", "source": "HRFCO rainfall 10M", "limitation": "Within the proposed 10 km screening radius but beyond the existing 5 km representative-gauge cutoff; rainfall can differ across the site."},
        {"feature": "independent_event_rainfall", "route": "rain", "status": "ACQUIRED_REGIONAL_CROSSCHECK", "coverage": "KMA AWS stations 327 and 977 · hourly observations during the Osong event", "source": "KMA AWS/ASOS event CSV plus KMA station catalogue", "limitation": "Both stations are regional context beyond 10 km; they are not treated as facility-local rainfall."},
        {"feature": "kma_heavy_rain_issuance_history", "route": "rain", "status": "NOT_ACQUIRED", "coverage": "No historical warning issuance series joined", "source": "KMA warning history API approval pending", "limitation": "Do not backfill a past issue state from current warnings."},
        {"feature": "dam_release", "route": "river", "status": "NOT_LINKED", "coverage": "No dam linked to the Osong facility record", "source": "Facility-specific basin linkage not supplied", "limitation": "A downstream-facility release feature is only applicable where a reservoir is hydraulically relevant."},
        {"feature": "upstream_travel_time", "route": "river", "status": "NOT_CALIBRATED", "coverage": "Upstream gauge stage is present; travel-time value is empty", "source": "Requires paired event hydrographs and routing validation", "limitation": "Do not relabel stage differences or peak lags as water travel time."},
        {"feature": "facility_protection_grade", "route": "vulnerability", "status": "CATALOG_ONLY_UNVERIFIED", "coverage": "Osong catalogue record 15124755:518 lists 2종", "source": "National underpass inventory catalogue", "limitation": "The catalogue row is unverified and is not a current field inspection."},
        {"feature": "lowest_inlet_elevation_and_stage_gap", "route": "vulnerability", "status": "NOT_AVAILABLE", "coverage": "No surveyed underpass low-point elevation", "source": "Facility survey / design drawing needed", "limitation": "DEM surface elevation is not a substitute for the surveyed lowest entry point."},
        {"feature": "temporary_levee_or_work_condition", "route": "vulnerability", "status": "EVENT_LABEL_ONLY", "coverage": "Temporary levee overflow and breach are labelled for Osong 2023", "source": "Official Osong investigation", "limitation": "No live or historic construction-condition feed is joined."},
        {"feature": "pump_capacity_and_inflow", "route": "vulnerability", "status": "NOT_AVAILABLE", "coverage": "No facility pump capacity or runoff inflow series", "source": "Managing authority asset and telemetry records needed", "limitation": "Pump-to-inflow ratio cannot be calculated."},
        {"feature": "onsite_water_depth_and_pump_state", "route": "field_confirmation", "status": "NOT_AVAILABLE", "coverage": "No time-stamped field depth or pump-state sensor readings", "source": "Managing authority telemetry / CCTV integration needed", "limitation": "The official 5 cm policy reference cannot be compared to an observed depth in this case."},
    ]


def build_stage_design() -> list[dict[str, str]]:
    return [
        {
            "stage_order": "1", "stage": "관심", "river_path_signal": "시설 대표 관측소의 관심 기준 접근·상승 추세",
            "rain_path_signal": "1·3·12시간 관측 누적의 증가 또는 특보 기준 접근",
            "vulnerability_adjustment": "취약성 자료와 조기 단계 이동 효과 검증 전에는 적용하지 않음",
            "field_override": "없음", "operator_action": "자료 신선도·관측소 대표성 확인",
            "required_evidence": "수위·강우 관측과 품질·관측시각", "validation_status": "DATA_AVAILABLE_RULE_UNCALIBRATED",
        },
        {
            "stage_order": "2", "stage": "주의", "river_path_signal": "공식 홍수주의보 또는 검증된 시설별 수위 기준",
            "rain_path_signal": "공식 호우주의보 발효; 관측 누적은 예보 기준과 참고 비교",
            "vulnerability_adjustment": "확인된 고위험 시설에서만 한 단계 조기화 후보를 검증",
            "field_override": "현장 이상 보고가 있으면 단계 검토를 요청",
            "operator_action": "담당자 알림·현장 및 시설 상태 확인",
            "required_evidence": "발령·발효 이력, 지점별 기준, 통제·침수 기록", "validation_status": "KMA_HISTORICAL_ISSUANCE_AND_SITE_REVIEW_PENDING",
        },
        {
            "stage_order": "3", "stage": "통제 준비", "river_path_signal": "공식 홍수경보 또는 시설별 준비 기준 도달",
            "rain_path_signal": "공식 호우경보 또는 검증된 강우·배수 용량 조건",
            "vulnerability_adjustment": "임시제방·공사·저점 등 확인된 상태만 반영",
            "field_override": "펌프 정지·배수 장애·제방 이상은 별도 신호로 표시",
            "operator_action": "차단시설·우회·인력과 통제 절차 준비",
            "required_evidence": "특보·관측, 펌프 용량·가동·유입, 시설 상태", "validation_status": "PUMP_AND_SITE_STATE_DATA_MISSING",
        },
        {
            "stage_order": "4", "stage": "통제 검토", "river_path_signal": "시설별 통제 검토 기준 또는 검증된 도달 예상시간 조건",
            "rain_path_signal": "시설별 내수 기준과 공식 특보·펌프 부담을 함께 확인",
            "vulnerability_adjustment": "검증된 시설 취약성으로만 단계 상향; 임의 가중치 금지",
            "field_override": "현장 확인 결과와 공식 기준을 한 화면에서 검토",
            "operator_action": "사람이 통제 여부와 시각을 결정하고 근거를 기록",
            "required_evidence": "시설별 승인 기준·경로별 신호·과거 통제 대조", "validation_status": "EXISTING_OSONG_RULE_IS_PROTOTYPE_ONLY",
        },
        {
            "stage_order": "5", "stage": "즉시 통제", "river_path_signal": "시설 유입·침수 관측 또는 현행 공식 시설 통제 조건 충족",
            "rain_path_signal": "현장 침수심이 적용 가능한 공식 시설 기준을 초과",
            "vulnerability_adjustment": "취약성은 조기 경보에만 사용; 현장 통제 기준을 늦추지 않음",
            "field_override": "현장 실측과 시설별 통제계획 우선",
            "operator_action": "기존 SOP에 따라 진입 차단 및 우회 안내",
            "required_evidence": "시각이 있는 현장 침수심·통제 기준·차단기 상태", "validation_status": "5CM_POLICY_REFERENCE_SITE_APPLICABILITY_AND_SENSOR_DATA_PENDING",
        },
    ]


def build_event_labels() -> list[dict[str, str]]:
    shared = {
        "event_id": EVENT_ID,
        "facility_id": FACILITY_ID,
        "inflow_path_class": "external_river_flood_via_temporary_levee_breach",
        "source_status": "OFFICIAL_REPORT_OR_HRFCO_ISSUANCE",
        "source_url": PMO_SOURCE,
    }
    facts = [
        ("2023-07-14 17:20", "flood_advisory_issued", "river", "minute", "HRFCO flood issuance CSV", "홍수주의보 발령"),
        ("2023-07-15 04:10", "flood_warning_issued", "river", "minute", "HRFCO flood issuance CSV", "홍수경보 변경발령"),
        ("2023-07-15 06:40", "facility_control_criterion_met", "river", "minute", "Prime Minister's Office Osong investigation", "계획홍수위 도달 및 지하차도 통제요건 충족"),
        ("2023-07-15 07:50", "temporary_levee_overtopping", "vulnerability", "reported minute", "Prime Minister's Office Osong investigation", "임시제방 월류"),
        ("2023-07-15 08:09", "temporary_levee_breach", "vulnerability", "reported minute", "Prime Minister's Office Osong investigation", "임시제방 붕괴"),
        ("2023-07-15 08:27", "river_water_entered_underpass", "outcome", "reported minute", "Prime Minister's Office Osong investigation", "지하차도 유입 시작"),
        ("2023-07-15 08:35", "underpass_unsafe_to_drive", "outcome", "reported minute", "Prime Minister's Office Osong investigation", "차량 주행 곤란"),
        ("2023-07-15 08:40", "underpass_fully_inundated", "outcome", "reported minute", "Prime Minister's Office Osong investigation", "지하차도 완전 침수"),
    ]
    rows = []
    for index, fact in enumerate(facts, start=1):
        at, label, route, precision, source, note = fact
        source_url = "https://api.hrfco.go.kr/" if source.startswith("HRFCO") else PMO_SOURCE
        source_record = "data/processed/flood_forecast/flood_forecast_issuances.csv · station 3011665" if source.startswith("HRFCO") else "official Osong investigation report"
        rows.append({
            **shared, "label_id": f"{EVENT_ID}-{index:02d}", "occurred_at_kst": at,
            "label": label, "route": route, "time_precision": precision,
            "source_name": source, "source_url": source_url, "source_record": source_record, "source_note": note,
        })
    return rows


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def build_event_rainfall_crosscheck() -> tuple[Path, int]:
    aws_catalog = json.loads(INPUTS["kma_aws_stations"].read_text(encoding="utf-8-sig"))
    stations = aws_catalog.get("stations", {})
    observations = read_csv(INPUTS["osong_event_rain"])
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in observations:
        grouped[row["station_id"]].append(row)
    output_rows: list[dict[str, Any]] = []
    facility_lon, facility_lat = 127.3376, 36.6246
    for station_id, rows in sorted(grouped.items()):
        station = stations.get(station_id, {})
        queue: deque[float | None] = deque()
        total = 0.0
        valid_count = 0
        previous: datetime | None = None
        for row in sorted(rows, key=lambda item: item["timestamp_kst"]):
            now = parse_timestamp(row["timestamp_kst"])
            value = maybe_float(row.get("rainfall_mm"))
            # A missing hour breaks the rolling window rather than being filled with zero.
            if previous is None or now - previous != timedelta(hours=1):
                queue.clear()
                total = 0.0
                valid_count = 0
            queue.append(value)
            if value is not None:
                total += value
                valid_count += 1
            if len(queue) > 12:
                old = queue.popleft()
                if old is not None:
                    total -= old
                    valid_count -= 1
            queued_values = list(queue)
            last_three = queued_values[-3:]
            values = {"1h": value if value is not None else None, "3h": None, "12h": None}
            if len(last_three) == 3 and all(item is not None for item in last_three):
                values["3h"] = sum(item for item in last_three if item is not None)
            if len(queue) == 12 and valid_count == 12:
                values["12h"] = total
            station_lon = maybe_float(station.get("lon"))
            station_lat = maybe_float(station.get("lat"))
            distance = haversine_km(facility_lon, facility_lat, station_lon, station_lat) if station_lon is not None and station_lat is not None else None
            output_rows.append({
                "event_id": EVENT_ID,
                "facility_id": FACILITY_ID,
                "timestamp_kst": row["timestamp_kst"],
                "station_id": station_id,
                "station_name": row.get("station_name", ""),
                "distance_to_facility_km": show_number(distance, 2),
                "distance_scope": "regional_context_only_over_10km" if distance is not None and distance > 10 else "within_10km",
                "rain_1h_observed_mm": show_number(values["1h"]),
                "rain_3h_observed_mm": show_number(values["3h"]),
                "rain_12h_observed_mm": show_number(values["12h"]),
                "rain_3h_coverage_hours": sum(item is not None for item in last_three),
                "rain_12h_coverage_hours": valid_count,
                "rain_3h_advisory_reference_exceeded": "" if values["3h"] is None else str(values["3h"] >= 60).lower(),
                "rain_3h_warning_reference_exceeded": "" if values["3h"] is None else str(values["3h"] >= 90).lower(),
                "rain_12h_advisory_reference_exceeded": "" if values["12h"] is None else str(values["12h"] >= 110).lower(),
                "rain_12h_warning_reference_exceeded": "" if values["12h"] is None else str(values["12h"] >= 180).lower(),
                "source_type": row.get("source_type", ""),
                "data_status": row.get("data_status", ""),
                "threshold_interpretation": "OBSERVED_VS_FORECAST_CRITERION_REFERENCE_ONLY",
            })
            previous = now
    path = OUT / EVENT_ID / "rainfall-crosscheck-hourly.csv"
    if output_rows:
        write_csv(path, list(output_rows[0].keys()), output_rows)
    else:
        raise RuntimeError("No KMA AWS event rainfall observations found")
    return path, len(output_rows)


def active_alert_rows() -> list[dict[str, str]]:
    rows = [row for row in read_csv(INPUTS["flood_alerts"]) if row.get("station_code") == "3011665"]
    rows.sort(key=lambda row: (row.get("issued_at", ""), row.get("number", "")))
    return rows


def next_alert_state(current: str, kind: str) -> str:
    if "해제" in kind:
        if "경보" in kind or current != "WARNING":
            return "NONE"
        return current
    if "경보" in kind:
        return "WARNING"
    if "주의보" in kind:
        return "ADVISORY"
    return current


def build_panel(thresholds: list[dict[str, Any]]) -> tuple[Path, dict[str, Any]]:
    primary, timestamps = load_value_series(INPUTS["water_primary"], "wl")
    upstream, _ = load_value_series(INPUTS["water_upstream"], "wl")
    downstream, _ = load_value_series(INPUTS["water_downstream"], "wl")
    rain, _ = load_value_series(INPUTS["rain_primary"], "rf")

    observed_primary_times = [stamp for stamp, value in primary.items() if value is not None]
    if not observed_primary_times:
        raise RuntimeError("Primary river gauge has no observed readings")
    end = max(observed_primary_times)
    timestamps = [stamp for stamp in timestamps if stamp <= end]
    datetimes = [parse_timestamp(stamp) for stamp in timestamps]

    rain_windows = {6: deque(), 18: deque(), 72: deque()}
    rain_sums = {6: 0.0, 18: 0.0, 72: 0.0}
    rain_valid_counts = {6: 0, 18: 0, 72: 0}
    issue_rows = active_alert_rows()
    issue_index = 0
    alert_state = "NONE"
    last_issue: dict[str, str] = {}
    active_issue: dict[str, str] = {}
    rain_distance = "5.38"
    primary_warning = 8.0
    primary_planned = 9.38

    target = OUT / EVENT_ID / "facility-timeseries-10m.csv.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as raw_handle:
        with gzip.GzipFile(fileobj=raw_handle, mode="wb", mtime=0, compresslevel=6) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text_handle:
                writer = csv.DictWriter(text_handle, fieldnames=PANEL_COLUMNS, lineterminator="\n")
                writer.writeheader()
                complete_rain_windows = {"1h": 0, "3h": 0, "12h": 0}
                rows_written = 0
                alert_state_counts: dict[str, int] = defaultdict(int)

                for index, (stamp, now) in enumerate(zip(timestamps, datetimes)):
                    current_rain = rain.get(stamp)
                    current_rain_text = current_rain
                    window_values: dict[int, float | None] = {}
                    window_counts: dict[int, int] = {}
                    for bins, queue in rain_windows.items():
                        item = current_rain
                        queue.append(item)
                        if item is not None:
                            rain_sums[bins] += item
                            rain_valid_counts[bins] += 1
                        if len(queue) > bins:
                            removed = queue.popleft()
                            if removed is not None:
                                rain_sums[bins] -= removed
                                rain_valid_counts[bins] -= 1
                        window_counts[bins] = rain_valid_counts[bins]
                        window_values[bins] = rain_sums[bins] if len(queue) == bins and rain_valid_counts[bins] == bins else None

                    stage = primary.get(stamp)
                    stage10 = primary.get(timestamps[index - 1]) if index else None
                    stage_step = stage - stage10 if stage is not None and stage10 is not None else None
                    qc = "MISSING" if stage is None else "OK"
                    if stage_step is not None and abs(stage_step) >= 3.0:
                        qc = "LARGE_STEP_GE_3M_REVIEW"
                    elif stage_step is not None and abs(stage_step) >= 0.3:
                        qc = "STEP_GE_0_3M_REVIEW"

                    stage30 = None
                    rate_status = "MISSING_OR_GAP"
                    if stage is not None:
                        lookback = [now - timedelta(minutes=offset) for offset in (30, 20, 10, 0)]
                        values = [primary.get(value.strftime("%Y-%m-%d %H:%M")) for value in lookback]
                        if all(value is not None for value in values):
                            stage30 = (values[-1] - values[0]) / 0.5
                            rate_status = "OK" if all(abs(values[n] - values[n - 1]) < 0.3 for n in range(1, len(values))) else "STEP_REVIEW"

                    minutes_warning = None
                    minutes_planned = None
                    if stage is not None and stage30 is not None and stage30 > 0 and rate_status == "OK":
                        minutes_warning = max(0.0, (primary_warning - stage) / stage30 * 60.0)
                        minutes_planned = max(0.0, (primary_planned - stage) / stage30 * 60.0)

                    while issue_index < len(issue_rows) and issue_rows[issue_index].get("issued_at", "") <= stamp.replace(" ", "T"):
                        last_issue = issue_rows[issue_index]
                        alert_state = next_alert_state(alert_state, last_issue.get("kind", ""))
                        if "해제" in last_issue.get("kind", ""):
                            if alert_state == "NONE":
                                active_issue = {}
                        else:
                            active_issue = last_issue
                        issue_index += 1
                    alert_state_counts[alert_state] += 1

                    def threshold_exceeded(value: float | None, threshold: float) -> str:
                        return "" if value is None else str(value >= threshold).lower()

                    row = {
                        "timestamp_kst": stamp,
                        "facility_id": FACILITY_ID,
                        "event_id": EVENT_ID if "2023-07-14 12:00" <= stamp <= "2023-07-15 08:40" else "",
                        "river_primary_station_id": "3011665",
                        "river_primary_stage_m": show_number(stage),
                        "river_primary_trend_30m_m_per_h": show_number(stage30),
                        "river_trend_30m_qc_status": rate_status,
                        "river_minutes_to_warning_linear": show_number(minutes_warning, 1) if rate_status == "OK" else "",
                        "river_minutes_to_planned_flood_linear": show_number(minutes_planned, 1) if rate_status == "OK" else "",
                        "river_primary_data_status": "MISSING" if stage is None else "SOURCE_OBSERVED",
                        "river_primary_stage_step_10m_m": show_number(stage_step),
                        "river_primary_step_qc_status": qc,
                        "river_upstream_station_id": "3011635",
                        "river_upstream_stage_m": show_number(upstream.get(stamp)),
                        "river_upstream_trend_30m_m_per_h": show_number(_trend(upstream, now)),
                        "river_downstream_station_id": "3011685",
                        "river_downstream_stage_m": show_number(downstream.get(stamp)),
                        "river_downstream_trend_30m_m_per_h": show_number(_trend(downstream, now)),
                        "rain_station_id": "30114070",
                        "rain_station_distance_km": rain_distance,
                        "rain_station_within_5km": "false",
                        "rain_10m_mm": show_number(current_rain),
                        "rain_1h_mm": show_number(window_values[6]),
                        "rain_1h_valid_bins": window_counts[6],
                        "rain_3h_mm": show_number(window_values[18]),
                        "rain_3h_valid_bins": window_counts[18],
                        "rain_12h_mm": show_number(window_values[72]),
                        "rain_12h_valid_bins": window_counts[72],
                        "rain_data_status": "MISSING" if current_rain is None else "SOURCE_OBSERVED",
                        "rain_3h_advisory_reference_exceeded": threshold_exceeded(window_values[18], 60),
                        "rain_3h_warning_reference_exceeded": threshold_exceeded(window_values[18], 90),
                        "rain_12h_advisory_reference_exceeded": threshold_exceeded(window_values[72], 110),
                        "rain_12h_warning_reference_exceeded": threshold_exceeded(window_values[72], 180),
                        "official_flood_alert_state": alert_state,
                        "official_flood_alert_kind": active_issue.get("kind", ""),
                        "official_flood_alert_issued_at": active_issue.get("issued_at", ""),
                        "official_flood_alert_age_min": _minutes_since(now, active_issue.get("issued_at", "")),
                        "official_flood_forecast_level_m": active_issue.get("forecast_level_m", ""),
                        "official_flood_forecast_at": active_issue.get("forecast_time", ""),
                        "rainfall_threshold_interpretation": "OBSERVED_VS_FORECAST_CRITERION_REFERENCE_ONLY",
                    }
                    writer.writerow(row)
                    rows_written += 1
                    complete_rain_windows["1h"] += window_values[6] is not None
                    complete_rain_windows["3h"] += window_values[18] is not None
                    complete_rain_windows["12h"] += window_values[72] is not None

    panel_summary = {
        "path": target.relative_to(ROOT).as_posix(),
        "sha256": sha256(target),
        "compression": "gzip, mtime=0",
        "rows": rows_written,
        "first_timestamp_kst": timestamps[0],
        "last_timestamp_kst": timestamps[-1],
        "rain_complete_window_rows": complete_rain_windows,
        "official_alert_state_row_counts": dict(alert_state_counts),
        "primary_river_stage_thresholds_used_for_linear_diagnostics_m": {
            "warning": primary_warning,
            "planned_flood": primary_planned,
            "source_vintage": "HRFCO station catalogue fetched 2026-10-10; historical threshold history not joined",
        },
        "rain_station_distance_km": float(rain_distance),
        "rain_station_within_5km": False,
    }
    return target, panel_summary


def _trend(series: dict[str, float | None], now: datetime) -> float | None:
    current = series.get(now.strftime("%Y-%m-%d %H:%M"))
    past = series.get((now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"))
    if current is None or past is None:
        return None
    for offset in (20, 10):
        if series.get((now - timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M")) is None:
            return None
    return (current - past) / 0.5


def _minutes_since(now: datetime, issued_at: str) -> str:
    if not issued_at:
        return ""
    issued = datetime.strptime(issued_at, "%Y-%m-%dT%H:%M")
    return str(int((now - issued).total_seconds() // 60))


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Required source files are missing: " + ", ".join(missing))

    OUT.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(INPUTS["station_catalog"].read_text(encoding="utf-8-sig"))
    profiles, profile_summary = build_profiles()
    profile_path = OUT / "facility-profiles.csv"
    write_csv(profile_path, FACILITY_COLUMNS, profiles)

    thresholds = build_threshold_reference(catalog)
    threshold_path = OUT / "threshold-reference.csv"
    write_csv(threshold_path, list(thresholds[0].keys()), thresholds)

    readiness = build_readiness()
    readiness_path = OUT / "feature-readiness.csv"
    write_csv(readiness_path, list(readiness[0].keys()), readiness)

    stage_design = build_stage_design()
    stage_design_path = OUT / "stage-design.csv"
    write_csv(stage_design_path, list(stage_design[0].keys()), stage_design)

    event_labels = build_event_labels()
    labels_path = OUT / EVENT_ID / "event-labels.csv"
    write_csv(labels_path, list(event_labels[0].keys()), event_labels)

    rainfall_crosscheck_path, rainfall_crosscheck_rows = build_event_rainfall_crosscheck()
    panel_path, panel_summary = build_panel(thresholds)
    output_files = [profile_path, threshold_path, readiness_path, stage_design_path, labels_path, rainfall_crosscheck_path, panel_path]
    inputs = {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
        for name, path in INPUTS.items()
    }
    manifest = {
        "schema_version": "1.0",
        "dataset_id": "floodops-multifactor-v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "script": "data/scripts/build_multifactor_dataset.py",
        "scope": "facility candidate inventory plus an all-available-period 10-minute Osong external-flood feature panel",
        "profiles": profile_summary,
        "osong_panel": panel_summary,
        "event_labels": {"path": labels_path.relative_to(ROOT).as_posix(), "rows": len(event_labels), "sha256": sha256(labels_path)},
        "event_rainfall_crosscheck": {"path": rainfall_crosscheck_path.relative_to(ROOT).as_posix(), "rows": rainfall_crosscheck_rows, "sha256": sha256(rainfall_crosscheck_path)},
        "feature_readiness": {"path": readiness_path.relative_to(ROOT).as_posix(), "rows": len(readiness), "sha256": sha256(readiness_path)},
        "stage_design": {"path": stage_design_path.relative_to(ROOT).as_posix(), "rows": len(stage_design), "sha256": sha256(stage_design_path)},
        "threshold_reference": {"path": threshold_path.relative_to(ROOT).as_posix(), "rows": len(thresholds), "sha256": sha256(threshold_path)},
        "inputs": inputs,
        "method_notes": [
            "Observed HRFCO rainfall is summed over the trailing 6, 18, and 72 ten-minute bins. A window is blank unless every bin is present and numeric.",
            "River 30-minute rates use endpoint change over 30 minutes, and are blank unless all four 10-minute readings are present. Linear time-to-threshold is a retrospective diagnostic, not a forecast.",
            "Observed rainfall is compared with KMA expected-rainfall criteria only as a reference screen; historical KMA warning issuance is not joined.",
            "Raw gauge values are preserved. A change of at least 0.3 m per 10 minutes is flagged for review; changes of at least 3 m are separately flagged. No reading is silently removed.",
            "The historical case labels an external river flood through temporary-levee failure. It does not supply a continuous levee-condition feature, measured underpass depth, pump telemetry, or surveyed low-point elevation.",
            "Current station thresholds are included as metadata references. Their values are not asserted to be the values in force during every historical year.",
        ],
        "outputs": [
            {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in output_files
        ],
    }
    manifest_path = ROOT / "data/manifests/multifactor-dataset.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": manifest_path.relative_to(ROOT).as_posix(),
        "facility_profiles": len(profiles),
        "event_labels": len(event_labels),
        "event_rainfall_crosscheck_rows": rainfall_crosscheck_rows,
        "panel_rows": panel_summary["rows"],
        "panel_start": panel_summary["first_timestamp_kst"],
        "panel_end": panel_summary["last_timestamp_kst"],
        "rain_complete_window_rows": panel_summary["rain_complete_window_rows"],
        "stage_design_rows": len(stage_design),
        "output_files": [path.relative_to(ROOT).as_posix() for path in output_files],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
