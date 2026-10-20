"""Real-time risk of every river-contact facility, judged by the driver that floods it.

Most underpasses flood from local rain (내수), not from the river, so one indicator cannot rank them all:

- river:   the facility sits on the same river as a gauge and the gauge's past peaks come close to its
           ground (research grade B or better), or it is a riverside entrance. Judged by the gauge stage.
- pluvial: every other underpass. Judged by nearby 1-, 3- and 12-hour rain against the KMA heavy-rain
           advisory/warning amounts (호우주의보 3 h 60 mm / 12 h 110 mm, 호우경보 3 h 90 mm / 12 h 180 mm).
- live only: KMA heavy-rain alerts floor pluvial and riverside entrance levels when the alert-zone name
             matches the facility's province and municipality. Historical replay uses collected HRFCO
             flood forecasts only; the KMA alert-history API is not approved yet.

The rain thresholds are the national forecast-advisory amounts applied to observed rain. They say "rain at the
level the KMA warns about", not that a given underpass floods: pump capacity, sump and catchment decide that,
and those are not public. Facility-level control rules stay with the operational registry.
"""

from __future__ import annotations

import csv
import threading
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from . import flood_forecast as ff
from . import kma_aws
from . import kma_weather_warning as kww
from . import national_watch as nw

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_FILE = REPO_ROOT / "docs" / "research" / "underpass_river_influence" / "facility_river_influence_ranked.csv"

# 기상청 호우특보 기준 누적량. 12시간 기준은 시간별 HRFCO 자료가 연속해서 쌓인 경우에만 쓴다.
RAIN_3H_ADVISORY_MM = 60.0
RAIN_3H_WARNING_MM = 90.0
RAIN_12H_ADVISORY_MM = 110.0
RAIN_12H_WARNING_MM = 180.0
RAIN_1H_CASE_REFERENCE_MM_H = 95.0
RAIN_1H_STRONG_MM = 15.0  # 기상청 강수강도 '강한 비' 하한, 3시간 자료가 없을 때 1시간으로 대신 본다
SAME_RIVER_KM = 1.5
ELEVATION_HINT_MIN_M = -3.0

LEVELS = {0: "평상", 1: "관심", 2: "주의", 3: "경계", 4: "심각"}
RIVER_LEVEL = {"attention": 1, "advisory": 2, "warning": 3, "planned_flood": 4}
OFFICIAL_LEVEL = {"advisory": 2, "warning": 3}  # 홍수주의보 → 주의, 홍수경보 → 경계 (floor, never lowers)
LIMITATIONS = [
    "하천형은 같은 하천 1.5 km 안 관측소의 과거 최고 수위가 지면 근처까지 온 시설(조사 B등급 이상)과 하천변 출입구다. 나머지 지하차도는 내수형으로 추정한다.",
    "내수형은 시설 10 km 안 강우 관측소의 1·3·12시간 누적을 기상청 호우특보 기준량(3시간 60·90 mm, 12시간 110·180 mm)과 비교한다. 특보 기준은 예보용이며, 시설이 실제로 잠기는지는 배수·펌프 용량이 정한다.",
    "실시간 3시간 누적은 10분 자료가 충분하지 않으면 시간별 자료로 계산한다. 12시간 누적은 12개의 연속된 시간별 자료가 있어야 하며 로컬 캐시에 저장한다.",
    "기상청 AWS의 RN-15m은 원래 15분 누적으로 보존한다. 강한 비 보조 신호에만 시간당 환산값(×4)을 쓰며, 10분 강우나 호우특보 누적 기준으로 간주하지 않는다.",
    "기상청 호우특보는 시군구 이름이 직접 맞는 내수형·하천변 출입구에만 실시간 단계 하한으로 쓴다. 복합 특보구역 이름은 미매칭으로 남고, 과거 재생에는 현재 특보를 적용하지 않는다.",
]

_LOCK = threading.Lock()
_RAIN_HISTORY: dict[str, dict[datetime, float]] = {}  # live 10-minute rain per gauge, kept 3 hours


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


