import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from collections import deque

from shapely.geometry import LineString, mapping, shape
from shapely.ops import nearest_points, transform, unary_union
from shapely.strtree import STRtree


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"

DEM_GRID_FILE = OSONG_DIR / "osong_dem_elevation_grid.geojson"
RIVER_FILE = OSONG_DIR / "osong_wamis_rivers.geojson"
UNDERPASS_FILE = OSONG_DIR / "gungpyeong2_underpass.geojson"
WATER_LEVEL_FILE = OSONG_DIR / "osong_hrfco_water_level_10m_2023-07-14_17.csv"
RAINFALL_FILE = OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv"

HAND_GRID_FILE = OSONG_DIR / "osong_hand_reconstruction_grid.geojson"
HAND_TIMELINE_FILE = OSONG_DIR / "osong_hand_flood_envelope_timeline.geojson"
HAND_REPORT_FILE = OSONG_DIR / "osong_hand_reconstruction_validation.json"
HAND_REFERENCE_FILE = OSONG_DIR / "osong_hand_reference_other_drainage.geojson"

# The incident is a Miho River temporary-levee breach. Only the Miho River gauge
# drives the stage threshold, so only cells reachable from the Miho side count
# as the incident envelope.
PRIMARY_RIVER_NAME = "미호천"
PRIMARY_SEED_DISTANCE_M = 250
# Cells sharing an edge longer than this are neighbours (4-neighbour grid).
NEIGHBOUR_EDGE_MIN_M = 1.0

TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True).transform
TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True).transform

PRIMARY_WATER_LEVEL_STATION_ID = "3011665"

EVENT_STAGES = [
    {
        "stage_index": 0,
        "time": "2023-07-15T04:10:00+09:00",
        "state": "warning",
        "label": "Flood warning",
        "connectivity_distance_m": 100,
        "flow_corridor_m": 80,
        "breach_boost_m": 0.0,
    },
    {
        "stage_index": 1,
        "time": "2023-07-15T06:40:00+09:00",
        "state": "hydraulic_warning",
        "label": "Design flood level reached",
        "connectivity_distance_m": 250,
        "flow_corridor_m": 140,
        "breach_boost_m": 0.2,
    },
    {
        "stage_index": 2,
        "time": "2023-07-15T07:50:00+09:00",
        "state": "overtopping",
        "label": "Overtopping begins",
        "connectivity_distance_m": 450,
        "flow_corridor_m": 220,
        "breach_boost_m": 0.8,
    },
    {
        "stage_index": 3,
        "time": "2023-07-15T08:09:00+09:00",
        "state": "levee_failure",
        "label": "Temporary levee failure",
        "connectivity_distance_m": 700,
        "flow_corridor_m": 340,
        "breach_boost_m": 1.6,
    },
    {
        "stage_index": 4,
        "time": "2023-07-15T08:27:00+09:00",
        "state": "underpass_inflow",
        "label": "Underpass inflow starts",
        "connectivity_distance_m": 950,
        "flow_corridor_m": 460,
        "breach_boost_m": 2.2,
    },
    {
        "stage_index": 5,
        "time": "2023-07-15T08:35:00+09:00",
        "state": "unsafe_driving",
        "label": "Unsafe driving condition",
        "connectivity_distance_m": 1150,
        "flow_corridor_m": 560,
        "breach_boost_m": 2.8,
    },
    {
        "stage_index": 6,
        "time": "2023-07-15T08:40:00+09:00",
        "state": "full_inundation",
        "label": "Full inundation",
        "connectivity_distance_m": 1350,
        "flow_corridor_m": 660,
        "breach_boost_m": 3.2,
    },
]


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def iso_to_kst_hour(ts: str) -> str:
    return ts.replace("T", " ").replace("+09:00", "")[:13] + ":00"


