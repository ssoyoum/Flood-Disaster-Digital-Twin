"""Process manually acquired official Osong source data.

Raw files are preserved. This script creates AOI subsets, CRS-normalized
GeoJSON, building QA flags, rainfall normalized CSV, and a validation report.
"""

import csv
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pyogrio
from pyproj import Transformer
from shapely.geometry import box, shape


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed" / "osong"

AOI_WGS84 = box(127.27, 36.58, 127.40, 36.68)
OFFICIAL_CRS = "EPSG:5174"
ANALYSIS_CRS = "EPSG:4326"

BUILDING_ZIPS = {
    "chungbuk": RAW / "building_integrated" / "vworld_gis_building_integrated_2023-07-12_chungbuk" / "AL_43_D010_20230712.zip",
    "chungnam": RAW / "building_integrated" / "vworld_gis_building_integrated_2023-07-12_chungnam" / "AL_44_D010_20230712.zip",
}
OSM_BUILDINGS = PROCESSED / "osong_osm_buildings_2023.geojson"
KMA_RAINFALL = RAW / "rainfall" / "osong" / "OBS_AWS_TIM_20260830132752.csv"
VALIDATION_REPORT = PROCESSED / "validation_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def aoi_bbox_in(crs: str) -> tuple[float, float, float, float]:
    transformer = Transformer.from_crs(ANALYSIS_CRS, crs, always_xy=True)
    points = [transformer.transform(x, y) for x, y in AOI_WGS84.exterior.coords]
    return (
        min(x for x, _ in points),
        min(y for _, y in points),
        max(x for x, _ in points),
        max(y for _, y in points),
    )


def zip_shapefile_layers(path: Path) -> list[dict[str, Any]]:
    rows = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for layer_name, geometry_type in pyogrio.list_layers(path):
            dbf_name = f"{layer_name}.dbf"
            if dbf_name not in names:
                continue
            header = archive.read(dbf_name)[:32]
            record_count = int.from_bytes(header[4:8], byteorder="little", signed=False)
            rows.append({"layer_name": layer_name, "geometry_type": geometry_type, "record_count": record_count})
    return rows


def read_official_subset() -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    bbox5174 = aoi_bbox_in(OFFICIAL_CRS)
    subsets = []
    source_stats: dict[str, Any] = {}
    aoi5174 = gpd.GeoSeries([AOI_WGS84], crs=ANALYSIS_CRS).to_crs(OFFICIAL_CRS).iloc[0]

    for region, path in BUILDING_ZIPS.items():
        source_stats[region] = {
            "raw_file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "raw_size_bytes": path.stat().st_size,
            "raw_sha256": sha256(path),
            "raw_layers": zip_shapefile_layers(path),
        }
        layers = [item["layer_name"] for item in source_stats[region]["raw_layers"]]
        region_parts = []
        for layer in layers:
            gdf = gpd.read_file(path, layer=layer, bbox=bbox5174)
            if gdf.empty:
                continue
            if gdf.crs is None:
                gdf = gdf.set_crs(OFFICIAL_CRS)
            gdf = gdf[gdf.geometry.notna()].copy()
            gdf = gdf[gdf.geometry.intersects(aoi5174)].copy()
            if gdf.empty:
                continue
            gdf["source_region"] = region
            gdf["source_layer"] = layer
            region_parts.append(gdf)

        if region_parts:
            region_subset = pd.concat(region_parts, ignore_index=True)
            source_stats[region]["subset_feature_count"] = len(region_subset)
            subsets.append(region_subset)
        else:
            source_stats[region]["subset_feature_count"] = 0

    if subsets:
        official = gpd.GeoDataFrame(pd.concat(subsets, ignore_index=True), geometry="geometry", crs=OFFICIAL_CRS)
    else:
        official = gpd.GeoDataFrame(geometry=[], crs=OFFICIAL_CRS)

    official = official.reset_index(drop=True)
    official["official_feature_id"] = official.index.map(lambda value: f"official-building-{value + 1}")
    official["source_name"] = "MOLIT/VWorld GIS Building Integrated Information"
    official["data_vintage"] = "2023-07-12"
    official["qa_source"] = "OFFICIAL"
    return official, source_stats


