"""Underpass control-decision twin (Phase 3 skeleton).

The twin's unit is a facility, not an event. For each registered underpass it reads the nearest
river gauge, classifies the current stage against the gauge's official levels, estimates how many
minutes remain before the planned flood level at the current rate of rise, and says whether a
closure review is recommended. The same rule is replayed over the 2023 Osong series as a backtest.

Observation sources:
- replay: the processed 10-minute CSV already in the repository, played at a chosen "now".
- live: the Han River Flood Control Office OpenAPI when ``HRFCO_API_KEY`` is set.

Nothing here measures depth inside the underpass. The official closure trigger is flood depth
(15 cm, lowered to 5 cm in 2026 per press reports); this twin only shows leading indicators.
"""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from .llm_planner import _load_env_file_once

REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"
WATER_LEVEL_FILE = OSONG_DIR / "osong_hrfco_water_level_10m_2023-07-14_17.csv"
RAINFALL_FILE = OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv"
HRFCO_ENDPOINT = "https://api.hrfco.go.kr/{key}/waterlevel/list/{interval}/{station}/{start}/{end}.xml"
DEFAULT_REPLAY_NOW = "2023-07-15T08:00:00"

# Gauge levels come from the HRFCO station metadata (hrfco_waterlevel_info.xml, queried 2026).
# attwl=관심, wrnwl=주의보, almwl=경보, srswl=심각, pfh=계획홍수위 (all stage heights in m above the gauge datum gdt).
FACILITIES: dict[str, dict[str, Any]] = {
    "gungpyeong2-underpass": {
        "id": "gungpyeong2-underpass",
        "name": "궁평2지하차도",
        "kind": "underpass",
        "driver": "river_stage",
        "location": [127.3376, 36.6246],
        "road": "지방도 508호선",
        "managing_agency": "충청북도도로관리사업소",
        "event_id": "osong-2023",
        "gauge": {
            "station_id": "3011665",
            "name": "청주시(미호강교)",
            "datum_el_m": 19.643,
            "levels_m": {"attention": 5.0, "advisory": 7.0, "warning": 8.0, "severe": 9.38, "planned_flood": 9.38},
            "source": "HRFCO waterlevel info (2026 조회); 계획홍수위 EL 29.023 m = gdt 19.643 + pfh 9.38",
        },
        "rain_station": {"station_id": "327", "name": "청주금천", "source": "KMA AWS hourly (2023 CSV)"},
        "control_rule": {
            "id": "river_stage_v1",
            "review_when": "stage >= planned_flood, or stage >= warning and the planned flood level is less than 60 minutes away at the current rate of rise",
            "rate_window_min": 30,
            "lead_threshold_min": 60,
            "basis": "국무조정실 감찰 결과는 계획홍수위 도달(06:40)을 통제 요건 충족 시각으로 봤다. 상승 속도 조건은 그보다 앞서 검토를 시작하게 하는 트윈의 가정이다.",
            "official_closure_trigger": "행안부 지하차도 통제 기준은 침수심(15 cm → 2026년 5 cm, 보도 기준, 원문 확보 필요). 이 트윈은 침수심을 재지 않고 선행 지표만 보여준다.",
        },
        "reference_event": {
            "official_requirement_met": "2023-07-15T06:40:00",
            "levee_failure": "2023-07-15T08:09:00",
            "underpass_inflow": "2023-07-15T08:27:00",
            "full_inundation": "2023-07-15T08:40:00",
            "source": "국무조정실 발표(06:40) · 사건 재구성 타임라인(출처 쪽수 확인 필요)",
        },
    },
}

STAGE_ORDER = ["normal", "attention", "advisory", "warning", "planned_flood"]
STAGE_KO = {"normal": "정상", "attention": "관심", "advisory": "주의보 수위", "warning": "경보 수위", "planned_flood": "계획홍수위 도달"}


# ---- observation sources ------------------------------------------------------------------------
def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace(" ", "T")[:16])