def nearest_water_level(rows: list[dict[str, str]], stage_time: str) -> dict[str, Any]:
    from datetime import datetime

    target = datetime.fromisoformat(stage_time)
    candidates = [
        row
        for row in rows
        if row.get("station_id") == PRIMARY_WATER_LEVEL_STATION_ID and row.get("water_level_m")
    ]
    if not candidates:
        candidates = [row for row in rows if row.get("water_level_m")]
    best = min(
        candidates,
        key=lambda row: abs((datetime.fromisoformat(row["timestamp_kst"].replace(" ", "T") + "+09:00") - target).total_seconds()),
    )
    return {
        "station_id": best["station_id"],
        "station_name": best.get("station_name"),
        "timestamp_kst": best["timestamp_kst"],
        "water_level_m": float(best["water_level_m"]),
    }


def rainfall_context(rows: list[dict[str, str]], stage_time: str) -> dict[str, Any]:
    stage_hour = iso_to_kst_hour(stage_time)
    matching = [row for row in rows if row.get("timestamp_kst") == stage_hour and row.get("rainfall_mm")]
    hourly_values = [float(row["rainfall_mm"]) for row in matching]
    all_values = [float(row["rainfall_mm"]) for row in rows if row.get("rainfall_mm")]
    return {
        "timestamp_kst": stage_hour,
        "station_count": len(matching),
        "max_hourly_rainfall_mm": max(hourly_values) if hourly_values else None,
        "event_peak_hourly_rainfall_mm": max(all_values) if all_values else None,
    }


def classify_hand(hand_m: float) -> str:
    if hand_m <= 1.0:
        return "LOW_HAND"
    if hand_m <= 3.0:
        return "MODERATE_HAND"
    if hand_m <= 6.0:
        return "HIGH_HAND"
    return "VERY_HIGH_HAND"


