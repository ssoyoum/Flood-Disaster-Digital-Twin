"""Bridge real observations to the water-level-rise input contract; no unvalidated inference."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import math
from pathlib import Path

KST = timezone(timedelta(hours=9))
MANIFEST = Path(__file__).resolve().parents[2] / "data/manifests/water-level-research.json"
LAGS = (0, 1, 3, 6, 12, 24)


@lru_cache(maxsize=1)
def research_contract():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def parse_time(value: str) -> datetime:
    if "T" not in value:
        raise ValueError("Use an ISO date-time for the observation window")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.astimezone(KST).replace(tzinfo=None) if result.tzinfo is not None else result


def water_inputs(rows, now: datetime, station_id: str):
    """Only past, finite readings at exact lag times; no filling gaps with future values."""
    by_time = {}
    for row in rows:
        if str(row["station_id"]) != station_id or row["time"] > now:
            continue
        value = float(row["water_level_m"])
        if not math.isfinite(value):
            continue
        previous = by_time.get(row["time"])
        if previous and previous["water_level_m"] != value:
            raise ValueError("Conflicting observations at the same timestamp")
        by_time[row["time"]] = {**row, "water_level_m": value}
    anchor = max(by_time) if by_time else None
    latest = by_time.get(anchor) if anchor else None
    interval = latest.get("interval", "10M") if latest else None
    max_age = 90 if interval == "1H" else 20
    age = int((now - anchor).total_seconds() // 60) if anchor else None
    quality = "missing" if anchor is None else "stale" if age > max_age else "fresh"
    features, history = {}, []
    for lag in LAGS:
        name = "wl_t" if lag == 0 else f"wl_t_minus_{lag}h"
        target = anchor - timedelta(hours=lag) if anchor else None
        sample = by_time.get(target)
        value = sample["water_level_m"] if sample else None
        features[name] = value
        history.append({"hours_ago": lag, "time": target.isoformat() if target else None,
                        "water_level_m": value, "status": "AVAILABLE" if sample else "MISSING_EXACT_LAG"})
    derived = {}
    if features["wl_t"] is not None:
        for lag in LAGS[1:]:
            value = features[f"wl_t_minus_{lag}h"]
            if value is not None:
                derived[f"wl_change_{lag}h"] = round(features["wl_t"] - value, 6)
        if "wl_change_1h" in derived and "wl_change_3h" in derived:
            derived["wl_acceleration_3h"] = round(derived["wl_change_1h"] - derived["wl_change_3h"] / 3, 6)
        if "wl_change_3h" in derived and "wl_change_6h" in derived:
            derived["wl_acceleration_6h"] = round(derived["wl_change_3h"] / 3 - derived["wl_change_6h"] / 6, 6)
        if all(value is not None for value in features.values()):
            derived["wl_observed_range_24h"] = round(max(features.values()) - min(features.values()), 6)
    return {"as_of": anchor.isoformat() if anchor else None, "observation_quality": quality,
            "observation_age_min": age, "interval": interval, "freshness_policy_max_age_min": max_age,
            "features": features, "derived_features": derived, "history": history}


def readiness(facility_id: str, at: str | None = None):
    from . import twin
    facility = twin.FACILITIES[facility_id]
    contract = research_contract()
    now = parse_time(at) if at else (datetime.now(KST).replace(tzinfo=None, second=0, microsecond=0)
                                    if twin.twin_mode()["mode"] == "live" else parse_time(twin.DEFAULT_REPLAY_NOW))
    source = twin.ReplaySource() if at else twin.get_source()
    station_id = facility["gauge"]["station_id"]
    # Includes the 24-hour lag. A source failure never substitutes the event replay.
    try:
        rows = source.window(station_id, now, 26 * 60)
    except Exception as exc:
        raise RuntimeError("Water-level observation source unavailable") from exc
    inputs = water_inputs(rows, now, station_id)
    available = [name for name, value in inputs["features"].items() if value is not None]
    required = contract["required_features"]
    blockers = ["ANONYMOUS_STATION_NOT_MAPPED", "REAL_FACILITY_VALIDATION_REQUIRED"]
    if set(required) - set(available):
        blockers.append("MISSING_MODEL_INPUTS")
    if inputs["observation_quality"] != "fresh":
        blockers.append("OBSERVATION_NOT_FRESH")
    return {
        "facility_id": facility_id, "station_id": station_id, "at": now.isoformat(), "mode": source.mode,
        "status": "RESEARCH_ONLY", "prediction_available": False, "prediction_maxrise_6h_m": None,
        "control_decision_usable": False, **inputs,
        "available_input_count": len(available), "required_input_count": len(required),
        "missing_features": [name for name in required if name not in available], "blockers": blockers,
        "research": {key: contract[key] for key in ("project", "horizon_hours", "target", "target_unit", "evaluation", "models")},
        "limitations": [*contract["limits"], "표시한 수위 이력은 실제 관측소 기준면의 m 값이다. 대회 자료의 혼재 기준면과 동일하다고 가정하지 않는다.",
                        "강우·레이더·유역 입력을 0으로 채우거나 가까운 강우계 값을 동일한 격자 변수로 대체하지 않는다.",
                        "시각별 예측 곡선이 없으므로 6시간 최대 상승량으로 계획홍수위 도달 분을 계산하지 않는다."],
    }
