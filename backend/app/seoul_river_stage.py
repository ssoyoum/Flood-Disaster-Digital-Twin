"""Current Seoul river gauge levels and the city's published control levels."""

from __future__ import annotations

import csv
import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_FILE = REPO_ROOT / "data" / "processed" / "platform" / "seoul_river_control_levels.csv"
SOURCE_URL = "https://data.seoul.go.kr/dataList/datasetView.do?infId=OA-1167&serviceKind=1&srvType=S"
API_URL = "http://openapi.seoul.go.kr:8088/{key}/json/ListRiverStageService/1/1000/"
REFRESH_SECONDS = 300
STALE_AFTER_MINUTES = 30
SEOUL = timezone(timedelta(hours=9), "KST")

_LOCK = threading.Lock()
_CACHE: dict[str, Any] | None = None
_CACHE_AT = 0.0

_API_FIELDS = {
    "WATG_CD": "gauge_code",
    "WATG_NM": "gauge_name",
    "RVR_NM": "river",
    "GU_OFC_NM": "district",
    "EBM_HGT": "embankment_m",
    "PLAN_FLDE": "planned_flood_m",
    "RBH": "riverbed_m",
    "CNTRL_WATL": "control_level_m",
    "RLTM_RVR_WATL_CNT": "level_at_collection_m",
    "DTRSM_DATA_CLCT_TM": "collected_at",
}


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed and abs(parsed) != float("inf") else None


def _timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y%m%d%H%M%S")
        except ValueError:
            return None
    return parsed.replace(tzinfo=SEOUL) if parsed.tzinfo is None else parsed.astimezone(SEOUL)


def _normalise(row: dict[str, Any], now: datetime, mode: str) -> dict[str, Any]:
    if "WATG_CD" in row:
        row = {target: row.get(source) for source, target in _API_FIELDS.items()}

    control = _number(row.get("control_level_m"))
    level = _number(row.get("level_at_collection_m"))
    collected = _timestamp(row.get("collected_at"))
    age = max(0, int((now - collected).total_seconds() // 60)) if collected else None
    has_control = control is not None and control > 0
    if not has_control:
        control_status = "no_control_level"
    elif level is None:
        control_status = "no_reading"
    else:
        control_status = "at_or_above" if level >= control else "below"

    return {
        "gauge_code": str(row.get("gauge_code") or "").strip(),
        "gauge_name": str(row.get("gauge_name") or "").strip(),
        "river": str(row.get("river") or "").strip(),
        "district": str(row.get("district") or "").strip(),
        "embankment_m": _number(row.get("embankment_m")),
        "planned_flood_m": _number(row.get("planned_flood_m")),
        "riverbed_m": _number(row.get("riverbed_m")),
        "control_level_m": control if has_control else None,
        "level_m": level,
        "collected_at": collected.isoformat(timespec="seconds") if collected else None,
        "age_minutes": age,
        "freshness": "unknown" if age is None else "fresh" if age <= STALE_AFTER_MINUTES else "stale",
        "control_status": control_status,
        "mode": mode,
    }


def _live_rows() -> list[dict[str, Any]]:
    from .llm_planner import _load_env_file_once

    _load_env_file_once()
    key = os.environ.get("SEOUL_OPEN_API_KEY", "").strip()
    if not key:
        raise RuntimeError("missing key")

    request = urllib.request.Request(
        API_URL.format(key=key),
        headers={"Accept": "application/json", "User-Agent": "FloodOps/1.0"},
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        body = json.loads(response.read().decode("utf-8"))
    service = body.get("ListRiverStageService") if isinstance(body, dict) else None
    rows = service.get("row") if isinstance(service, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty response")
    return rows


def _snapshot_rows() -> list[dict[str, Any]]:
    if not SNAPSHOT_FILE.is_file():
        return []
    with SNAPSHOT_FILE.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _build_result(now: datetime, rows: list[dict[str, Any]], mode: str, error: str | None) -> dict[str, Any]:
    stations = [_normalise(row, now, mode) for row in rows]
    stations = [row for row in stations if row["gauge_code"]]
    stations.sort(key=lambda row: (row["river"], row["gauge_name"], row["gauge_code"]))
    controlled = [row for row in stations if row["control_level_m"] is not None]
    return {
        "available": bool(stations),
        "mode": mode,
        "fetched_at": now.isoformat(timespec="seconds"),
        "source": "서울 열린데이터광장 ListRiverStageService",
        "source_url": SOURCE_URL,
        "update_interval_minutes": 10,
        "stations_total": len(stations),
        "stations_with_control_level": len(controlled),
        "at_or_above_control": sum(row["control_status"] == "at_or_above" for row in controlled),
        "error": error,
        "stations": stations,
        "limitations": [
            "통제수위는 서울시 관측소에 공개된 기준이며 특정 출입구의 침수·폐쇄 여부나 FloodOps 경보를 뜻하지 않습니다.",
            "통제수위가 제공되는 관측소만 현재 수위와 기준을 비교합니다.",
            "수위 자료는 약 10분 간격으로 갱신되며 관측 지점과 출입구 사이의 차이는 별도 검증이 필요합니다.",
        ],
    }


def summary(force: bool = False) -> dict[str, Any]:
    """Return a five-minute cached live feed, falling back to the collected CSV."""

    global _CACHE, _CACHE_AT
    with _LOCK:
        if not force and _CACHE is not None and time.monotonic() - _CACHE_AT < REFRESH_SECONDS:
            return dict(_CACHE)

        now = datetime.now(SEOUL).replace(microsecond=0)
        try:
            result = _build_result(now, _live_rows(), "live", None)
        except Exception as exc:  # The credential is part of the URL and must never enter the response.
            if isinstance(exc, RuntimeError) and str(exc) == "missing key":
                reason = "서울 열린데이터광장 API 키가 없어 저장된 수집 자료를 표시합니다."
            else:
                reason = "서울시 실시간 자료에 연결하지 못해 저장된 수집 자료를 표시합니다."
            result = _build_result(now, _snapshot_rows(), "snapshot", reason)

        _CACHE = result
        _CACHE_AT = time.monotonic()
        return dict(result)
