"""Synthetic heavy-rain scenarios for testing the watch board when it is not raining.

A preset is one storm cell: rain falls off from its centre as exp(-(d/R)^2). Rain gauges get that rain, and a
river gauge's stage is lifted from the 3-hour total at its location. Nothing here is a forecast or a hydrological
model; it only exercises the board's stages, filters and ordering.
"""

from __future__ import annotations

import math
from typing import Any

PRESETS: dict[str, dict[str, Any]] = {
    "central": {"label": "중부 집중호우(서울·경기)", "center": (126.98, 37.45), "radius_km": 45.0, "peak_1h_mm": 70.0},
    "chungcheong": {"label": "충청 국지성 호우(청주·대전)", "center": (127.40, 36.55), "radius_km": 35.0, "peak_1h_mm": 65.0},
    "south": {"label": "남부 장마전선(광주~부산)", "center": (127.90, 35.15), "radius_km": 70.0, "peak_1h_mm": 50.0},
}

# Ratios from a peak hour to the other windows of the same storm.
_WINDOW_RATIO = {"rain_10m_mm": 1 / 5, "rain_15m_mm": 1 / 3.6, "rain_1h_mm": 1.0, "rain_3h_mm": 2.4, "rain_12h_mm": 4.5}
# 3-hour rain at a river gauge -> the stage it is pushed to (only ever raised, never lowered).
_STAGE_FROM_3H = (("planned_flood", 150.0), ("warning", 110.0), ("advisory", 70.0), ("attention", 35.0))
_STAGE_ORDER = ("unrated", "normal", "attention", "advisory", "warning", "planned_flood")
STAGE_KO = {"attention": "관심", "advisory": "주의보", "warning": "경보", "planned_flood": "계획홍수위"}

LIMITATION = "가상 강우 테스트입니다. 실제 관측·특보가 아니며, 강우는 한 개의 폭우 세포를 가정해 거리로만 줄였고 하천 단계는 그 강우로 끌어올린 값입니다."


def _km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    dx = (lon2 - lon1) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110.57
    return math.hypot(dx, dy)


def rain_at(preset: dict[str, Any], lon: float, lat: float) -> dict[str, float]:
    distance = _km(lon, lat, *preset["center"])
    hour = preset["peak_1h_mm"] * math.exp(-((distance / preset["radius_km"]) ** 2))
    return {key: round(hour * ratio, 1) for key, ratio in _WINDOW_RATIO.items()}


def lifted_stage(current: str | None, rain_3h_mm: float) -> str | None:
    target = next((stage for stage, floor in _STAGE_FROM_3H if rain_3h_mm >= floor), None)
    if target is None:
        return current
    if current in _STAGE_ORDER and _STAGE_ORDER.index(current) >= _STAGE_ORDER.index(target):
        return current
    return target


def describe(key: str) -> dict[str, Any]:
    preset = PRESETS[key]
    return {"id": key, "label": preset["label"], "center": list(preset["center"]), "radius_km": preset["radius_km"],
            "peak_1h_mm": preset["peak_1h_mm"], "note": LIMITATION}