@lru_cache(maxsize=1)
def _replay_rows() -> list[dict[str, Any]]:
    if not WATER_LEVEL_FILE.exists():
        return []
    with WATER_LEVEL_FILE.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("water_level_m")]
    return sorted(({"time": _parse_ts(r["timestamp_kst"]), "station_id": r["station_id"], "water_level_m": float(r["water_level_m"])} for r in rows), key=lambda r: r["time"])


@lru_cache(maxsize=1)
def _replay_rain() -> list[dict[str, Any]]:
    if not RAINFALL_FILE.exists():
        return []
    with RAINFALL_FILE.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("rainfall_mm")]
    return sorted(({"time": _parse_ts(r["timestamp_kst"]), "station_id": r["station_id"], "rainfall_mm": float(r["rainfall_mm"])} for r in rows), key=lambda r: r["time"])


class ReplaySource:
    mode = "replay"

    def window(self, station_id: str, end: datetime, minutes: int) -> list[dict[str, Any]]:
        start = end - timedelta(minutes=minutes)
        return [r for r in _replay_rows() if r["station_id"] == station_id and start <= r["time"] <= end]

    def series(self, station_id: str) -> list[dict[str, Any]]:
        return [r for r in _replay_rows() if r["station_id"] == station_id]

    def rain_window(self, station_id: str, end: datetime, minutes: int) -> list[dict[str, Any]]:
        start = end - timedelta(minutes=minutes)
        return [r for r in _replay_rain() if r["station_id"] == station_id and start <= r["time"] <= end]