def build_hand_grid() -> tuple[dict[str, Any], list[dict[str, Any]], LineString, dict[str, float]]:
    dem_grid = read_geojson(DEM_GRID_FILE)
    rivers = read_geojson(RIVER_FILE)
    underpass = read_geojson(UNDERPASS_FILE)

    river_union = unary_union([transform(TO_METERS, shape(feature["geometry"])) for feature in rivers["features"]])
    primary_river = unary_union(
        [
            transform(TO_METERS, shape(feature["geometry"]))
            for feature in rivers["features"]
            if feature["properties"].get("RIVNM_2") == PRIMARY_RIVER_NAME
        ]
    )
    if primary_river.is_empty:
        raise RuntimeError(f"{PRIMARY_RIVER_NAME} polygon not found in {RIVER_FILE}")
    underpass_union = unary_union([transform(TO_METERS, shape(feature["geometry"])) for feature in underpass["features"]])
    underpass_center = underpass_union.centroid
    breach_point = nearest_points(river_union, underpass_center)[0]
    flow_path = LineString([breach_point, underpass_center])

    cells = []
    for feature in dem_grid["features"]:
        geom_m = transform(TO_METERS, shape(feature["geometry"]))
        centroid = geom_m.centroid
        elevation = float(feature["properties"]["mean_elevation_m"])
        distance_to_river = centroid.distance(river_union)
        distance_to_underpass = centroid.distance(underpass_center)
        distance_to_flow_path = centroid.distance(flow_path)
        cells.append(
            {
                "source_feature": feature,
                "geometry_m": geom_m,
                "centroid": centroid,
                "elevation_m": elevation,
                "distance_to_river_m": distance_to_river,
                "distance_to_primary_river_m": centroid.distance(primary_river),
                "distance_to_underpass_m": distance_to_underpass,
                "distance_to_flow_path_m": distance_to_flow_path,
            }
        )

    drainage_cells = [cell for cell in cells if cell["distance_to_river_m"] <= 250]
    if not drainage_cells:
        drainage_cells = sorted(cells, key=lambda cell: cell["distance_to_river_m"])[:20]

    primary_drainage_cells = [cell for cell in cells if cell["distance_to_primary_river_m"] <= PRIMARY_SEED_DISTANCE_M]
    if not primary_drainage_cells:
        raise RuntimeError(f"No DEM cell lies within {PRIMARY_SEED_DISTANCE_M} m of {PRIMARY_RIVER_NAME}")

    hand_features = []
    hand_values = []
    for cell in cells:
        local_drainage = min(drainage_cells, key=lambda candidate: candidate["centroid"].distance(cell["centroid"]))
        drainage_elevation = local_drainage["elevation_m"]
        hand_m = max(0.0, cell["elevation_m"] - drainage_elevation)
        primary_drainage = min(primary_drainage_cells, key=lambda candidate: candidate["centroid"].distance(cell["centroid"]))
        hand_primary_m = max(0.0, cell["elevation_m"] - primary_drainage["elevation_m"])
        hand_values.append(hand_m)
        properties = dict(cell["source_feature"]["properties"])
        properties.update(
            {
                "layer_role": "hand_reconstruction_grid",
                "status": "TEMPORARY",
                "source_type": "DERIVED_APPROXIMATION",
                "method": "HAND-like relative elevation to nearest WAMIS drainage context using Copernicus DEM grid.",
                "mean_elevation_m": round(cell["elevation_m"], 2),
                "local_drainage_elevation_m": round(drainage_elevation, 2),
                "hand_m": round(hand_m, 2),
                "hand_class": classify_hand(hand_m),
                "primary_drainage_elevation_m": round(primary_drainage["elevation_m"], 2),
                "hand_primary_m": round(hand_primary_m, 2),
                "distance_to_river_m": round(cell["distance_to_river_m"], 1),
                "distance_to_primary_river_m": round(cell["distance_to_primary_river_m"], 1),
                "distance_to_underpass_m": round(cell["distance_to_underpass_m"], 1),
                "distance_to_flow_path_m": round(cell["distance_to_flow_path_m"], 1),
                "not_official_flood_extent": True,
                "not_hydraulic_simulation": True,
            }
        )
        hand_features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": cell["source_feature"]["geometry"],
            }
        )

    stats = {
        "min_hand_m": round(min(hand_values), 2),
        "max_hand_m": round(max(hand_values), 2),
        "mean_hand_m": round(sum(hand_values) / len(hand_values), 2),
        "drainage_cell_count": len(drainage_cells),
        "primary_drainage_cell_count": len(primary_drainage_cells),
    }
    output = {
        "type": "FeatureCollection",
        "name": "osong_hand_reconstruction_grid",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "event_id": "osong-2023",
            "status": "TEMPORARY",
            "source_type": "DERIVED_APPROXIMATION",
            "role": "HAND-like reconstruction grid; not official Flood Extent",
            "method": "Relative elevation to WAMIS river drainage context from Copernicus DEM grid.",
            "limitations": [
                "Gauge water-level datum is not converted to DEM vertical datum.",
                "Nearest-drainage elevation is estimated from coarse processed DEM grid cells.",
                "Connectivity is approximate and not a hydraulic routing calculation.",
            ],
        },
        "features": hand_features,
    }
    breach_cell = min(range(len(cells)), key=lambda index: cells[index]["geometry_m"].distance(breach_point))
    return output, cells, flow_path, stats, build_neighbours(cells), breach_cell


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
            shared = geometry.boundary.intersection(geometries[other].boundary)
            if shared.length > NEIGHBOUR_EDGE_MIN_M:
                found.append(other)
        neighbours.append(found)
    return neighbours


def breach_connected(candidates: set[int], seeds: set[int], neighbours: list[list[int]]) -> set[int]:
    """Grow from Miho-side seeds through adjacent candidate cells only."""

    reached = set(seeds & candidates)
    queue = deque(reached)
    while queue:
        current = queue.popleft()
        for other in neighbours[current]:
            if other in candidates and other not in reached:
                reached.add(other)
                queue.append(other)
    return reached


