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
import gzip
import json
import os
import re
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from . import facility_registry
from .llm_planner import _load_env_file_once

REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"
WATER_LEVEL_FILE = OSONG_DIR / "osong_hrfco_water_level_10m_2023-07-14_17.csv"
RAINFALL_FILE = OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv"
# Explicit research quarantines (e.g. the 2023-05-16 미호강교 step fault) shared with the hourly audit.
QUALITY_POLICY_FILE = REPO_ROOT / "data" / "manifests" / "hrfco-quality-policy.json"
HRFCO_ENDPOINT = "https://api.hrfco.go.kr/{key}/waterlevel/list/{interval}/{station}/{start}/{end}.xml"
DEFAULT_REPLAY_NOW = "2023-07-15T08:00:00"

# Operational facilities live in data/facilities/registry.json (hand-kept; candidates are generated into
# candidates.json and never reach this dict). Gauge levels there come from the HRFCO station metadata
# (hrfco_waterlevel_info.xml, queried 2026): attwl=관심, wrnwl=주의보, almwl=경보, srswl=심각, pfh=계획홍수위
# (all stage heights in m above the gauge datum gdt). Each facility registers its own gauge's levels;
# thresholds are never copied between facilities.
FACILITIES: dict[str, dict[str, Any]] = facility_registry.operational()

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
    floor = rule.get("stage_floor", "warning")
    review = stage == "planned_flood" or (STAGE_ORDER.index(stage) >= STAGE_ORDER.index(floor) and minutes_to_pfh is not None and minutes_to_pfh <= rule["lead_threshold_min"])
    if review:
        recommendation, reason = "CLOSURE_REVIEW", ("계획홍수위에 도달했습니다." if stage == "planned_flood" else f"{STAGE_KO[floor]} 이상이고 현재 상승 속도로 계획홍수위까지 {minutes_to_pfh:.0f}분입니다.")
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


