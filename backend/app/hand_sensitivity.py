"""Sensitivity of the temporary HAND envelope to a lower selection threshold.

This reselects cells from the existing Miho-connected baseline envelope. It is a
parameter sensitivity exercise, not an intervention, hydraulic, or damage model.
"""

from __future__ import annotations

import json
import math
import re
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Any

from .data import EVENT_ID
from .services import ReconstructionUnavailable


_OSONG_DIR = Path(__file__).resolve().parents[2] / "data" / "processed" / "osong"
_GRID_ID = re.compile(r"dem-(\d+)-(\d+)")
_SEED_DISTANCE_M = 250.0


@lru_cache(maxsize=1)
def _source() -> tuple[dict[int, dict[str, dict[str, Any]]], list[dict[str, Any]]]:
    timeline = json.loads((_OSONG_DIR / "osong_hand_flood_envelope_timeline.geojson").read_text(encoding="utf-8"))
    report = json.loads((_OSONG_DIR / "osong_hand_reconstruction_validation.json").read_text(encoding="utf-8"))
    by_stage: dict[int, dict[str, dict[str, Any]]] = {}
    for feature in timeline["features"]:
        if feature["geometry"]["type"] != "Polygon":
            continue
        props = feature["properties"]
        by_stage.setdefault(int(props["stage_index"]), {})[str(props["grid_id"])] = props
    return by_stage, report["stage_contexts"]


def _connected(candidates: set[str], props_by_id: dict[str, dict[str, Any]]) -> set[str]:
    """Apply the same four-neighbour Miho-side reachability rule to retained cells."""

    seeds = {grid_id for grid_id in candidates if float(props_by_id[grid_id]["distance_to_primary_river_m"]) <= _SEED_DISTANCE_M}
    reached = set(seeds)
    queue = deque(seeds)
    while queue:
        match = _GRID_ID.fullmatch(queue.popleft())
        if match is None:
            continue
        row, col = map(int, match.groups())
        for adjacent in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if min(adjacent) < 0:
                continue
            neighbour = f"dem-{adjacent[0]:02d}-{adjacent[1]:02d}"
            if neighbour in candidates and neighbour not in reached:
                reached.add(neighbour)
                queue.append(neighbour)
    return reached


def analyze_hand_threshold(event_id: str, reduction_m: float) -> dict[str, Any]:
    """Return stage cell IDs after an explicit reduction in the selection threshold."""

    if event_id != EVENT_ID:
        raise ReconstructionUnavailable(f"HAND reconstruction is not connected for {event_id}")
    if not math.isfinite(reduction_m) or not 0 <= reduction_m <= 2.5:
        raise ValueError("reduction_m must be between 0 and 2.5 metres")
    by_stage, contexts = _source()
    stages = []
    for context in contexts:
        index = int(context["stage_index"])
        props_by_id = by_stage.get(index, {})
        baseline = set(props_by_id)
        threshold = float(context["hand_threshold_m"])
        scenario_threshold = max(0.0, round(threshold - reduction_m, 2))
        candidates = {
            grid_id for grid_id, props in props_by_id.items()
            if float(props["hand_primary_m"]) <= scenario_threshold
        }
        selected = _connected(candidates, props_by_id)
        if reduction_m == 0 and selected != baseline:
            raise RuntimeError(f"HAND baseline connectivity does not reproduce stage {index}")
        removed = baseline - selected
        stages.append({
            "stage_index": index,
            "state": context["state"],
            "time": context["time"],
            "baseline_threshold_m": threshold,
            "scenario_threshold_m": scenario_threshold,
            "baseline_cell_count": len(baseline),
            "scenario_cell_count": len(selected),
            "removed_cell_count": len(removed),
            "selected_grid_ids": sorted(selected),
            "removed_grid_ids": sorted(removed),
        })
    return {
        "event_id": event_id,
        "analysis": "hand_threshold_sensitivity",
        "reduction_m": reduction_m,
        "coverage_status": "fallback",
        "coverage_note": "TEMPORARY HAND-like reconstruction, not official Flood Extent or a calibrated hydraulic model.",
        "stages": stages,
        "assumptions": [
            "The HAND selection threshold is lowered by the entered amount at each stage; observed gauge readings and event times stay fixed.",
            "Only cells in the existing Miho-connected baseline envelope are reconsidered, and retained cells must remain four-neighbour-connected to Miho-side seeds.",
        ],
        "limitations": [
            "The reduction is a user-defined sensitivity parameter, not a measured effect of a levee, barrier, or pump.",
            "Changed red cells are changes in a temporary derived envelope, not verified changes in real inundation, depth, or damage.",
            "Coarse DEM cells do not resolve narrow levees, roads, drains, or water-flow dynamics.",
        ],
    }