def create_timeline(
    hand_grid: dict[str, Any],
    water_rows: list[dict[str, str]],
    rain_rows: list[dict[str, str]],
    flow_path: LineString,
    neighbours: list[list[int]],
    breach_cell: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int], list[dict[str, Any]]]:
    levels = [nearest_water_level(water_rows, stage["time"]) for stage in EVENT_STAGES]
    baseline_level = levels[0]["water_level_m"]
    max_relative_rise = max(level["water_level_m"] - baseline_level for level in levels)
    features = []
    reference_features = []
    stage_counts: dict[str, int] = {}
    stage_contexts = []
    grid = hand_grid["features"]

    for stage, level in zip(EVENT_STAGES, levels):
        relative_rise = max(0.0, level["water_level_m"] - baseline_level)
        threshold = max(0.25, relative_rise + stage["breach_boost_m"])
        rain = rainfall_context(rain_rows, stage["time"])
        count = 0
        candidate_count = 0
        reference_count = 0
        if stage["stage_index"] > 0:
            candidates: set[int] = set()
            legacy_candidates: set[int] = set()
            for index, feature in enumerate(grid):
                props = feature["properties"]
                hand_m = float(props["hand_m"])
                near_drainage = (
                    float(props["distance_to_river_m"]) <= stage["connectivity_distance_m"]
                    or float(props["distance_to_flow_path_m"]) <= stage["flow_corridor_m"]
                    or (
                        stage["stage_index"] >= 4
                        and float(props["distance_to_underpass_m"]) <= stage["connectivity_distance_m"] * 0.9
                    )
                )
                if near_drainage and hand_m <= threshold:
                    legacy_candidates.add(index)
                # The threshold comes from the Miho River gauge, so height is measured against Miho drainage.
                if near_drainage and float(props["hand_primary_m"]) <= threshold:
                    candidates.add(index)
            seeds = {
                index for index in candidates
                if float(grid[index]["properties"]["distance_to_primary_river_m"]) <= PRIMARY_SEED_DISTANCE_M
            }
            if stage["stage_index"] >= 3:
                seeds.add(breach_cell)
            reached = breach_connected(candidates, seeds, neighbours)
            candidate_count = len(legacy_candidates)
            for index in sorted(legacy_candidates - reached):
                properties = dict(grid[index]["properties"])
                properties.update(
                    {
                        "layer_role": "hand_reference_other_drainage",
                        "stage_index": stage["stage_index"],
                        "time": stage["time"],
                        "state": stage["state"],
                        "hand_threshold_m": round(threshold, 2),
                        "reason": "Low relative to its nearest drainage line (legacy rule) but above the Miho-referenced threshold or not grid-connected to the Miho River side.",
                    }
                )
                reference_features.append({"type": "Feature", "properties": properties, "geometry": grid[index]["geometry"]})
                reference_count += 1
            for index in sorted(reached):
                feature = grid[index]
                props = feature["properties"]
                properties = dict(props)
                properties.update(
                    {
                        "layer_role": "hand_flood_envelope",
                        "connectivity": "grid-connected to Miho River side or breach cell",
                        "stage_index": stage["stage_index"],
                        "time": stage["time"],
                        "state": stage["state"],
                        "label": stage["label"],
                        "observed_water_level_m": level["water_level_m"],
                        "water_level_timestamp_kst": level["timestamp_kst"],
                        "relative_water_level_rise_m": round(relative_rise, 2),
                        "hand_threshold_m": round(threshold, 2),
                        "stage_hourly_rainfall_mm": rain["max_hourly_rainfall_mm"],
                        "event_peak_hourly_rainfall_mm": rain["event_peak_hourly_rainfall_mm"],
                    }
                )
                features.append({"type": "Feature", "properties": properties, "geometry": feature["geometry"]})
                count += 1
            if stage["stage_index"] >= 3:
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "layer_role": "hand_flow_connection",
                            "status": "TEMPORARY",
                            "source_type": "DERIVED_APPROXIMATION",
                            "stage_index": stage["stage_index"],
                            "time": stage["time"],
                            "state": stage["state"],
                            "label": f"{stage['label']} HAND connection context",
                            "basis": "Nearest WAMIS drainage point to Gungpyeong 2 Underpass; directional context only.",
                            "not_official_flood_extent": True,
                            "not_hydraulic_simulation": True,
                        },
                        "geometry": mapping(transform(TO_WGS84, flow_path)),
                    }
                )
        stage_counts[stage["state"]] = count
        stage_contexts.append(
            {
                "stage_index": stage["stage_index"],
                "time": stage["time"],
                "state": stage["state"],
                "observed_water_level_m": level["water_level_m"],
                "water_level_timestamp_kst": level["timestamp_kst"],
                "relative_water_level_rise_m": round(relative_rise, 2),
                "hand_threshold_m": round(threshold, 2),
                "selected_feature_count": count,
                "legacy_rule_count": candidate_count,
                "reference_other_drainage_count": reference_count,
            }
        )

    output = {
        "type": "FeatureCollection",
        "name": "osong_hand_flood_envelope_timeline",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "event_id": "osong-2023",
            "status": "TEMPORARY",
            "source_type": "DERIVED_APPROXIMATION",
            "role": "HAND-based historical reconstruction envelope; visual comparison only",
            "data_vintage": "2023-07-15 incident timeline with 2023-07-14 through 2023-07-17 observations",
            "method": "Height above the nearest Miho River drainage cell, thresholded by observed Miho River water-level rise per incident stage, keeping only cells grid-connected (4-neighbour) to the Miho River side or the breach cell.",
            "limitations": [
                "Observed gauge level is used as relative stage change, not absolute DEM water-surface elevation.",
                "Grid connectivity uses about 280 m DEM cells, so levees, road embankments, and drains narrower than a cell are not represented.",
                "No discharge, breach geometry, roughness, depth, velocity, or drainage structure simulation is computed.",
                "Do not use for final official exposure KPI counts.",
            ],
        },
        "features": features,
    }
    reference = {
        "type": "FeatureCollection",
        "name": "osong_hand_reference_other_drainage",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "event_id": "osong-2023",
            "status": "REFERENCE_ONLY",
            "source_type": "DERIVED_APPROXIMATION",
            "role": "Low-lying cells near other drainage lines; excluded from the Miho breach envelope",
            "limitations": [
                "The stage threshold comes from the Miho River gauge; no gauge evidence exists for the other drainage lines.",
                "Not a flood extent and not used for exposure counts.",
            ],
        },
        "features": reference_features,
    }
    return output, reference, stage_counts, stage_contexts


