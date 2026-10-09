"""Create HAND-like stage envelopes for the Seoul, Pohang and Andong-Uiseong cases.

This mirrors the Osong reconstruction: a Copernicus DEM grid, height above the nearest
primary-river cell, a per-stage threshold, and a 4-neighbour flood fill from river-side
seed cells. What differs is the stage driver, because these cases have no river gauge
series:

- pohang-2022: no observation drives the stages. The threshold rises in the reported order
  of events and its peak is calibrated so that the reported inundated site (인덕동 일대) is
  reached. Everything about depth is an assumption and is labelled as such.
- andong-uiseong-2026: the reported Micheon stage (3.5 m at the 23:40 warning, warning level
  4.7 m expected at 00:30) orders the rise and fall; the peak is calibrated to the reported
  inundated temporary-housing villages (귀미1리, 구계리).

- seoul-2022: the band follows the 신림P 60-minute rainfall (running maximum over the event peak)
  on the same rule, drawn on top of the official flood traces. A DSM-based envelope was tested
  against the traces on 2026-10-10: 14-16% of it lay on traces at every threshold, the same share
  as the corridor as a whole, so it is a replay visual, not evidence (DQ-012).

All three use the same rule as Andong: the valley floor is HAND 0 almost everywhere, so the
stage fraction mainly widens the band around the river lines (distance = fraction^2 x 2 km).

None of this is an official flood extent, a hydraulic model, or a depth estimate.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import tifffile
from pyproj import Transformer
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.seoul_repository import SEOUL_RECONSTRUCTION_EVENTS, trace_reveal_rule  # noqa: E402
from app.timeline_cases import CASES as TIMELINE_CASES  # noqa: E402

PROCESSED = REPO_ROOT / "data" / "processed"
RAW_DEM_DIR = REPO_ROOT / "data" / "raw" / "copernicus_dem_glo30"
TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True).transform
TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True).transform
NEIGHBOUR_EDGE_MIN_M = 1.0
CALIBRATION_STEP_M = 0.25
CALIBRATION_MAX_M = 6.0

# Fractions of the peak threshold per stage state. The basis is written into every output.
POHANG_FRACTIONS = {
    "typhoon_landfall": 0.0, "first_notice": 0.0, "river_overflow": 0.35, "move_car_broadcast": 0.6,
    "parking_inflow": 0.8, "parking_full": 1.0, "plant_outage": 1.0, "missing_report": 1.0,
}
ANDONG_FRACTIONS = {
    "first_isolation": 0.3, "flood_warning": 0.55, "camper_isolation": 0.6, "evacuation_order": 0.8,
    "predicted_warning_level": 1.0, "warning_lifted": 0.35, "national_landslide_alert": 0.2,
}

def seoul_fractions() -> dict[str, float]:
    rule = trace_reveal_rule()
    peak = max(row["rainfall_60min_running_max_mm"] for row in rule) or 1.0
    return {row["state"]: round(row["rainfall_60min_running_max_mm"] / peak, 4) for row in rule}


CASES: dict[str, dict[str, Any]] = {
    "seoul-2022": {
        "dir": "seoul_2022",
        "prefix": "seoul",
        "tile": "Copernicus_DSM_COG_10_N37_00_E126_00_DEM.tif",
        "aoi": "seoul_dorimcheon_aoi.geojson",
        "waterways": "seoul_osm_waterways_2022.geojson",
        "primary_river": "도림천",
        "primary_filter": {"waterway": "stream"},
        "cell_pixels": 3,
        "seed_distance_m": 150,
        "connectivity_m": (0, 2000),
        "connectivity_power": 2,
        "stages": [{"stage_index": i, **e} for i, e in enumerate(SEOUL_RECONSTRUCTION_EVENTS)],
        "driver": "RAINFALL_60MIN_RUNNING_MAX",
        "driver_basis": "신림P(2302) 60분 누적 강우의 단계 시각까지 최댓값을 사건 최댓값(121.5 mm)으로 나눈 비율로 띠를 넓힌다. 하천은 OSM stream 등급 선 전체(도림천·대방천·봉천천 등)이고 임계 0.25 m는 다른 사례와 같다. 공식 침수흔적도와 대조하면 띠의 14~16%만 흔적 위에 있어 재생용 도식이지 침수 근거가 아니다.",
        "fractions": seoul_fractions(),
        "anchors": None,
        "anchor_names": [],
    },
    "pohang-2022": {
        "dir": "pohang_2022",
        "prefix": "pohang",
        "tile": "Copernicus_DSM_COG_10_N35_00_E129_00_DEM.tif",
        "aoi": "pohang_aoi.geojson",
        "waterways": "pohang_osm_waterways.geojson",
        "primary_river": "냉천",
        "cell_pixels": 3,
        "seed_distance_m": 150,
        "connectivity_m": (0, 2000),
        "connectivity_power": 2,
        "stages": [{"stage_index": i, **e} for i, e in enumerate(TIMELINE_CASES["pohang-2022"]["replay"])],
        "driver": "REPORTED_ORDER_ONLY",
        "driver_basis": "관측 수위·강우 계열이 없어 보도된 사건 순서(범람 06:00 → 유입 06:37 → 완전 침수 06:45)로만 냉천 양안의 띠를 넓힌다(거리 = 비율²×2 km). 임계 상한은 보도된 침수 지점(인덕동 일대)에 닿는 최소 임계다.",
        "fractions": POHANG_FRACTIONS,
        "anchors": "pohang_focus_sites.geojson",
        "anchor_names": ["인덕동 일대"],
    },
    "andong-uiseong-2026": {
        "dir": "andong_uiseong_2026",
        "prefix": "andong",
        "tile": "Copernicus_DSM_COG_10_N36_00_E128_00_DEM.tif",
        "aoi": "andong_aoi.geojson",
        "waterways": "andong_osm_waterways.geojson",
        "primary_river": "미천",
        "primary_filter": {"waterway": "river"},
        "cell_pixels": 5,
        "seed_distance_m": 250,
        # The valley floor is HAND 0 almost everywhere, so the stage fraction mainly widens the band
        # around the river-class lines: distance = fraction^2 x 2 km (180 m at the first report, 2 km at the predicted peak).
        "connectivity_m": (0, 2000),
        "connectivity_power": 2,
        "anchor_snap_m": 400,
        "stages": [{"stage_index": i, **e} for i, e in enumerate(TIMELINE_CASES["andong-uiseong-2026"]["replay"])],
        "driver": "REPORTED_GAUGE_AND_ORDER",
        "driver_basis": "보도된 미천 운산리 수위(23:40 3.5 m, 경보 수위 4.7 m 도달 예측 00:30, 05:40 해제)로 상승·하강 순서만 정한다. 하천은 OSM river 등급 선(미천과 이름 없는 상류 구간) 전체이고, 상한은 침수가 보도된 귀미1리(일직면) 주변 가장 낮은 셀에 닿는 최소 임계로 맞춘다. 구계리(단촌면)는 river 선에서 5 km 떨어진 소하천 변이라 이 envelope으로 재현하지 않는다.",
        "fractions": ANDONG_FRACTIONS,
        "anchors": "andong_focus_sites.geojson",
        "anchor_names": ["귀미1리 (안동 일직면)"],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bbox_of(aoi: dict[str, Any]) -> tuple[float, float, float, float]:
    geom = shape(aoi["features"][0]["geometry"])
    return tuple(round(v, 6) for v in geom.bounds)  # type: ignore[return-value]


def read_dem_window(tile: Path, bbox: tuple[float, float, float, float]) -> tuple[np.ndarray, tuple[float, float, float, float], dict[str, Any]]:
    with tifffile.TiffFile(tile) as tif:
        page = tif.pages[0]
        scale = page.tags["ModelPixelScaleTag"].value
        tiepoint = page.tags["ModelTiepointTag"].value
        image = page.asarray()
    pixel_x, pixel_y = float(scale[0]), float(scale[1])
    origin_x, origin_y = float(tiepoint[3]), float(tiepoint[4])
    minx, miny, maxx, maxy = bbox
    col0 = max(0, int(np.floor((minx - origin_x) / pixel_x)))
    col1 = min(image.shape[1], int(np.ceil((maxx - origin_x) / pixel_x)))
    row0 = max(0, int(np.floor((origin_y - maxy) / pixel_y)))
    row1 = min(image.shape[0], int(np.ceil((origin_y - miny) / pixel_y)))
    window = image[row0:row1, col0:col1].astype(float)
    bounds = (origin_x + col0 * pixel_x, origin_y - row1 * pixel_y, origin_x + col1 * pixel_x, origin_y - row0 * pixel_y)
    metadata = {
        "raw_file": str(tile.relative_to(REPO_ROOT)).replace("\\", "/"),
        "raw_sha256": sha256(tile),
        "raw_crs": "EPSG:4326",
        "raw_pixel_size_degrees": [pixel_x, pixel_y],
        "window_shape": list(window.shape),
        "window_bounds": list(bounds),
        "source": "Copernicus DEM GLO-30 (public AWS Open Data bucket copernicus-dem-30m)",
    }
    return window, bounds, metadata


def build_cells(dem: np.ndarray, bounds: tuple[float, float, float, float], pixels: int) -> list[dict[str, Any]]:
    minx, miny, maxx, maxy = bounds
    rows_px, cols_px = dem.shape
    grid_rows = rows_px // pixels
    grid_cols = cols_px // pixels
    dx = (maxx - minx) / cols_px * pixels
    dy = (maxy - miny) / rows_px * pixels
    cells = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            block = dem[row * pixels:(row + 1) * pixels, col * pixels:(col + 1) * pixels]
            finite = block[np.isfinite(block)]
            if finite.size == 0:
                continue
            geometry = box(minx + col * dx, maxy - (row + 1) * dy, minx + (col + 1) * dx, maxy - row * dy)
            cells.append({"grid_id": f"dem-{row:03d}-{col:03d}", "elevation_m": float(finite.mean()), "geometry": geometry, "geometry_m": transform(TO_METERS, geometry)})
    return cells


def build_neighbours(cells: list[dict[str, Any]]) -> list[list[int]]:
    geometries = [cell["geometry_m"] for cell in cells]
    tree = STRtree(geometries)
    neighbours: list[list[int]] = []
    for index, geometry in enumerate(geometries):
        found = []
        for other in tree.query(geometry.buffer(0.5)):
            other = int(other)
            if other == index:
                continue
            if geometry.boundary.intersection(geometries[other].boundary).length > NEIGHBOUR_EDGE_MIN_M:
                found.append(other)
        neighbours.append(found)
    return neighbours


def flood_fill(candidates: set[int], seeds: set[int], neighbours: list[list[int]]) -> set[int]:
    reached = set(seeds & candidates)
    queue = deque(reached)
    while queue:
        current = queue.popleft()
        for other in neighbours[current]:
            if other in candidates and other not in reached:
                reached.add(other)
                queue.append(other)
    return reached


def envelope(cells: list[dict[str, Any]], neighbours: list[list[int]], threshold_m: float, connectivity_m: float, seed_distance_m: float, origin: Point | None = None) -> set[int]:
    """Cells at or below the HAND threshold, grid-connected to river-side seeds.

    Without an origin, connectivity is measured from the primary river (the whole reach rises).
    With an origin (a reported overflow point), connectivity is measured from that point, so the
    envelope spreads outward from where overflow was reported.
    """
    if threshold_m <= 0:
        return set()
    if origin is None:
        candidates = {i for i, c in enumerate(cells) if c["hand_m"] <= threshold_m and c["distance_to_primary_river_m"] <= connectivity_m}
        seeds = {i for i in candidates if cells[i]["distance_to_primary_river_m"] <= seed_distance_m}
    else:
        candidates = {i for i, c in enumerate(cells) if c["hand_m"] <= threshold_m and c["centroid"].distance(origin) <= connectivity_m}
        seeds = {i for i in candidates if cells[i]["distance_to_primary_river_m"] <= seed_distance_m and cells[i]["centroid"].distance(origin) <= seed_distance_m * 2}
    return flood_fill(candidates, seeds, neighbours)


def calibrate_peak(cells: list[dict[str, Any]], neighbours: list[list[int]], anchor_cells: list[int], connectivity_m: float, seed_distance_m: float, origin: Point | None = None) -> dict[str, Any]:
    threshold = CALIBRATION_STEP_M
    while threshold <= CALIBRATION_MAX_M + 1e-9:
        reached = envelope(cells, neighbours, threshold, connectivity_m, seed_distance_m, origin)
        if all(i in reached for i in anchor_cells):
            return {"peak_threshold_m": round(threshold, 2), "all_anchors_reached": True}
        threshold += CALIBRATION_STEP_M
    return {"peak_threshold_m": CALIBRATION_MAX_M, "all_anchors_reached": False}


def calibrate_reach(cells: list[dict[str, Any]], neighbours: list[list[int]], anchor_cells: list[int], threshold_m: float, seed_distance_m: float, origin: Point, base_m: float, max_m: float) -> float:
    """Smallest spread distance from the origin (100 m steps) at which every anchor is reached."""
    reach = base_m
    while reach <= max_m + 1e-9:
        if all(i in envelope(cells, neighbours, threshold_m, reach, seed_distance_m, origin) for i in anchor_cells):
            return reach
        reach += 100
    return max_m


def run_case(event_id: str) -> dict[str, Any]:
    case = CASES[event_id]
    case_dir = PROCESSED / case["dir"]
    aoi = read_geojson(case_dir / case["aoi"])
    bbox = bbox_of(aoi)
    dem, bounds, dem_meta = read_dem_window(RAW_DEM_DIR / case["tile"], bbox)
    cells = build_cells(dem, bounds, case["cell_pixels"])

    waterways = read_geojson(case_dir / case["waterways"])
    primary_filter = case.get("primary_filter") or {"name": case["primary_river"]}
    primary = unary_union([transform(TO_METERS, shape(f["geometry"])) for f in waterways["features"] if all(f["properties"].get(k) == v for k, v in primary_filter.items())])
    if primary.is_empty:
        raise RuntimeError(f"{case['primary_river']} not found in {case['waterways']}")
    all_rivers = unary_union([transform(TO_METERS, shape(f["geometry"])) for f in waterways["features"]])
    for cell in cells:
        centroid = cell["geometry_m"].centroid
        cell["centroid"] = centroid
        cell["distance_to_primary_river_m"] = centroid.distance(primary)
        cell["distance_to_river_m"] = centroid.distance(all_rivers)
    drainage = [c for c in cells if c["distance_to_primary_river_m"] <= case["seed_distance_m"]]
    if not drainage:
        raise RuntimeError("No DEM cell lies within the seed distance of the primary river")
    drainage_tree = STRtree([c["centroid"] for c in drainage])
    for cell in cells:
        nearest = drainage[int(drainage_tree.nearest(cell["centroid"]))]
        cell["drainage_elevation_m"] = nearest["elevation_m"]
        cell["hand_m"] = max(0.0, cell["elevation_m"] - nearest["elevation_m"])
    neighbours = build_neighbours(cells)
    cell_size_m = round((cells[0]["geometry_m"].bounds[2] - cells[0]["geometry_m"].bounds[0]), 1)

    stages = case["stages"]
    base_conn, span_conn = case["connectivity_m"]
    anchors: list[dict[str, Any]] = []
    fractions = case["fractions"]
    sites = read_geojson(case_dir / case["anchors"]) if case.get("anchors") else {"features": []}
    tree = STRtree([c["geometry_m"] for c in cells])
    origin: Point | None = None
    for site in sites["features"]:
        point = transform(TO_METERS, Point(site["geometry"]["coordinates"]))
        if site["properties"].get("name") == case.get("origin_name"):
            origin = point
        if site["properties"].get("name") in case["anchor_names"]:
            snap = case.get("anchor_snap_m", 0)
            nearby = [int(i) for i in tree.query(point.buffer(snap))] if snap else []
            index = min(nearby, key=lambda i: cells[i]["hand_m"]) if nearby else int(tree.nearest(point))
            anchors.append({"name": site["properties"]["name"], "grid_id": cells[index]["grid_id"], "cell_index": index, "hand_m": round(cells[index]["hand_m"], 2), "distance_to_primary_river_m": round(cells[index]["distance_to_primary_river_m"], 1), "snapped_within_m": snap, "distance_from_reported_point_m": round(cells[index]["centroid"].distance(point), 1)})
    if case.get("origin_name") and origin is None:
        raise RuntimeError(f"Origin site {case['origin_name']} not found in {case['anchors']}")
    calibration = calibrate_peak(cells, neighbours, [a["cell_index"] for a in anchors], base_conn + span_conn, case["seed_distance_m"], origin)
    peak_threshold = calibration["peak_threshold_m"]
    if origin is not None:
        span_conn = calibrate_reach(cells, neighbours, [a["cell_index"] for a in anchors], peak_threshold, case["seed_distance_m"], origin, base_conn, base_conn + span_conn) - base_conn
        calibration["origin"] = case["origin_name"]
        calibration["peak_reach_from_origin_m"] = base_conn + span_conn

    features: list[dict[str, Any]] = []
    stage_counts: dict[str, int] = {}
    stage_contexts = []
    for stage in stages:
        fraction = float(fractions.get(stage["state"], 0.0))
        threshold = round(fraction * peak_threshold, 2)
        connectivity = base_conn + (fraction ** case.get("connectivity_power", 1)) * span_conn
        reached = envelope(cells, neighbours, threshold, connectivity, case["seed_distance_m"], origin)
        for index in sorted(reached):
            cell = cells[index]
            features.append({
                "type": "Feature",
                "properties": {
                    "grid_id": cell["grid_id"], "layer_role": "hand_flood_envelope", "status": "TEMPORARY", "source_type": "DERIVED_APPROXIMATION",
                    "stage_index": stage["stage_index"], "time": stage["time"], "state": stage["state"], "label": stage["label"],
                    "hand_m": round(cell["hand_m"], 2), "hand_threshold_m": threshold, "stage_fraction": fraction,
                    "mean_elevation_m": round(cell["elevation_m"], 2), "distance_to_primary_river_m": round(cell["distance_to_primary_river_m"], 1),
                    "stage_driver": case["driver"], "not_official_flood_extent": True, "not_hydraulic_simulation": True,
                },
                "geometry": mapping(cell["geometry"]),
            })
        stage_counts[stage["state"]] = len(reached)
        stage_contexts.append({"stage_index": stage["stage_index"], "time": stage["time"], "state": stage["state"], "stage_fraction": fraction, "hand_threshold_m": threshold, "connectivity_distance_m": round(connectivity), "selected_feature_count": len(reached)})

    grid_out = {
        "type": "FeatureCollection", "name": f"{case['prefix']}_hand_reconstruction_grid",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {"event_id": event_id, "status": "TEMPORARY", "source_type": "DERIVED_APPROXIMATION", "role": "HAND-like reconstruction grid; not official Flood Extent", "primary_river": case["primary_river"], "cell_size_m": cell_size_m},
        "features": [{"type": "Feature", "properties": {"grid_id": c["grid_id"], "mean_elevation_m": round(c["elevation_m"], 2), "hand_m": round(c["hand_m"], 2), "distance_to_primary_river_m": round(c["distance_to_primary_river_m"], 1), "distance_to_river_m": round(c["distance_to_river_m"], 1), "status": "TEMPORARY"}, "geometry": mapping(c["geometry"])} for c in cells],
    }
    limitations = [
        ("관측 수위가 아니라 강우 비율" if case["driver"].startswith("RAINFALL") else "관측 수위가 아니라 보도된 사건 순서") + "로 띠를 넓힌 지형 근사다. 침수심·유속·유량을 계산하지 않는다.",
        f"{cell_size_m:.0f} m 격자라 제방·도로 성토·배수로처럼 격자보다 좁은 구조물은 반영되지 않는다.",
        "공식 침수범위가 아니며 노출 집계에 쓰지 않는다.",
    ]
    limitations.insert(1, f"임계 상한 {peak_threshold} m는 관측값이 아니라 보도된 침수 지점에 닿도록 맞춘 값이다.")
    timeline_out = {
        "type": "FeatureCollection", "name": f"{case['prefix']}_hand_flood_envelope_timeline",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "event_id": event_id, "status": "TEMPORARY", "source_type": "DERIVED_APPROXIMATION",
            "role": "HAND-based stage envelope; visual replay only", "stage_driver": case["driver"], "stage_driver_basis": case["driver_basis"],
            "peak_threshold_m": peak_threshold, "primary_river": case["primary_river"], "cell_size_m": cell_size_m, "limitations": limitations,
        },
        "features": features,
    }
    grid_file = case_dir / f"{case['prefix']}_hand_reconstruction_grid.geojson"
    timeline_file = case_dir / f"{case['prefix']}_hand_flood_envelope_timeline.geojson"
    report_file = case_dir / f"{case['prefix']}_hand_reconstruction_validation.json"
    grid_file.write_text(json.dumps(grid_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    timeline_file.write_text(json.dumps(timeline_out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    report: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id, "status": "TEMPORARY", "source_type": "DERIVED_APPROXIMATION",
        "method": f"Height above the nearest {case['primary_river']} cell on a {cell_size_m:.0f} m Copernicus DEM grid, thresholded per stage, 4-neighbour flood fill from river-side seeds.",
        "stage_driver": case["driver"], "stage_driver_basis": case["driver_basis"], "peak_threshold_m": peak_threshold,
        "dem": dem_meta, "aoi_bbox": list(bbox), "cell_size_m": cell_size_m, "grid_feature_count": len(cells), "timeline_feature_count": len(features),
        "seed_distance_m": case["seed_distance_m"], "connectivity_distance_m": {"base": base_conn, "peak": base_conn + span_conn, "power": case.get("connectivity_power", 1), "measured_from": case.get("origin_name") or case["primary_river"]},
        "stage_counts": stage_counts, "stage_contexts": stage_contexts, "limitations": limitations,
        "output_files": [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in (grid_file, timeline_file, report_file)],
        "validity_assessment": {
            "appropriate_use": "Stage-by-stage replay of where low, river-connected terrain lies as the reported event unfolds.",
            "inappropriate_use": "Official flood extent, hydraulic simulation, depth or velocity estimate, exposure KPI.",
        },
    }
    report["calibration"] = {**calibration, "anchors": anchors}
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"event_id": event_id, "grid_cells": len(cells), "timeline_features": len(features), "peak_threshold_m": peak_threshold, "stage_counts": stage_counts, "calibration": report["calibration"]}


def main() -> None:
    targets = sys.argv[1:] or list(CASES)
    for event_id in targets:
        print(json.dumps(run_case(event_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
