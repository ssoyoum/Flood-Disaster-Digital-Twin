"""6-hour maximum water-level rise forecast for a registered facility (research card).

The model is the LightGBM regressor retrained on real HRFCO stations by
``data/scripts/train_rise_model.py`` (input contract from water-level-rise/baseline.py: the level now and
1/3/6/12/24 h ago, surface rain totals over 1/6/24 h, derived changes). It is applied to the facility
gauge's exact-lag inputs from ``water_level_bridge.water_inputs`` and the facility rain window.

This output is shown beside the control recommendation and never feeds it: ``assess()`` in twin.py
does not read it, and every response carries ``control_decision_usable: False``.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "data" / "models"
MODEL_FILE = MODEL_DIR / "rise_lgbm_1h.txt"
STATS_FILE = MODEL_DIR / "rise_station_stats.json"
CARD_FILE = MODEL_DIR / "rise_model_card.json"
HORIZON_H = 6
LAGS = (1, 3, 6, 12, 24)
WATER = ["wl_t"] + [f"wl_t_minus_{h}h" for h in LAGS]
RAIN_WINDOWS_H = (1, 6, 24)


@lru_cache(maxsize=1)
def load_model() -> tuple[Any, dict[str, Any], dict[str, Any]] | None:
    """(booster, station stats, model card) or None when the model files or lightgbm are absent."""
    if not (MODEL_FILE.exists() and STATS_FILE.exists()):
        return None
    try:
        import lightgbm as lgb
    except ImportError:
        return None
    booster = lgb.Booster(model_str=MODEL_FILE.read_text(encoding="utf-8"))
    stats = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    card = json.loads(CARD_FILE.read_text(encoding="utf-8")) if CARD_FILE.exists() else {}
    return booster, stats, card


def rain_totals(rain_rows: list[dict[str, Any]], anchor: datetime) -> dict[str, float | None]:
    """Sums of hourly rain (mm) over the last 1/6/24 h ending at the observation anchor.

    A window with fewer hourly rows than hours is reported as None rather than as a smaller total.
    """
    out: dict[str, float | None] = {}
    for hours in RAIN_WINDOWS_H:
        rows = [r for r in rain_rows if anchor - timedelta(hours=hours) < r["time"] <= anchor and r.get("rainfall_mm") is not None]
        out[f"sfc_rain_{hours}h"] = round(sum(float(r["rainfall_mm"]) for r in rows), 1) if len(rows) >= hours else None
    return out


def feature_vector(features: dict[str, float | None], rain: dict[str, float | None], station_id: str, stats: dict[str, Any]) -> dict[str, float]:
    """Same derivations as train_rise_model.make_features; missing rain stays NaN (LightGBM handles it)."""
    if any(features.get(name) is None for name in WATER):
        raise ValueError("every exact-lag water level is required")
    x: dict[str, float] = {name: float(features[name]) for name in WATER}
    for hours in RAIN_WINDOWS_H:
        value = rain.get(f"sfc_rain_{hours}h")
        x[f"sfc_rain_{hours}h"] = math.nan if value is None else float(value)
    for h in LAGS:
        x[f"wl_change_{h}h"] = x["wl_t"] - x[f"wl_t_minus_{h}h"]
    x["wl_acceleration_3h"] = x["wl_change_1h"] - x["wl_change_3h"] / 3
    x["wl_acceleration_6h"] = x["wl_change_3h"] / 3 - x["wl_change_6h"] / 6
    levels = [x[name] for name in WATER]
    x["wl_observed_range_24h"] = max(levels) - min(levels)
    x["sfc_rain_previous_1_to_6h"] = x["sfc_rain_6h"] - x["sfc_rain_1h"]
    x["sfc_rain_previous_6_to_24h"] = x["sfc_rain_24h"] - x["sfc_rain_6h"]
    x["sfc_rain_recent_share"] = x["sfc_rain_1h"] / (abs(x["sfc_rain_6h"]) + 1.0)
    median = stats["wl_median"].get(station_id, stats.get("wl_fallback"))
    x["wl_above_station_median"] = x["wl_t"] - float(median) if median is not None else math.nan
    x["station_rise_std"] = float(stats["rise_std"].get(station_id, math.nan))
    x["station_rise_q99"] = float(stats["rise_q99"].get(station_id, math.nan))
    return x


def predict_rise(booster: Any, x: dict[str, float]) -> float:
    import numpy as np

    names = booster.feature_name()
    missing = [n for n in names if n not in x]
    if missing:
        raise ValueError(f"model expects features not built here: {missing}")
    return float(booster.predict(np.array([[x[n] for n in names]], dtype=float))[0])


def model_summary(card: dict[str, Any]) -> dict[str, Any]:
    cv = card.get("cv") or {}
    hold = card.get("holdout") or {}
    osong = card.get("osong_2023_07_15") or {}
    pfh_skill = ((hold.get("threshold_skill") or {}).get("pfh") or {})
    return {
        "trained_at": card.get("trained_at"),
        "stations": card.get("stations"),
        "train_rows": card.get("train_rows"),
        "rows_with_rain": card.get("rows_with_rain"),
        "cv_oof_rmse_m": cv.get("oof_rmse_m"),
        "cv_oof_rmse_target_gt_1m": cv.get("oof_rmse_target_gt_1m"),
        "cv_linear_rmse_m": cv.get("baseline_linear_rmse_m"),
        "cv_no_change_rmse_m": cv.get("baseline_no_change_rmse_m"),
        "holdout_month": card.get("holdout_month"),
        "holdout_pfh_skill": {k: pfh_skill.get(k) for k in ("hours_reaching_within_6h", "model", "linear")} if pfh_skill else None,
        "osong_planned_flood_lead_min": (osong.get("planned_flood") or {}).get("lead_min_model"),
        "osong_planned_flood_lead_min_linear": (osong.get("planned_flood") or {}).get("lead_min_linear"),
        "osong_window_rmse_m": osong.get("rmse_m"),
        "contract": card.get("contract"),
        "lightgbm": card.get("lightgbm"),
    }


def forecast(facility_id: str, at: str | None = None) -> dict[str, Any]:
    from . import twin
    from .water_level_bridge import parse_time, water_inputs

    facility = twin.FACILITIES[facility_id]
    gauge = facility["gauge"]
    station_id = gauge["station_id"]
    mode = twin.twin_mode()
    source = twin.get_source()
    now = parse_time(at) if at else (datetime.now().replace(second=0, microsecond=0) if mode["mode"] == "live" else parse_time(twin.DEFAULT_REPLAY_NOW))
    rows = source.window(station_id, now, 26 * 60)
    inputs = water_inputs(rows, now, station_id)
    anchor = datetime.fromisoformat(inputs["as_of"]) if inputs["as_of"] else None
    rain_rows = source.rain_window(facility["rain_station"]["station_id"], now, 25 * 60) if facility.get("rain_station") and anchor else []
    rain = rain_totals(rain_rows, anchor) if anchor else {f"sfc_rain_{h}h": None for h in RAIN_WINDOWS_H}
    base: dict[str, Any] = {
        "facility_id": facility_id, "station_id": station_id, "at": now.isoformat(), "mode": source.mode, "kind": "RESEARCH",
        "control_decision_usable": False, "horizon_hours": HORIZON_H,
        "as_of": inputs["as_of"], "observation_quality": inputs["observation_quality"], "observation_age_min": inputs["observation_age_min"], "interval": inputs["interval"],
        "inputs": {"water": inputs["features"], "rain": {**rain, "station": (facility.get("rain_station") or {}).get("name")}},
        "limitations": [
            "6시간 안의 최대 상승량(m)을 예측하며 도달 시각·지하차도 침수심은 예측하지 않는다.",
            "학습은 홍수통제소 실명 관측소의 1시간 자료이고, 강우 입력은 가장 가까운 강우 관측소(실시간은 없으면 결측) 값이다.",
            "통제 권고는 이 예측과 무관하게 수위 규칙만으로 계산한다. 이 카드는 참고 자료다.",
        ],
    }
    model = load_model()
    if model is None:
        return {**base, "prediction_available": False, "reason": "MODEL_NOT_AVAILABLE", "model": None}
    booster, stats, card = model
    base["model"] = model_summary(card)
    missing = [name for name in WATER if inputs["features"].get(name) is None]
    if missing:
        return {**base, "prediction_available": False, "reason": "MISSING_EXACT_LAGS", "missing_inputs": missing}
    if inputs["observation_quality"] != "fresh":
        return {**base, "prediction_available": False, "reason": "OBSERVATION_NOT_FRESH"}
    x = feature_vector(inputs["features"], rain, station_id, stats)
    rise = predict_rise(booster, x)
    level = float(inputs["features"]["wl_t"])
    forecast_level = level + rise
    levels = gauge["levels_m"]
    stage = twin.classify_stage(forecast_level, levels)
    linear = max(0.0, x["wl_change_1h"]) * HORIZON_H
    return {
        **base,
        "prediction_available": True,
        "maxrise_6h_m": round(rise, 2),
        "forecast_level_m": round(forecast_level, 2),
        "forecast_level_el_m": round(gauge["datum_el_m"] + forecast_level, 2),
        "forecast_stage": stage,
        "forecast_stage_label": twin.STAGE_KO[stage],
        "reaches_within_6h": {name: forecast_level >= levels[name] for name in ("advisory", "warning", "planned_flood")},
        "margin_after_rise_m": round(levels["planned_flood"] - forecast_level, 2),
        "linear_6h_m": round(linear, 2),
        "station_in_training": station_id in stats["wl_median"],
    }