def main() -> None:
    hand_grid, _, flow_path, hand_stats, neighbours, breach_cell = build_hand_grid()
    water_rows = read_csv(WATER_LEVEL_FILE)
    rain_rows = read_csv(RAINFALL_FILE)
    timeline, reference, stage_counts, stage_contexts = create_timeline(hand_grid, water_rows, rain_rows, flow_path, neighbours, breach_cell)

    HAND_GRID_FILE.write_text(json.dumps(hand_grid, ensure_ascii=False, indent=2), encoding="utf-8")
    HAND_TIMELINE_FILE.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    HAND_REFERENCE_FILE.write_text(json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "TEMPORARY",
        "source_type": "DERIVED_APPROXIMATION",
        "method": "Miho-referenced HAND-like height with Miho-side grid connectivity (4-neighbour flood fill from Miho River cells and the breach cell).",
        "output_files": [
            str(HAND_GRID_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(HAND_TIMELINE_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(HAND_REFERENCE_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        ],
        "input_files": [
            str(DEM_GRID_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(RIVER_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(UNDERPASS_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(WATER_LEVEL_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
            str(RAINFALL_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        ],
        "crs": "EPSG:4326 / CRS84",
        "hand_grid_feature_count": len(hand_grid["features"]),
        "timeline_feature_count": len(timeline["features"]),
        "timeline_geometry_types": sorted({feature["geometry"]["type"] for feature in timeline["features"]}),
        "hand_stats": hand_stats,
        "stage_counts": stage_counts,
        "reference_other_drainage_feature_count": len(reference["features"]),
        "breach_cell_id": hand_grid["features"][breach_cell]["properties"].get("cell_id"),
        "stage_contexts": stage_contexts,
        "validity_assessment": {
            "appropriate_use": "Historical reconstruction visualization using observed water-level timing and terrain connectivity.",
            "inappropriate_use": "Official Flood Extent, hydraulic simulation, depth/velocity estimate, or final exposure KPI.",
            "confidence": "MEDIUM_FOR_RELATIVE_TERRAIN_CONNECTIVITY; LOW_TO_MEDIUM_FOR_SPATIAL_EXTENT",
        },
        "data_warning": "This is a HAND-like approximation. Gauge datum is not converted to DEM vertical datum.",
    }
    HAND_REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "hand_grid": str(HAND_GRID_FILE),
                "timeline": str(HAND_TIMELINE_FILE),
                "report": str(HAND_REPORT_FILE),
                "hand_grid_feature_count": len(hand_grid["features"]),
                "timeline_feature_count": len(timeline["features"]),
                "stage_counts": stage_counts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