def make_building_outputs(official5174: gpd.GeoDataFrame) -> dict[str, Any]:
    official4326 = official5174.to_crs(ANALYSIS_CRS)
    official4326.to_file(PROCESSED / "osong_official_buildings_2023.geojson", driver="GeoJSON")

    osm4326 = gpd.read_file(OSM_BUILDINGS)
    if osm4326.crs is None:
        osm4326 = osm4326.set_crs(ANALYSIS_CRS)
    osm4326 = osm4326[osm4326.geometry.notna()].copy()
    osm4326["qa_source"] = "OSM"
    osm4326["source_name"] = "OpenStreetMap Overpass attic"
    osm4326["data_vintage"] = "2023-07-15T23:59:59Z"

    official_match = gpd.sjoin(
        official5174[["official_feature_id", "geometry"]],
        osm4326.to_crs(OFFICIAL_CRS)[["osm_id", "geometry"]],
        how="left",
        predicate="intersects",
    )
    matched_official_ids = set(official_match.loc[official_match["osm_id"].notna(), "official_feature_id"])

    osm_match = gpd.sjoin(
        osm4326.to_crs(OFFICIAL_CRS)[["osm_id", "geometry"]],
        official5174[["official_feature_id", "geometry"]],
        how="left",
        predicate="intersects",
    )
    matched_osm_ids = set(osm_match.loc[osm_match["official_feature_id"].notna(), "osm_id"])

    official_qa = official4326.copy()
    official_qa["qa_flag"] = official_qa["official_feature_id"].map(lambda value: "MATCHED" if value in matched_official_ids else "OFFICIAL_ONLY")

    osm_only = osm4326[~osm4326["osm_id"].isin(matched_osm_ids)].copy()
    osm_only["official_feature_id"] = None
    osm_only["qa_flag"] = "OSM_ONLY"

    common_columns = sorted(set(official_qa.columns).union(osm_only.columns) - {"geometry"})
    official_qa = official_qa.reindex(columns=common_columns + ["geometry"])
    osm_only = osm_only.reindex(columns=common_columns + ["geometry"])
    qa = gpd.GeoDataFrame(pd.concat([official_qa, osm_only], ignore_index=True), geometry="geometry", crs=ANALYSIS_CRS)
    qa.to_file(PROCESSED / "osong_building_qa_official_osm_2023.geojson", driver="GeoJSON")

    summary = {
        "official_subset_feature_count": int(len(official_qa)),
        "osm_2023_feature_count": int(len(osm4326)),
        "matched_official_feature_count": int(len(matched_official_ids)),
        "official_only_feature_count": int(len(official_qa) - len(matched_official_ids)),
        "osm_only_feature_count": int(len(osm_only)),
        "matching_method": "geometry intersects after projecting both layers to EPSG:5174",
        "merge_policy": "OSM-only footprints are not added to the authoritative official layer.",
        "qa_flags": ["MATCHED", "OFFICIAL_ONLY", "OSM_ONLY"],
    }
    (PROCESSED / "osong_building_qa_summary_2023.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def process_rainfall() -> dict[str, Any]:
    raw_bytes = KMA_RAINFALL.read_bytes()
    rows = list(csv.DictReader(raw_bytes.decode("cp949").splitlines()))
    output = PROCESSED / "osong_kma_aws_rainfall_2023-07-14_17.csv"
    fields = ["station_id", "station_name", "timestamp_kst", "rainfall_mm", "temperature_c", "wind_direction_deg", "wind_speed_mps", "humidity_percent", "source", "source_type", "data_status"]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "station_id": row["지점"],
                    "station_name": row["지점명"],
                    "timestamp_kst": row["일시"],
                    "rainfall_mm": row["강수량(mm)"],
                    "temperature_c": row["기온(°C)"],
                    "wind_direction_deg": row["풍향(deg)"],
                    "wind_speed_mps": row["풍속(m/s)"],
                    "humidity_percent": row["습도(%)"],
                    "source": "KMA AWS/ASOS",
                    "source_type": "OBSERVATION",
                    "data_status": "VERIFIED",
                }
            )

    station_totals = {}
    for station in sorted({(row["지점"], row["지점명"]) for row in rows}):
        station_rows = [row for row in rows if row["지점"] == station[0]]
        station_totals[f"{station[0]}:{station[1]}"] = {
            "record_count": len(station_rows),
            "rainfall_total_mm": sum(float(row["강수량(mm)"] or 0) for row in station_rows),
        }

    return {
        "raw_file": str(KMA_RAINFALL.relative_to(ROOT)).replace("\\", "/"),
        "raw_size_bytes": KMA_RAINFALL.stat().st_size,
        "raw_sha256": sha256(KMA_RAINFALL),
        "processed_file": str(output.relative_to(ROOT)).replace("\\", "/"),
        "processed_sha256": sha256(output),
        "record_count": len(rows),
        "period_start": min(row["일시"] for row in rows),
        "period_end": max(row["일시"] for row in rows),
        "unit": "mm",
        "stations": station_totals,
    }


def update_validation_report(source_stats: dict[str, Any], qa_summary: dict[str, Any], rainfall: dict[str, Any]) -> None:
    if VALIDATION_REPORT.exists():
        report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    else:
        report = {"aoi": [127.27, 36.58, 127.40, 36.68], "crs": ANALYSIS_CRS, "result": {}}

    report["official_buildings_2023"] = {
        "source_stats": source_stats,
        "processed_file": "data/processed/osong/osong_official_buildings_2023.geojson",
        "qa_file": "data/processed/osong/osong_building_qa_official_osm_2023.geojson",
        "qa_summary_file": "data/processed/osong/osong_building_qa_summary_2023.json",
        "qa_summary": qa_summary,
        "crs": ANALYSIS_CRS,
        "validation": "official SHP subset converted to EPSG:4326 and intersect-matched with OSM 2023 footprints",
    }
    report["kma_aws_rainfall_2023"] = rainfall
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    official, source_stats = read_official_subset()
    if official.empty:
        raise ValueError("No official building features intersect Osong AOI")
    qa_summary = make_building_outputs(official)
    rainfall = process_rainfall()
    update_validation_report(source_stats, qa_summary, rainfall)
    print(json.dumps({"official_buildings": qa_summary, "rainfall": rainfall}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
