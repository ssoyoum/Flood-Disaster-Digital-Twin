import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import LineString, mapping, shape
from shapely.ops import nearest_points, transform, unary_union


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"

LOW_ELEVATION_FILE = OSONG_DIR / "osong_dem_low_elevation_context.geojson"
RIVER_FILE = OSONG_DIR / "osong_wamis_rivers.geojson"
UNDERPASS_FILE = OSONG_DIR / "gungpyeong2_underpass.geojson"
RAINFALL_FILE = OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv"
WATER_LEVEL_FILE = OSONG_DIR / "osong_hrfco_water_level_10m_2023-07-14_17.csv"
OUTPUT_FILE = OSONG_DIR / "osong_approx_flood_envelope_timeline.geojson"
REPORT_FILE = OSONG_DIR / "osong_approx_flood_envelope_validation.json"

TO_METERS = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True).transform
TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True).transform

EVENT_STAGES = [
    {
        "stage_index": 0,
        "time": "2023-07-15T04:10:00+09:00",
        "state": "warning",
        "label": "Flood warning",
        "river_distance_m": 0,
        "underpass_distance_m": 0,
        "elevation_rank": 0.0,
    },
    {
        "stage_index": 1,
        "time": "2023-07-15T06:40:00+09:00",
        "state": "hydraulic_warning",
        "label": "Design flood level reached",
        "river_distance_m": 250,
        "underpass_distance_m": 0,
        "elevation_rank": 0.20,
    },
    {
        "stage_index": 2,
        "time": "2023-07-15T07:50:00+09:00",
        "state": "overtopping",
        "label": "Overtopping begins",
        "river_distance_m": 450,
        "underpass_distance_m": 900,
        "elevation_rank": 0.45,
    },
    {
        "stage_index": 3,
        "time": "2023-07-15T08:09:00+09:00",
        "state": "levee_failure",
        "label": "Temporary levee failure",
        "river_distance_m": 750,
        "underpass_distance_m": 1200,
        "elevation_rank": 0.68,
    },
    {
        "stage_index": 4,
        "time": "2023-07-15T08:27:00+09:00",
        "state": "underpass_inflow",
        "label": "Underpass inflow starts",
        "river_distance_m": 950,
        "underpass_distance_m": 900,
        "elevation_rank": 0.86,
    },
    {
        "stage_index": 5,
        "time": "2023-07-15T08:35:00+09:00",
        "state": "unsafe_driving",
        "label": "Unsafe driving condition",
        "river_distance_m": 1150,
        "underpass_distance_m": 1200,
        "elevation_rank": 0.95,
    },
    {
        "stage_index": 6,
        "time": "2023-07-15T08:40:00+09:00",
        "state": "full_inundation",
        "label": "Full inundation",
        "river_distance_m": 1400,
        "underpass_distance_m": 1500,
        "elevation_rank": 1.0,
    },
]


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def peak_rainfall() -> dict[str, Any]:
    rows = read_csv(RAINFALL_FILE)
    peak = max(rows, key=lambda row: float(row["rainfall_mm"]) if row.get("rainfall_mm") else -1)
    return {
        "source": "KMA AWS/ASOS rainfall observation",
        "period": "2023-07-14 01:00 through 2023-07-17 00:00 KST",
        "records": len(rows),
        "peak_mm_per_hour": float(peak["rainfall_mm"]),
        "peak_timestamp": peak["timestamp_kst"],
        "peak_station_id": peak["station_id"],
        "peak_station_name": peak["station_name"],
    }


def peak_water_level() -> dict[str, Any]:
    rows = read_csv(WATER_LEVEL_FILE)
    primary_rows = [row for row in rows if row.get("station_id") == "3011665"]
    target_rows = primary_rows or rows
    peak = max(target_rows, key=lambda row: float(row["water_level_m"]) if row.get("water_level_m") else -1)
    return {
        "source": "Flood Control Office water-level observation",
        "period": "2023-07-14 00:00 through 2023-07-17 00:00 KST",
        "records": len(rows),
        "peak_m": float(peak["water_level_m"]),
        "peak_timestamp": peak["timestamp_kst"],
        "peak_station_id": peak["station_id"],
        "peak_station_name": peak["station_name"],
    }