@lru_cache(maxsize=1)
def river_type_underpasses() -> dict[str, dict[str, Any]]:
    """Underpasses the 2026-10-16 research found river-driven, with the evidence that put them there."""
    out: dict[str, dict[str, Any]] = {}
    if not RESEARCH_FILE.exists():
        return out
    with RESEARCH_FILE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("dup_of") or row.get("coord_flag") or row.get("eligible", "").strip().lower() != "true":
                continue
            distance = _float(row.get("same_river_dist_m"))
            hint = _float(row.get("hint_maxclean_minus_ground_m"))
            years_advisory = _float(row.get("yrs_advisory")) or 0
            years_warning = _float(row.get("yrs_warning")) or 0
            if distance is None or distance > SAME_RIVER_KM * 1000 or hint is None or hint < ELEVATION_HINT_MIN_M or years_advisory < 1:
                continue
            out[row["facility_id"]] = {"grade": "A" if years_warning >= 1 else "B", "station_code": row["station_code"],
                                       "same_river_m": distance, "elevation_hint_m": hint,
                                       "years_advisory": int(years_advisory), "years_warning": int(years_warning)}
    return out


@lru_cache(maxsize=1)
def operational_names() -> tuple[str, ...]:
    return tuple(f["name"] for f in nw.facility_catalog() if f["tier"] == "operational")


@lru_cache(maxsize=1)
def duplicates_of_river_type() -> dict[str, str]:
    """Research rows marked as the same place as another row (e.g. 궁평지하차도 = 궁평2지하차도)."""
    out: dict[str, str] = {}
    if not RESEARCH_FILE.exists():
        return out
    with RESEARCH_FILE.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("dup_of"):
                out[row["facility_id"]] = row["dup_of"]
    return out


def driver_of(facility: dict[str, Any]) -> tuple[str, str]:
    if facility["tier"] == "operational":
        return "river", "운영 등록(시설별 규칙)"
    if facility["group"] == "riverside":
        return "river", "하천변 출입구"
    evidence = river_type_underpasses().get(facility["facility_id"])
    duplicate_note = duplicates_of_river_type().get(facility["facility_id"], "")
    if evidence is None and any(name in duplicate_note for name in operational_names()):
        return "river", "운영 시설과 같은 위치(중복 행)"
    if evidence:
        return "river", f"하천형 {evidence['grade']}등급(같은 하천 {evidence['same_river_m']:.0f} m, 경보 초과 {evidence['years_warning']}개 연도)"
    return "pluvial", "내수형 추정"


# ---- rain totals --------------------------------------------------------------------------------------
def _gauge(code: str) -> Any:
    """An HRFCO rain gauge, or a KMA AWS station for `kma:{stn}` codes (name, region, lon, lat)."""
    if code.startswith("kma:"):
        station = kma_aws.stations().get(code[4:])
        if station is None:
            return None
        return SimpleNamespace(name=f"{station['name']}(기상청 AWS)", region=nw.region_of(station["address"]), lon=station["lon"], lat=station["lat"])
    return nw.rain_gauges().get(code)


def _with_kma(rain_at: datetime | None, totals: dict[str, dict[str, float | None]], basis: str) -> tuple[datetime | None, dict[str, dict[str, float | None]], str]:
    """Live only: add KMA AWS stations (denser in cities) to the HRFCO gauges; an outage leaves HRFCO alone."""
    try:
        kma = kma_aws.rain_totals()
    except Exception:
        return rain_at, totals, basis
    if not kma["rows"]:
        return rain_at, totals, basis
    merged = {**totals, **{code: values for code, values in kma["rows"].items() if _gauge(code) is not None}}
    observed_at = max((stamp for stamp in (rain_at, kma["observed_at"]) if stamp is not None), default=None)
    return observed_at, merged, basis + " + 기상청 AWS 매분(RN-15m · RN-60m · RN-12H; 3시간 = RN-60m 3회 합)"


def _nearest_rain_codes(lon: float, lat: float, codes: set[str]) -> list[tuple[str, float]]:
    near = []
    for code in codes:
        gauge = _gauge(code)
        if gauge is None or abs(gauge.lat - lat) > 0.1 or abs(gauge.lon - lon) > 0.13:
            continue
        distance = nw._km(lon, lat, gauge.lon, gauge.lat)
        if distance <= nw.RAIN_LINK_KM:
            near.append((code, round(distance, 1)))
    return sorted(near, key=lambda item: item[1])