def backtest(facility_id: str, include_points: bool = False) -> dict[str, Any]:
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
    result = {
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
    if include_points:
        # The hydrograph the rule read, so a screen can draw the thresholds it crossed instead of only the lead.
        # Opt-in: the agent tool shares this function and should not carry 400+ rows into the model.
        result["points"] = [[row["time"].isoformat(timespec="minutes"), row["water_level_m"]] for row in series]
    return result


# ---- closure-criteria review -------------------------------------------------------------------
CRITERIA_FLOORS = ("advisory", "warning")
CRITERIA_LEADS = (0, 30, 60, 90, 120, 180)
CRITERIA_MAX_LEAD = 360
EPISODE_GAP = timedelta(hours=6)
REFERENCE_WINDOW = timedelta(hours=24)
REFERENCE_KEYS = ("official_requirement_met", "levee_failure", "underpass_inflow", "full_inundation")
HISTORY_STEP = timedelta(minutes=10)
# 2.5x the largest 10-minute rise on 2023-07-15 (0.12 m). Flagged for review only, never removed,
# like the hourly policy's jump review (hrfco-quality-policy.json).
HISTORY_STEP_REVIEW_M = 0.3
ASSESS_WINDOW = timedelta(minutes=120)


@lru_cache(maxsize=4)
def _history_series(filename: str) -> tuple[tuple[datetime, float], ...]:
    path = OSONG_DIR / filename
    if not path.exists():
        return ()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return tuple(sorted((_parse_ts(r["timestamp_kst"]), float(r["wl"])) for r in csv.DictReader(handle) if r.get("wl")))


def _review_flags(series: tuple[tuple[datetime, float], ...], levels: dict[str, float], stage_floor: str, lead_threshold_min: int, rate_window_min: int) -> list[bool]:
    """``assess`` applied at every row of a long series: same 120-minute window, base row and rule."""

    pfh = levels["planned_flood"]
    floor_level = levels[stage_floor]
    window = ASSESS_WINDOW
    rate_delta = timedelta(minutes=rate_window_min)
    flags: list[bool] = []
    lo = 0
    cand = -1  # last row at or before t - rate_window; only moves forward
    for i, (t, level) in enumerate(series):
        while series[lo][0] < t - window:
            lo += 1
        while cand + 1 <= i and series[cand + 1][0] <= t - rate_delta:
            cand += 1
        base = cand if cand >= lo else lo
        if base == i:
            rate = 0.0
        else:
            span = max(1.0, (t - series[base][0]).total_seconds() / 60)
            rate = (level - series[base][1]) / span
        flags.append(level >= pfh or (level >= floor_level and rate > 0 and (pfh - level) / rate <= lead_threshold_min))
    return flags


@lru_cache(maxsize=1)
def _quality_policy() -> dict[str, Any]:
    if not QUALITY_POLICY_FILE.exists():
        return {}
    return json.loads(QUALITY_POLICY_FILE.read_text(encoding="utf-8"))


def _quarantines(station_id: str) -> list[dict[str, Any]]:
    return [q for q in _quality_policy().get("quarantines", []) if q.get("station_id") == station_id]


def _in_quarantine(t: datetime, quarantines: list[dict[str, Any]]) -> bool:
    return any(datetime.fromisoformat(q["start"]) <= t <= datetime.fromisoformat(q["end"]) for q in quarantines)


@lru_cache(maxsize=4)
def _review_series(facility_id: str) -> tuple[tuple[datetime, float], ...]:
    """The stored history without readings inside an explicit quarantine; those never drive a review."""

    facility = FACILITIES[facility_id]
    quarantines = _quarantines(facility["gauge"]["station_id"])
    return tuple(row for row in _history_series(facility["history_series"]) if not _in_quarantine(row[0], quarantines))


@lru_cache(maxsize=4)
def _history_quality(facility_id: str) -> dict[str, Any]:
    facility = FACILITIES[facility_id]
    series = _history_series(facility["history_series"])
    quarantines = _quarantines(facility["gauge"]["station_id"])
    quality = _series_quality(series)
    for step in quality["step_reviews"]:
        step["quarantined"] = _in_quarantine(datetime.fromisoformat(step["time"]), quarantines)
    quality["policy_found"] = bool(_quality_policy())
    quality["quarantines"] = [{
        "id": q["id"], "start": q["start"], "end": q["end"], "review_status": q.get("review_status"),
        "readings_excluded": sum(1 for t, _ in series if _in_quarantine(t, [q])),
    } for q in quarantines]
    return quality


def _series_quality(series: tuple[tuple[datetime, float], ...]) -> dict[str, Any]:
    """Missing 10-minute slots and steps of at least HISTORY_STEP_REVIEW_M between consecutive readings."""

    gaps: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    for (t0, w0), (t1, w1) in zip(series, series[1:]):
        missing = int((t1 - t0) / HISTORY_STEP) - 1
        if missing > 0:
            gaps.append({"after": t0.isoformat(), "before": t1.isoformat(), "missing_slots": missing})
        elif abs(w1 - w0) >= HISTORY_STEP_REVIEW_M:
            steps.append({"time": t1.isoformat(), "change_m": round(w1 - w0, 2), "water_level_m": w1})
    expected = int((series[-1][0] - series[0][0]) / HISTORY_STEP) + 1 if series else 0
    return {
        "step_review_threshold_m": HISTORY_STEP_REVIEW_M,
        "expected_slots": expected,
        "present_slots": len(series),
        "missing_slots": sum(g["missing_slots"] for g in gaps),
        "gaps": gaps,
        "step_reviews": steps,
    }


def _episode_quality(episode: dict[str, Any], quality: dict[str, Any]) -> dict[str, int]:
    """Flags inside the readings that drove an episode: from one assess window before its start to its end."""

    lo = datetime.fromisoformat(episode["start"]) - ASSESS_WINDOW
    hi = datetime.fromisoformat(episode["end"])
    steps = sum(1 for s in quality["step_reviews"] if lo <= datetime.fromisoformat(s["time"]) <= hi)
    missing = sum(g["missing_slots"] for g in quality["gaps"] if datetime.fromisoformat(g["after"]) < hi and datetime.fromisoformat(g["before"]) > lo)
    return {"step_reviews": steps, "missing_slots": missing}


def _review_episodes(series: tuple[tuple[datetime, float], ...], flags: list[bool], levels: dict[str, float], interval_min: int = 10) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for (t, level), flag in zip(series, flags):
        if not flag:
            continue
        if current is not None and t - current["end"] <= EPISODE_GAP:
            current["end"] = t
            current["rows"] += 1
            current["peak"] = max(current["peak"], level)
        else:
            current = {"start": t, "end": t, "rows": 1, "peak": level}
            episodes.append(current)
    return [{
        "start": e["start"].isoformat(), "end": e["end"].isoformat(), "review_minutes": e["rows"] * interval_min,
        "peak_water_level_m": e["peak"], "peak_stage": classify_stage(e["peak"], levels),
    } for e in episodes]


@lru_cache(maxsize=64)
def _criteria_result(facility_id: str, stage_floor: str, lead_threshold_min: int, rate_window_min: int) -> dict[str, Any]:
    facility = FACILITIES[facility_id]
    series = _review_series(facility_id)
    levels = facility["gauge"]["levels_m"]
    reference = facility["reference_event"]
    inflow = datetime.fromisoformat(reference["underpass_inflow"])
    flags = _review_flags(series, levels, stage_floor, lead_threshold_min, rate_window_min)
    first = next(((t, wl) for (t, wl), flag in zip(series, flags) if flag and inflow - REFERENCE_WINDOW <= t <= inflow), None)
    episodes = _review_episodes(series, flags, levels)
    quality = _history_quality(facility_id)
    for episode in episodes:
        start = datetime.fromisoformat(episode["start"])
        episode["reference_event"] = inflow - REFERENCE_WINDOW <= start <= inflow
        episode["quality"] = _episode_quality(episode, quality)
        episode["quality_review_required"] = any(episode["quality"].values())
    others = [e for e in episodes if not e["reference_event"]]
    by_year: dict[str, dict[str, Any]] = {}
    for t, wl in series:
        year = by_year.setdefault(str(t.year), {"year": t.year, "rows": 0, "max_water_level_m": wl, "episodes": 0, "review_minutes": 0, "reference_event": False})
        year["rows"] += 1
        year["max_water_level_m"] = max(year["max_water_level_m"], wl)
    for episode in episodes:
        year = by_year[episode["start"][:4]]
        if episode["reference_event"]:
            year["reference_event"] = True
        else:
            year["episodes"] += 1
            year["review_minutes"] += episode["review_minutes"]
    return {
        "first_review": {"time": first[0].isoformat(), "water_level_m": first[1]} if first else None,
        "lead_minutes": {key: int((datetime.fromisoformat(reference[key]) - first[0]).total_seconds() // 60) for key in REFERENCE_KEYS} if first else None,
        "other_episode_count": len(others),
        "other_review_minutes": sum(e["review_minutes"] for e in others),
        "episodes": episodes,
        "by_year": [by_year[key] for key in sorted(by_year)],
    }


def criteria_review(facility_id: str, stage_floor: str | None = None, lead_threshold_min: int | None = None) -> dict[str, Any]:
    """Replay a closure-review rule over every flood season on record and show its cost and lead.

    The 2023 event gives the lead time; the other seasons show how often the same rule would have asked
    for a closure review without a recorded underpass flood (not verified as false alarms).
    """

    facility = FACILITIES[facility_id]
    if not facility.get("history_series") or not _history_series(facility["history_series"]):
        raise LookupError(f"No stored history for {facility_id}")
    rule = facility["control_rule"]
    floor = stage_floor or rule.get("stage_floor", "warning")
    lead = rule["lead_threshold_min"] if lead_threshold_min is None else lead_threshold_min
    if floor not in CRITERIA_FLOORS:
        raise ValueError(f"stage_floor must be one of {CRITERIA_FLOORS}")
    if not 0 <= lead <= CRITERIA_MAX_LEAD:
        raise ValueError(f"lead_threshold_min must be between 0 and {CRITERIA_MAX_LEAD}")
    rate_window = rule["rate_window_min"]
    series = _review_series(facility_id)
    result = _criteria_result(facility_id, floor, lead, rate_window)
    sweep = []
    for sweep_floor in CRITERIA_FLOORS:
        for sweep_lead in CRITERIA_LEADS:
            row = _criteria_result(facility_id, sweep_floor, sweep_lead, rate_window)
            sweep.append({
                "stage_floor": sweep_floor, "lead_threshold_min": sweep_lead,
                "first_review_time": row["first_review"]["time"] if row["first_review"] else None,
                "lead_to_inflow_min": row["lead_minutes"]["underpass_inflow"] if row["lead_minutes"] else None,
                "other_episode_count": row["other_episode_count"], "other_review_minutes": row["other_review_minutes"],
            })
    quality = _history_quality(facility_id)
    months = {t.month for t, _ in series}
    season = "매년 6~9월" if months <= {6, 7, 8, 9} else "연중(1~12월)"
    flagged = sum(1 for e in result["episodes"] if e["quality_review_required"])
    return {
        "facility_id": facility_id,
        "station": {"station_id": facility["gauge"]["station_id"], "name": facility["gauge"]["name"], "levels_m": facility["gauge"]["levels_m"]},
        "params": {"stage_floor": floor, "stage_floor_label": STAGE_KO[floor], "lead_threshold_min": lead, "rate_window_min": rate_window},
        "current_rule": {"id": rule["id"], "stage_floor": rule.get("stage_floor", "warning"), "lead_threshold_min": rule["lead_threshold_min"]},
        "is_current_rule": floor == rule.get("stage_floor", "warning") and lead == rule["lead_threshold_min"],
        "reference_event": facility["reference_event"],
        **result,
        "sweep": sweep,
        "coverage": {"from": series[0][0].isoformat(), "to": series[-1][0].isoformat(), "rows": len(series), "interval": "10M", "season": season, "years": sorted({t.year for t, _ in series})},
        "quality": {
            "step_review_threshold_m": quality["step_review_threshold_m"],
            "expected_slots": quality["expected_slots"], "present_slots": quality["present_slots"], "missing_slots": quality["missing_slots"],
            "gap_count": len(quality["gaps"]), "gaps": quality["gaps"][:20],
            "step_review_count": len(quality["step_reviews"]), "step_reviews": quality["step_reviews"][:50],
            "quarantines": quality["quarantines"], "policy_found": quality["policy_found"],
            "episodes_with_flags": flagged,
        },
        "limitations": [
            f"{'홍수기(6~9월)' if season == '매년 6~9월' else '연중'} 10분 수위를 쓴다. 품질 정책에 연구 격리로 등록된 구간(미호강교 2023-05-16 01:00~12:00 계단 변화 등)만 규칙에서 빼고, 빠진 10분 칸과 10분 사이 {HISTORY_STEP_REVIEW_M} m 이상 변화는 지우지 않고 표시만 한다. 권고 구간 판단에 쓰인 수위에 표시가 있으면 그 구간에 '자료 확인 필요'를 붙인다.",
            "2023년 사건 밖의 권고 구간은 '실제 침수 기록 없이 통제를 검토했을 구간'의 후보다. 그 시기 지하차도 침수·통제 기록을 확인하지 않았으므로 오경보로 단정하지 않는다.",
            "권고가 6시간 넘게 끊기면 다른 구간으로 센다. 계획홍수위 도달은 기준과 관계없이 항상 권고한다.",
            "규칙은 미호강교 수위만 본다. 내수 침수와 강우의 직접 영향은 반영하지 않는다.",
            "통제 결정은 담당자 판단과 현장 기준(침수심)이 우선한다.",
        ],
    }


def list_facilities() -> list[dict[str, Any]]:
    mode = twin_mode()
    return [{**{k: f[k] for k in ("id", "name", "kind", "driver", "location", "road", "managing_agency", "event_id")}, "gauge": {"station_id": f["gauge"]["station_id"], "name": f["gauge"]["name"]}, "mode": mode["mode"], "status": f["status"], "gates": f["gates"]} for f in FACILITIES.values()]