class HrfcoLiveSource:
    """10-minute water level from the HRFCO OpenAPI. Only used when a key is configured."""

    mode = "live"

    def __init__(self, key: str, timeout: float = 10.0):
        self.key = key
        self.timeout = timeout

    def window(self, station_id: str, end: datetime, minutes: int) -> list[dict[str, Any]]:
        """10-minute rows; falls back to the hourly series when the 10-minute feed is blank.

        Some Geum River gauges (e.g. 미호강교) publish blank 10-minute values outside flood operations
        while the hourly series stays populated (checked 2026-10-10).
        """
        rows = self._fetch(station_id, end, minutes, "10M")
        if rows:
            return rows
        hourly = self._fetch(station_id, end, max(minutes, 180), "1H")
        for row in hourly:
            row["interval"] = "1H"
        return hourly

    def _fetch(self, station_id: str, end: datetime, minutes: int, interval: str) -> list[dict[str, Any]]:
        start = end - timedelta(minutes=minutes)
        fmt = "%Y%m%d%H%M" if interval == "10M" else "%Y%m%d%H"
        url = HRFCO_ENDPOINT.format(key=self.key, interval=interval, station=station_id, start=start.strftime(fmt), end=end.strftime(fmt))
        response = httpx.get(url, timeout=self.timeout)
        response.raise_for_status()
        rows = []
        for block in re.findall(r"<Waterlevel>(.*?)</Waterlevel>", response.text, flags=re.S):
            fields = {k: v.strip() for k, v in re.findall(r"<(\w+)>([^<]*)</\1>", block)}
            # Missing values arrive as blank elements; skip them instead of failing the whole window.
            if fields.get("wl") and fields.get("ymdhm"):
                try:
                    stamp = fields["ymdhm"] if len(fields["ymdhm"]) == 12 else fields["ymdhm"] + "00"
                    rows.append({"time": datetime.strptime(stamp, "%Y%m%d%H%M"), "station_id": station_id, "water_level_m": float(fields["wl"]), "interval": interval})
                except ValueError:
                    continue
        return sorted(rows, key=lambda r: r["time"])

    def series(self, station_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Backtests run on the stored event series, not on the live API.")

    def rain_window(self, station_id: str, end: datetime, minutes: int) -> list[dict[str, Any]]:
        return []  # KMA API hub adapter is added once a key exists.


def twin_mode() -> dict[str, Any]:
    _load_env_file_once()
    hrfco = bool(os.environ.get("HRFCO_API_KEY"))
    kma = bool(os.environ.get("KMA_API_HUB_KEY"))
    forced = os.environ.get("FLOODOPS_TWIN_MODE", "").strip().lower()
    mode = "live" if (forced == "live" or (not forced and hrfco)) else "replay"
    return {"mode": mode, "hrfco_key_configured": hrfco, "kma_key_configured": kma, "replay_now_default": DEFAULT_REPLAY_NOW}


def get_source() -> ReplaySource | HrfcoLiveSource:
    if twin_mode()["mode"] == "live":
        return HrfcoLiveSource(os.environ["HRFCO_API_KEY"])
    return ReplaySource()


# ---- assessment --------------------------------------------------------------------------------
def classify_stage(level: float, levels: dict[str, float]) -> str:
    stage = "normal"
    for name in ("attention", "advisory", "warning", "planned_flood"):
        if level >= levels[name]:
            stage = name
    return stage


def assess(facility: dict[str, Any], window: list[dict[str, Any]], now: datetime, rain_window: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    gauge = facility["gauge"]
    levels = gauge["levels_m"]
    rule = facility["control_rule"]
    if not window:
        return {"facility_id": facility["id"], "at": now.isoformat(), "status": "NO_OBSERVATION", "stage": None, "recommendation": None}
    latest = window[-1]
    level = latest["water_level_m"]
    earlier = [r for r in window if r["time"] <= latest["time"] - timedelta(minutes=rule["rate_window_min"])]
    base = earlier[-1] if earlier else window[0]
    span_min = max(1.0, (latest["time"] - base["time"]).total_seconds() / 60)
    rate = (level - base["water_level_m"]) / span_min if latest is not base else 0.0
    stage = classify_stage(level, levels)
    pfh = levels["planned_flood"]
    if level >= pfh:
        minutes_to_pfh: float | None = 0.0
    elif rate > 0:
        minutes_to_pfh = (pfh - level) / rate
    else:
        minutes_to_pfh = None
    review = stage == "planned_flood" or (STAGE_ORDER.index(stage) >= STAGE_ORDER.index("warning") and minutes_to_pfh is not None and minutes_to_pfh <= rule["lead_threshold_min"])
    if review:
        recommendation, reason = "CLOSURE_REVIEW", ("계획홍수위에 도달했습니다." if stage == "planned_flood" else f"경보 수위 이상이고 현재 상승 속도로 계획홍수위까지 {minutes_to_pfh:.0f}분입니다.")
    elif stage in ("advisory", "warning"):
        recommendation, reason = "MONITOR", f"{STAGE_KO[stage]}입니다. 상승 속도를 감시합니다."
    else:
        recommendation, reason = "NORMAL", "주의보 수위 미만입니다."
    rain = None
    if rain_window:
        rain = {"station": facility.get("rain_station", {}).get("name"), "last_hour_mm": rain_window[-1]["rainfall_mm"], "sum_6h_mm": round(sum(r["rainfall_mm"] for r in rain_window), 1)}
    reference = facility.get("reference_event") or {}
    ref_lead = None
    if reference.get("underpass_inflow"):
        inflow = datetime.fromisoformat(reference["underpass_inflow"])
        if abs((inflow - now).total_seconds()) <= 48 * 3600:
            ref_lead = int((inflow - now).total_seconds() // 60)
    return {
        "facility_id": facility["id"],
        "at": now.isoformat(),
        "status": "OK",
        "observation": {"station_id": gauge["station_id"], "station": gauge["name"], "time": latest["time"].isoformat(), "water_level_m": level, "water_level_el_m": round(gauge["datum_el_m"] + level, 3), "age_min": int((now - latest["time"]).total_seconds() // 60), "interval": latest.get("interval", "10M")},
        "rate_m_per_10min": round(rate * 10, 3),
        "stage": stage,
        "stage_label": STAGE_KO[stage],
        "levels_m": levels,
        "margin_to_planned_flood_m": round(pfh - level, 2),
        "minutes_to_planned_flood": None if minutes_to_pfh is None else round(minutes_to_pfh),
        "recommendation": recommendation,
        "reason": reason,
        "rule": rule,
        "rainfall": rain,
        "reference_minutes_to_inflow": ref_lead,
        "limitations": [
            "침수심을 측정하지 않는다. 공식 통제 기준(침수심)은 현장 센서·담당자 판단이 우선한다.",
            "상승 속도 외삽은 최근 30분 기울기를 그대로 늘린 값이며 예보가 아니다.",
            "수위는 관측소 기준면 위 높이(m)이고 DEM 절대 수면고로 쓰지 않는다.",
        ],
    }


def facility_status(facility_id: str, at: str | None = None) -> dict[str, Any]:
    facility = FACILITIES[facility_id]
    mode = twin_mode()
    source = get_source()
    now = datetime.fromisoformat(at) if at else (datetime.now().replace(second=0, microsecond=0) if mode["mode"] == "live" else datetime.fromisoformat(DEFAULT_REPLAY_NOW))
    window = source.window(facility["gauge"]["station_id"], now, 120)
    rain = source.rain_window(facility["rain_station"]["station_id"], now, 360) if facility.get("rain_station") else []
    result = assess(facility, window, now, rain)
    result["mode"] = mode["mode"]
    result["facility"] = {k: facility[k] for k in ("id", "name", "kind", "driver", "location", "road", "managing_agency", "event_id")}
    return result


def backtest(facility_id: str) -> dict[str, Any]:
    """Replay the rule over the stored event series and report when it would have fired."""

    facility = FACILITIES[facility_id]
    source = ReplaySource()
    station = facility["gauge"]["station_id"]
    series = source.series(station)
    reference = facility["reference_event"]
    inflow = datetime.fromisoformat(reference["underpass_inflow"])
    transitions: list[dict[str, Any]] = []
    first_review: dict[str, Any] | None = None
    last_stage = None
    for row in series:
        window = [r for r in series if row["time"] - timedelta(minutes=120) <= r["time"] <= row["time"]]
        result = assess(facility, window, row["time"])
        if result["stage"] != last_stage:
            transitions.append({"time": row["time"].isoformat(), "stage": result["stage"], "water_level_m": row["water_level_m"]})
            last_stage = result["stage"]
        if first_review is None and result["recommendation"] == "CLOSURE_REVIEW":
            first_review = {"time": row["time"].isoformat(), "water_level_m": row["water_level_m"], "reason": result["reason"], "stage": result["stage"]}
    lead = None
    if first_review:
        lead = {key: int((datetime.fromisoformat(reference[key]) - datetime.fromisoformat(first_review["time"])).total_seconds() // 60) for key in ("levee_failure", "underpass_inflow", "full_inundation")}
    return {
        "facility_id": facility_id,
        "event_id": facility["event_id"],
        "rule": facility["control_rule"],
        "series": {"station_id": station, "from": series[0]["time"].isoformat() if series else None, "to": series[-1]["time"].isoformat() if series else None, "records": len(series)},
        "stage_transitions": transitions,
        "first_closure_review": first_review,
        "lead_minutes": lead,
        "reference_event": reference,
        "note": "백테스트는 저장된 2023년 10분 수위에 같은 규칙을 적용한 결과다. 06:40은 국무조정실이 통제 요건 충족 시각으로 본 시각이고, 보관된 10분 자료로는 06:50에 계획홍수위에 닿는다(DQ-009).",
    }


def list_facilities() -> list[dict[str, Any]]:
    mode = twin_mode()
    return [{**{k: f[k] for k in ("id", "name", "kind", "driver", "location", "road", "managing_agency", "event_id")}, "gauge": {"station_id": f["gauge"]["station_id"], "name": f["gauge"]["name"]}, "mode": mode["mode"]} for f in FACILITIES.values()]