def _replay_totals(at: str) -> tuple[datetime, dict[str, dict[str, float | None]]]:
    hour = datetime.fromisoformat(at).replace(minute=0, second=0, microsecond=0)
    totals: dict[str, dict[str, float | None]] = {}
    for code in nw.stored_rain_codes():
        values = [nw.stored_value("rainfall", code, (hour - timedelta(hours=back)).strftime("%Y-%m-%d %H:%M")) for back in range(12)]
        if values[0] is None:
            continue
        totals[code] = {
            "rain_1h_mm": values[0],
            "rain_3h_mm": round(sum(values[:3]), 1) if all(v is not None for v in values[:3]) else None,
            "rain_12h_mm": round(sum(values), 1) if all(v is not None for v in values) else None,
            "rain_10m_mm": None,
        }
    return hour, totals


def _hourly_total(slots: dict[datetime, float], hours: int) -> float | None:
    """Sum complete hourly buckets ending at the newest observation; missing hours stay unavailable."""
    buckets: dict[datetime, tuple[datetime, float]] = {}
    for stamp, value in slots.items():
        bucket = stamp.replace(minute=0, second=0, microsecond=0)
        if bucket not in buckets or stamp > buckets[bucket][0]:
            buckets[bucket] = (stamp, value)
    if not buckets:
        return None
    latest = max(buckets)
    values = [buckets.get(latest - timedelta(hours=back), (None, None))[1] for back in range(hours)]
    return round(sum(values), 1) if all(value is not None for value in values) else None


def _live_totals() -> tuple[datetime | None, dict[str, dict[str, float | None]]]:
    nw.refresh_live()
    with _LOCK:
        for code, slots in nw._LIVE.rain_slots.items():
            mine = _RAIN_HISTORY.setdefault(code, {})
            mine.update(slots)
        hourly_history = nw._LIVE.rain_hourly_history
        latest_10m = max((max(slots) for slots in _RAIN_HISTORY.values() if slots), default=None)
        latest_hourly = max((max(slots) for slots in hourly_history.values() if slots), default=None)
        latest = max((stamp for stamp in (latest_10m, latest_hourly) if stamp is not None), default=None)
        if latest is None:
            return None, {}
        now = datetime.now().replace(microsecond=0)
        totals: dict[str, dict[str, float | None]] = {}
        for code in set(_RAIN_HISTORY) | set(hourly_history):
            slots = _RAIN_HISTORY.get(code, {})
            for old in [moment for moment in slots if (latest - moment).total_seconds() > 3 * 3600]:
                slots.pop(old)
            stamp_10m = max(slots, default=None)
            hourly_slots = hourly_history.get(code, {})
            stamp_hourly = max(hourly_slots, default=None)
            hourly_fresh = stamp_hourly is not None and -300 <= (now - stamp_hourly).total_seconds() <= 90 * 60
            ten_minute_fresh = stamp_10m is not None and -300 <= (now - stamp_10m).total_seconds() <= 30 * 60
            if not hourly_fresh and not ten_minute_fresh:
                continue  # a gauge that stopped reporting is not "dry"
            last_1h = [v for t, v in slots.items() if stamp_10m is not None and 0 <= (stamp_10m - t).total_seconds() < 3600]
            last_3h = [v for t, v in slots.items() if stamp_10m is not None and 0 <= (stamp_10m - t).total_seconds() < 3 * 3600]
            hourly_one = _hourly_total(hourly_slots, 1) if hourly_fresh else None
            hourly_three = _hourly_total(hourly_slots, 3) if hourly_fresh else None
            hourly_twelve = _hourly_total(hourly_slots, 12) if hourly_fresh else None
            totals[code] = {
                "rain_10m_mm": slots[stamp_10m] if ten_minute_fresh and stamp_10m is not None else None,
                "rain_1h_mm": round(sum(last_1h), 1) if ten_minute_fresh and len(last_1h) >= 6 else hourly_one,
                "rain_3h_mm": round(sum(last_3h), 1) if ten_minute_fresh and len(last_3h) >= 18 else hourly_three,
                "rain_12h_mm": hourly_twelve,
            }
    return latest, totals