def main() -> None:
    dem = read_geojson(LOW_ELEVATION_FILE)
    rivers = read_geojson(RIVER_FILE)
    underpass = read_geojson(UNDERPASS_FILE)

    dem_features = []
    for feature in dem["features"]:
      geom = transform(TO_METERS, shape(feature["geometry"]))
      dem_features.append((feature, geom, geom.centroid))

    river_union = unary_union([transform(TO_METERS, shape(feature["geometry"])) for feature in rivers["features"]])
    underpass_union = unary_union([transform(TO_METERS, shape(feature["geometry"])) for feature in underpass["features"]])
    underpass_center = underpass_union.centroid
    breach_point = nearest_points(river_union, underpass_center)[0]
    flow_path = LineString([breach_point, underpass_center])

    elevations = sorted(float(feature["properties"].get("mean_elevation_m", 9999)) for feature, _, _ in dem_features)
    rainfall = peak_rainfall()
    water_level = peak_water_level()
    features = []
    stage_counts: dict[str, int] = {}

    for stage in EVENT_STAGES:
        if stage["stage_index"] == 0:
            stage_counts[stage["state"]] = 0
            continue
        max_rank_position = max(0, min(len(elevations) - 1, round((len(elevations) - 1) * stage["elevation_rank"])))
        max_elevation = elevations[max_rank_position]
        count = 0
        for source_feature, geom, centroid in dem_features:
            elevation = float(source_feature["properties"].get("mean_elevation_m", 9999))
            distance_to_river = centroid.distance(river_union)
            distance_to_underpass = centroid.distance(underpass_center)
            near_river = distance_to_river <= stage["river_distance_m"]
            near_underpass = stage["underpass_distance_m"] > 0 and distance_to_underpass <= stage["underpass_distance_m"]
            along_flow_path = centroid.distance(flow_path) <= max(stage["river_distance_m"] * 0.45, 160)
            if elevation <= max_elevation and (near_river or near_underpass or along_flow_path):
                properties = dict(source_feature["properties"])
                properties.update({
                    "layer_role": "approximate_flood_envelope",
                    "status": "TEMPORARY",
                    "source_type": "DERIVED_APPROXIMATION",
                    "stage_index": stage["stage_index"],
                    "time": stage["time"],
                    "state": stage["state"],
                    "label": stage["label"],
                    "basis": "KMA rainfall + Flood Control Office water level + Copernicus DEM low elevation + WAMIS river geometry + official incident timeline",
                    "not_official_flood_extent": True,
                    "not_hydraulic_simulation": True,
                    "distance_to_river_m": round(distance_to_river, 1),
                    "distance_to_underpass_m": round(distance_to_underpass, 1),
                    "rainfall_peak_mm_per_hour": rainfall["peak_mm_per_hour"],
                    "water_level_peak_m": water_level["peak_m"],
                })
                features.append({
                    "type": "Feature",
                    "properties": properties,
                    "geometry": source_feature["geometry"],
                })
                count += 1
        if stage["stage_index"] >= 3:
            features.append({
                "type": "Feature",
                "properties": {
                    "layer_role": "approximate_flow_path",
                    "status": "TEMPORARY",
                    "source_type": "DERIVED_APPROXIMATION",
                    "stage_index": stage["stage_index"],
                    "time": stage["time"],
                    "state": stage["state"],
                    "label": f"{stage['label']} flow direction context",
                    "basis": "Nearest WAMIS river point to Gungpyeong 2 Underpass, used only as directional context",
                    "not_official_flood_extent": True,
                    "not_hydraulic_simulation": True,
                },
                "geometry": mapping(transform(TO_WGS84, flow_path)),
            })
        stage_counts[stage["state"]] = count

    output = {
        "type": "FeatureCollection",
        "name": "osong_approx_flood_envelope_timeline",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "metadata": {
            "event_id": "osong-2023",
            "status": "TEMPORARY",
            "source_type": "DERIVED_APPROXIMATION",
            "role": "Historical reconstruction visualization only",
            "data_vintage": "2023-07-15 incident timeline with 2023-07-14 through 2023-07-17 observations",
            "method": "DEM low-elevation cells selected by stage thresholds using river proximity, underpass proximity, and directional flow context.",
            "limitations": [
                "Not an official flood extent.",
                "Not a 2D hydraulic simulation.",
                "No water depth, flow velocity, discharge, levee cross-section, or drainage structure is computed.",
                "Do not use for official exposure KPI counts.",
            ],
        },
        "features": features,
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_file": str(OUTPUT_FILE.relative_to(REPO_ROOT)),
        "status": "TEMPORARY",
        "source_type": "DERIVED_APPROXIMATION",
        "crs": "EPSG:4326 / CRS84",
        "geometry_types": sorted({feature["geometry"]["type"] for feature in features}),
        "feature_count": len(features),
        "stage_counts": stage_counts,
        "input_files": [
            str(LOW_ELEVATION_FILE.relative_to(REPO_ROOT)),
            str(RIVER_FILE.relative_to(REPO_ROOT)),
            str(UNDERPASS_FILE.relative_to(REPO_ROOT)),
            str(RAINFALL_FILE.relative_to(REPO_ROOT)),
            str(WATER_LEVEL_FILE.relative_to(REPO_ROOT)),
        ],
        "rainfall_context": rainfall,
        "water_level_context": water_level,
        "validity_assessment": {
            "appropriate_use": "Visual historical reconstruction and communication of plausible low-lying affected envelope by timeline stage.",
            "inappropriate_use": "Official flood extent, hydraulic simulation, depth/velocity estimate, or final exposure KPI.",
            "confidence": "LOW_TO_MEDIUM_FOR_SPATIAL_EXTENT; MEDIUM_FOR_EVENT_SEQUENCE_VISUALIZATION",
        },
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"output": str(OUTPUT_FILE), "feature_count": len(features), "stage_counts": stage_counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