def _pluvial_level(rain: dict[str, Any] | None) -> tuple[int, str]:
    if not rain:
        return 0, "10 km 안 강우 관측 없음"
    three, one = rain.get("rain_3h_mm"), rain.get("rain_1h_mm")
    ten, fifteen = rain.get("rain_10m_mm"), rain.get("rain_15m_mm")
    twelve = rain.get("rain_12h_mm")
    observed = [value for value in (three, one, ten, fifteen, twelve) if value is not None]
    if not observed:
        return 0, "강우 누적 관측값 없음 · 판단 보류"
    if twelve is not None and twelve >= RAIN_12H_WARNING_MM:
        return 3, f"12시간 {twelve} mm · 호우경보 기준량(180 mm) 이상"
    if three is not None and three >= RAIN_3H_WARNING_MM:
        return 3, f"3시간 {three} mm · 호우경보 기준량(90 mm) 이상"
    if twelve is not None and twelve >= RAIN_12H_ADVISORY_MM:
        return 2, f"12시간 {twelve} mm · 호우주의보 기준량(110 mm) 이상"
    if three is not None and three >= RAIN_3H_ADVISORY_MM:
        return 2, f"3시간 {three} mm · 호우주의보 기준량(60 mm) 이상"
    if (one is not None and one >= RAIN_1H_STRONG_MM) or (ten is not None and ten * 6 >= RAIN_1H_STRONG_MM * 2):
        detail = f"1시간 {one} mm" if one is not None else f"10분 {ten} mm"
        return 1, f"{detail} · 강한 비"
    if fifteen is not None and fifteen * 4 >= RAIN_1H_STRONG_MM:
        equivalent = round(fifteen * 4, 1)
        return 1, f"15분 {fifteen} mm · 시간당 환산 {equivalent} mm/h · 강한 비"
    if any(value > 0 for value in observed):
        return 0, "관측된 강우 기준 미만"
    return 0, "관측 구간 강우 0 mm · 자료가 있는 구간만 확인"


def _factor_evidence(item: dict[str, Any], driver: str, rain: dict[str, Any] | None,
                     rain_level: int, rain_reason: str, issued: dict[str, Any] | None,
                     weather_warning: dict[str, Any] | None) -> dict[str, Any]:
    """Expose each available path and keep missing vulnerability/field inputs explicitly unknown."""
    gauge = item.get("gauge") or {}
    observation = gauge.get("observation") or {}
    levels = gauge.get("levels_m") or {}
    rainfall_windows = {key: (rain or {}).get(key) for key in
                        ("rain_10m_mm", "rain_15m_mm", "rain_1h_mm", "rain_3h_mm", "rain_12h_mm")}
    available_windows = [key for key, value in rainfall_windows.items() if value is not None]
    rain_status = "UNAVAILABLE" if not rain else "UNAVAILABLE" if not available_windows else "PARTIAL" if any(
        rainfall_windows[key] is None for key in ("rain_1h_mm", "rain_3h_mm", "rain_12h_mm")
    ) else "AVAILABLE"
    stage_status = "NOT_LINKED" if not item.get("station_code") else "UNAVAILABLE" if not item.get("stage") else gauge.get("quality", "OBSERVED")
    return {
        "selected_route": driver,
        "classification_basis": item.get("driver_reason"),
        "river": {
            "status": stage_status,
            "station_code": item.get("station_code"),
            "station_name": gauge.get("name"),
            "stage": item.get("stage"),
            "stage_label": item.get("stage_label"),
            "stage_m": observation.get("water_level_m"),
            "observed_at": observation.get("time"),
            "age_min": observation.get("age_min"),
            "rise_m_per_10min": item.get("rate_m_per_10min"),
            "minutes_to_planned_flood": item.get("minutes_to_planned_flood"),
            "levels_m": levels,
            "quality": gauge.get("quality"),
            "used_for_level": driver == "river",
        },
        "rain": {
            "status": rain_status,
            "station_code": (rain or {}).get("code"),
            "station_name": (rain or {}).get("name"),
            "distance_km": (rain or {}).get("distance_km"),
            "windows_mm": rainfall_windows,
            "available_windows": available_windows,
            "candidate_level": rain_level,
            "reason": rain_reason,
            "used_for_level": driver == "pluvial",
            "threshold_interpretation": "KMA forecast-rainfall criteria compared with observed rain; retrospective/reference signal, not a facility-specific control threshold",
        },
        "official_river_alert": {
            "status": "ACTIVE" if issued else "NOT_APPLICABLE" if not item.get("station_code") else "NOT_ACTIVE_OR_HISTORY_UNAVAILABLE",
            "level": issued.get("level") if issued else None,
            "issued_at": issued.get("issued_at") if issued else None,
            "used_as_floor": bool(issued and driver == "river"),
        },
        "official_weather_warning": {
            "status": "ACTIVE" if weather_warning else "NONE_OR_NOT_MATCHED",
            "level": weather_warning.get("level") if weather_warning else None,
            "area": weather_warning.get("area") if weather_warning else None,
            "issued_at": weather_warning.get("issued_at") if weather_warning else None,
            "effective_at": weather_warning.get("effective_at") if weather_warning else None,
        },
        "vulnerability": {
            "status": "UNKNOWN_UNVERIFIED",
            "missing_or_unverified": ["facility protection grade", "surveyed lowest inlet elevation", "pump capacity/inflow", "temporary levee or construction state"],
            "stage_adjustment_applied": False,
        },
        "field_confirmation": {
            "status": "NOT_CONNECTED",
            "missing": ["onsite water depth", "pump operating state", "CCTV/gate state", "facility-specific control plan"],
            "immediate_control_assessed": False,
        },
        "rule_status": "SCREENING_ONLY_NOT_CALIBRATED_AS_A_FACILITY_CONTROL_RULE",
    }


def _case_rainfall_reference(rain: dict[str, Any] | None) -> dict[str, Any]:
    """Expose the Seoul 2022 one-hour comparison without treating it as a facility control rule."""
    amount = rain.get("rain_1h_mm") if rain else None
    return {
        "case_id": "seoul-2022-sillim",
        "window_minutes": 60,
        "threshold_mm_h": RAIN_1H_CASE_REFERENCE_MM_H,
        "observed_mm": amount,
        "crossed": None if amount is None else amount >= RAIN_1H_CASE_REFERENCE_MM_H,
        "reference_only": True,
    }


def _short_time(stamp: str, at: str | None) -> str:
    """'04:10' on the assessed day, '7.14 14:20' otherwise, so a day-old issuance does not read as today's."""
    if at and stamp[:10] == str(at)[:10]:
        return stamp[11:16]
    return f"{int(stamp[5:7])}.{int(stamp[8:10])} {stamp[11:16]}"


# ---- assessment ---------------------------------------------------------------------------------------
def facility_risk(at: str | None = None, region: str | None = None, driver: str | None = None, limit: int = 300,
                  rain_mode: str | None = None) -> dict[str, Any]:
    """Rank facilities by the linked flood driver and apply only time-valid official warning floors."""
    status = nw.facility_status(at, region, None, 2000, rain_mode)
    if rain_mode == "live":
        rain_at, totals = _live_totals()
        rain_at, totals, basis = _with_kma(rain_at, totals, "실시간 10분·시간별 강우 누적(시간별 자료는 로컬 캐시에 저장)")
    elif at or status["mode"] == "replay":
        rain_at, totals = _replay_totals(at or nw.DEFAULT_REPLAY_AT)
        basis = "저장 1시간 강우(3시간·12시간 누적 = 최근 관측 합)"
    else:
        rain_at, totals = _live_totals()
        rain_at, totals, basis = _with_kma(rain_at, totals, "실시간 10분·시간별 강우 누적(시간별 자료는 로컬 캐시에 저장)")
    # The official forecast leads the observed crossing by about an hour (docs/PLATFORM_DATA.md §3-1), so a gauge
    # under 홍수주의보·경보 lifts its river-type facilities even before the stage gets there.
    official = ff.active_at(status["at"]) if at or status["mode"] == "replay" else ff.active_now()
    if at or status["mode"] == "replay":
        warning_feed = {"available": False, "fetched_at": None, "active": [], "error": None}
        warning_mode = "replay-unavailable"
    else:
        warning_feed = kww.current()
        warning_mode = "live"
    weather_alerts = warning_feed.get("active", []) if warning_feed.get("available") else []
    codes = set(totals)
    rows = []
    for item in status["facilities"]:
        kind, reason = driver_of(item)
        if driver and kind != driver:
            continue
        active_route = kind
        near = _nearest_rain_codes(item["lon"], item["lat"], codes)
        rain = None
        if near:
            code, distance = near[0]
            gauge = _gauge(code)
            rain = {"code": code, "name": gauge.name, "distance_km": distance, "source": "KMA AWS" if code.startswith("kma:") else "HRFCO", **totals[code]}
        rain_candidate_level, rain_candidate_reason = _pluvial_level(rain)
        if kind == "river":
            level = RIVER_LEVEL.get(item.get("stage") or "", 0)
            minutes = item.get("minutes_to_planned_flood")
            why = f"{item['stage_label']}" + (f" · 계획홍수위까지 {minutes}분" if minutes is not None else "")
            if not item.get("station_code"):
                active_route = "pluvial_fallback"
                level, why = rain_candidate_level, rain_candidate_reason
                why = "하천 관측소 없음 · " + why
        else:
            level, why = rain_candidate_level, rain_candidate_reason
        case_rainfall_reference = _case_rainfall_reference(rain) if kind == "pluvial" else None
        if case_rainfall_reference and case_rainfall_reference["crossed"]:
            why += f" · 서울 2022 사례 참고 1시간 {case_rainfall_reference['observed_mm']} mm (95 mm/h)"
        issued = official.get(item.get("station_code") or "") if kind == "river" else None
        if issued:
            level = max(level, OFFICIAL_LEVEL[issued["level"]])
            forecast = (f" · 예상 {_short_time(issued['forecast_time'], status['at'])} {issued['forecast_level_m']:.2f} m"
                        if issued.get("forecast_time") and issued.get("forecast_level_m") is not None else "")
            why = f"공식 {issued['level_ko']} 중(발령 {_short_time(issued['issued_at'], status['at'])}{forecast}) · {why}"
        weather_warning = None
        if active_route in ("pluvial", "pluvial_fallback") or item["group"] == "riverside":
            weather_warning = kww.for_facility(weather_alerts, item)
            if weather_warning:
                weather_floor = OFFICIAL_LEVEL[weather_warning["level"]]
                level = max(level, weather_floor)
                timing = f"발효 {_short_time(weather_warning['effective_at'], status['at'])}" if weather_warning.get("effective_at") else "현재 발효"
                why = f"기상청 {weather_warning['level_ko']} · {weather_warning['area']} {timing} · {why}"
        rain_values_present = rain is not None and any(rain.get(key) is not None for key in
                                                       ("rain_10m_mm", "rain_15m_mm", "rain_1h_mm", "rain_3h_mm", "rain_12h_mm"))
        if active_route in ("pluvial", "pluvial_fallback"):
            complete_windows = rain is not None and all(rain.get(key) is not None for key in ("rain_1h_mm", "rain_3h_mm", "rain_12h_mm"))
            if not rain_values_present:
                assessment_status = "WARNING_ACTIVE_RAIN_DATA_MISSING" if weather_warning else "INSUFFICIENT_DATA"
            elif not complete_windows:
                assessment_status = "PARTIAL_INPUTS"
            else:
                assessment_status = "ASSESSED_REFERENCE_ONLY"
        else:
            quality = (item.get("gauge") or {}).get("quality")
            if not item.get("stage") and not issued:
                assessment_status = "INSUFFICIENT_DATA"
            elif quality in ("stale", "suspect", "missing"):
                assessment_status = "INPUT_QUALITY_REVIEW"
            else:
                assessment_status = "ASSESSED_SCREENING_ONLY"
        factor_evidence = _factor_evidence(item, active_route, rain, rain_candidate_level, rain_candidate_reason, issued, weather_warning)
        rows.append({
            "facility_id": item["facility_id"], "name": item["name"], "kind_ko": item["kind_ko"], "group": item["group"], "tier": item["tier"],
            "region": item["region"], "lon": item["lon"], "lat": item["lat"], "driver": kind, "driver_reason": reason,
            "assessment_route": active_route,
            "level": level, "level_label": LEVELS[level], "why": why,
            "assessment_status": assessment_status, "factor_evidence": factor_evidence,
            "gauge": (item.get("gauge") or {}).get("name"), "distance_km": item.get("distance_km"), "stage": item.get("stage"),
            # A gauge's minutes say nothing about an underpass that floods from local rain.
            "minutes_to_planned_flood": item.get("minutes_to_planned_flood") if kind == "river" else None,
            "rain": rain,
            "case_rainfall_reference": case_rainfall_reference,
            "official": {k: issued[k] for k in ("level", "level_ko", "issued_at", "forecast_level_m", "forecast_time", "minutes_since_issue")} if issued else None,
            "weather_warning": {k: weather_warning[k] for k in ("region_code", "province", "area", "level", "level_ko", "issued_at", "effective_at")} if weather_warning else None,
        })

    def order(row: dict[str, Any]) -> tuple:
        rain = row["rain"] or {}
        minutes = row["minutes_to_planned_flood"] if row["level"] > 0 else None  # thousands of minutes at 평상 rank nothing
        return (-row["level"], minutes if minutes is not None else 10**9, -(rain.get("rain_12h_mm") or 0), -(rain.get("rain_3h_mm") or 0), -(rain.get("rain_1h_mm") or 0),
                -(rain.get("rain_10m_mm") or 0), -(rain.get("rain_15m_mm") or 0), row["name"])

    rows.sort(key=order)
    counts = {"total": len(rows), "by_driver": {k: sum(1 for r in rows if r["driver"] == k) for k in ("river", "pluvial")},
              "by_level": {LEVELS[k]: sum(1 for r in rows if r["level"] == k) for k in LEVELS},
              "under_official": sum(1 for r in rows if r["official"]),
              "under_weather_warning": sum(1 for r in rows if r["weather_warning"]),
              "official_gauges": {"warning": sum(1 for a in official.values() if a["level"] == "warning"),
                                  "advisory": sum(1 for a in official.values() if a["level"] == "advisory")}}
    rain_rows = []
    for code, values in sorted(totals.items()):
        gauge = _gauge(code)
        if gauge is None:
            continue
        rain_rows.append({"code": code, "name": gauge.name, "region": gauge.region, "lon": gauge.lon, "lat": gauge.lat, **values})
    return {"mode": status["mode"], "at": status["at"], "observed_at": status.get("observed_at"),
            "rain_at": rain_at.isoformat() if rain_at else None, "rain_basis": basis,
            "weather_warning_feed": {"mode": warning_mode, "available": bool(warning_feed.get("available")),
                                     "fetched_at": warning_feed["fetched_at"].isoformat(timespec="minutes") if warning_feed.get("fetched_at") else None,
                                     "active_areas": len(weather_alerts), "error": warning_feed.get("error"),
                                     "source": "기상청 API Hub wrn_now_data.php"},
            "filter": {"region": region, "driver": driver}, "counts": counts, "facilities": rows[:limit], "rain_gauges": rain_rows,
            "thresholds": {"rain_3h_advisory_mm": RAIN_3H_ADVISORY_MM, "rain_3h_warning_mm": RAIN_3H_WARNING_MM,
                           "rain_12h_advisory_mm": RAIN_12H_ADVISORY_MM, "rain_12h_warning_mm": RAIN_12H_WARNING_MM,
                           "rain_1h_strong_mm": RAIN_1H_STRONG_MM,
                           "rain_15m_strong_equivalent_mm_h": RAIN_1H_STRONG_MM,
                           "rain_15m_signal_level": 1,
                           "rain_1h_case_reference_mm_h": RAIN_1H_CASE_REFERENCE_MM_H,
                           "rain_1h_case_reference_effect": "reference_only; does not change facility risk level"},
            "limitations": LIMITATIONS + status.get("limitations", [])[:2]}
