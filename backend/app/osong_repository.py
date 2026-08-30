import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}


def _read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _feature_count(data: dict[str, Any]) -> int:
    return len(data.get("features", []))


def _geometry_types(data: dict[str, Any]) -> list[str]:
    return sorted({feature.get("geometry", {}).get("type", "Unknown") for feature in data.get("features", [])})


def _layer(
    key: str,
    label: str,
    path: Path,
    *,
    status: str,
    source_type: str,
    source: str,
    snapshot: str | None = None,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "key": key,
            "label": label,
            "status": "UNAVAILABLE",
            "source_type": source_type,
            "source": source,
            "snapshot": snapshot,
            "path": str(path.relative_to(REPO_ROOT)),
            "feature_count": 0,
            "geometry_types": [],
            "data": EMPTY_FEATURE_COLLECTION,
        }

    data = _read_geojson(path)
    return {
        "key": key,
        "label": label,
        "status": status,
        "source_type": source_type,
        "source": source,
        "snapshot": snapshot,
        "path": str(path.relative_to(REPO_ROOT)),
        "feature_count": _feature_count(data),
        "geometry_types": _geometry_types(data),
        "data": data,
    }


def _read_population(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "UNAVAILABLE",
            "source": "KOSIS official eup/myeon/dong population",
            "data_year": 2023,
            "unit": "person",
            "records": 0,
            "osong_population": None,
            "path": str(path.relative_to(REPO_ROOT)),
        }

    records: list[list[str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            records.append(row)

    osong_rows = [
        row
        for row in records
        if len(row) >= 6 and row[0].lstrip("'") == "4311325000" and row[2].lstrip("'") == "0"
    ]
    latest = sorted(osong_rows, key=lambda row: row[4])[-1] if osong_rows else None
    population = int(float(latest[5])) if latest else None
    period = None
    if osong_rows:
        points = sorted(row[4] for row in osong_rows)
        period = f"{points[0]} through {points[-1]}"

    return {
        "status": "VERIFIED",
        "source": "KOSIS official eup/myeon/dong population",
        "source_type": "OFFICIAL_STATISTICS",
        "data_year": 2023,
        "period": period,
        "unit": "person",
        "records": len(records),
        "administrative_unit": "오송읍",
        "osong_population": population,
        "path": str(path.relative_to(REPO_ROOT)),
    }


def _read_rainfall(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "UNAVAILABLE",
            "source": "NASA POWER",
            "source_type": "REANALYSIS",
            "records": 0,
            "path": str(path.relative_to(REPO_ROOT)),
        }

    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = [float(row["precipitation_mm_per_hour"]) for row in rows if row.get("precipitation_mm_per_hour")]
    return {
        "status": "DERIVED",
        "source": "NASA POWER hourly reanalysis converted to project CSV",
        "source_type": "REANALYSIS",
        "parameter": "PRECTOTCORR",
        "period": "2023-07-15 through 2023-07-16",
        "unit": "mm/hour",
        "records": len(rows),
        "max_mm_per_hour": max(values) if values else None,
        "path": str(path.relative_to(REPO_ROOT)),
    }


def _read_kma_rainfall(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _read_rainfall(OSONG_DIR / "osong_nasa_power_precip_2023-07-15_16.csv")

    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = [float(row["rainfall_mm"]) for row in rows if row.get("rainfall_mm")]
    stations: dict[str, dict[str, Any]] = {}
    for row in rows:
        station_id = row.get("station_id")
        station_name = row.get("station_name")
        rainfall = float(row["rainfall_mm"]) if row.get("rainfall_mm") else 0.0
        if not station_id:
            continue
        station = stations.setdefault(
            station_id,
            {"station_id": station_id, "station_name": station_name, "records": 0, "rainfall_total_mm": 0.0},
        )
        station["records"] += 1
        station["rainfall_total_mm"] += rainfall
    for station in stations.values():
        station["rainfall_total_mm"] = round(station["rainfall_total_mm"], 1)
    return {
        "status": "VERIFIED",
        "source": "KMA AWS/ASOS rainfall observation",
        "source_type": "OBSERVATION",
        "parameter": "rainfall_mm",
        "period": "2023-07-14 01:00 through 2023-07-17 00:00 KST",
        "unit": "mm",
        "records": len(rows),
        "max_mm_per_hour": max(values) if values else None,
        "stations": list(stations.values()),
        "path": str(path.relative_to(REPO_ROOT)),
    }


def get_osong_observations() -> list[dict[str, Any]]:
    path = OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    observations = []
    for row in rows:
        if not row.get("rainfall_mm"):
            continue
        observations.append(
            {
                "timestamp": row["timestamp_kst"].replace(" ", "T") + "+09:00",
                "observation_type": "rainfall",
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "value": float(row["rainfall_mm"]),
                "unit": "mm",
                "quality_flag": "VERIFIED_OBSERVATION",
                "origin": "VERIFIED",
            }
        )
    return observations


def _read_dem_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "UNAVAILABLE",
            "source": "Copernicus DEM GLO-30",
            "source_type": "DEM",
            "role": "Terrain context only",
            "path": str(path.relative_to(REPO_ROOT)),
        }
    summary = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": "DERIVED",
        "source": "Copernicus DEM GLO-30",
        "source_type": "DEM",
        "role": "Terrain context only",
        "data_year": None,
        "period": "TanDEM-X acquisition 2011-2015; Copernicus object modified 2022-05-09",
        "min_elevation_m": round(float(summary["min_elevation_m"]), 2),
        "max_elevation_m": round(float(summary["max_elevation_m"]), 2),
        "mean_elevation_m": round(float(summary["mean_elevation_m"]), 2),
        "low_elevation_threshold_m": round(float(summary["low_elevation_threshold_m"]), 2),
        "grid_feature_count": summary["grid_feature_count"],
        "low_elevation_feature_count": summary["low_elevation_feature_count"],
        "path": str(path.relative_to(REPO_ROOT)),
    }


def _osm_snapshot(year: int) -> str:
    return "2023-07-15T23:59:59Z" if year == 2023 else "2026-08-30"


def _osm_path(name: str, year: int) -> Path:
    return OSONG_DIR / f"osong_osm_{name}_{year}.geojson"


@lru_cache(maxsize=1)
def get_osong_repository(layer_year: int = 2023) -> dict[str, Any]:
    if layer_year != 2023:
        layer_year = 2023
    osm_snapshot = _osm_snapshot(layer_year)
    layers = {
        "aoi": _layer(
            "aoi",
            "AOI administrative boundary",
            OSONG_DIR / "osong_geoboundaries_adm2_aoi.geojson",
            status="VERIFIED",
            source_type="BOUNDARY_SNAPSHOT",
            source="geoBoundaries ADM2 snapshot",
            snapshot="2020",
        ),
        "buildings": _layer(
            "buildings",
            "Official GIS Building Integrated Information 2023",
            OSONG_DIR / "osong_official_buildings_2023.geojson",
            status="VERIFIED",
            source_type="OFFICIAL_BUILDING_INTEGRATED_INFORMATION",
            source="MOLIT/VWorld GIS Building Integrated Information",
            snapshot="2023-07-12",
        ),
        "roads": _layer(
            "roads",
            f"OSM Roads {layer_year}",
            _osm_path("roads", layer_year),
            status="VERIFIED",
            source_type="OSM_HISTORICAL_SNAPSHOT",
            source="OpenStreetMap Overpass attic",
            snapshot=osm_snapshot,
        ),
        "waterways": _layer(
            "waterways",
            "WAMIS National/Local Rivers",
            OSONG_DIR / "osong_wamis_rivers.geojson",
            status="VERIFIED",
            source_type="OFFICIAL_RIVER_NETWORK",
            source="WAMIS national/local river network SHP",
            snapshot="NOT RECORDED",
        ),
        "terrain": _layer(
            "terrain",
            "DEM Low-Elevation Context",
            OSONG_DIR / "osong_dem_low_elevation_context.geojson",
            status="DERIVED",
            source_type="DEM_TERRAIN_CONTEXT",
            source="Copernicus DEM GLO-30 derived low-elevation context",
            snapshot="2011-2015 acquisition; object modified 2022-05-09",
        ),
        "facilities": _layer(
            "facilities",
            f"OSM Facilities {layer_year}",
            _osm_path("facilities", layer_year),
            status="VERIFIED",
            source_type="OSM_HISTORICAL_SNAPSHOT",
            source="OpenStreetMap Overpass attic",
            snapshot=osm_snapshot,
        ),
        "underpass": _layer(
            "underpass",
            "Gungpyeong 2 Underpass",
            OSONG_DIR / "gungpyeong2_underpass.geojson",
            status="DERIVED",
            source_type="OFFICIAL_METADATA_WITH_OSM_GEOMETRY",
            source="Chungcheongbuk-do/MOLIT metadata joined with OSM tunnel geometry",
            snapshot="2023-07-15T23:59:59Z",
        ),
        "flood_extent": {
            "key": "flood_extent",
            "label": "Flood Extent",
            "status": "TEMPORARY",
            "source_type": "AWAITING_OFFICIAL_DATASET",
            "source": "MOIS DSSP-IF-00117 approval pending",
            "snapshot": None,
            "path": None,
            "feature_count": 0,
            "geometry_types": [],
            "data": EMPTY_FEATURE_COLLECTION,
        },
    }

    population = _read_population(OSONG_DIR / "osong_official_population_2023.csv")
    rainfall = _read_kma_rainfall(OSONG_DIR / "osong_kma_aws_rainfall_2023-07-14_17.csv")
    dem = _read_dem_summary(OSONG_DIR / "osong_dem_summary.json")

    return {
        "event": {
            "id": "osong-2023",
            "name": "2023 Osong Underpass Flood",
            "location": "Osong-eup, Cheongju, Chungcheongbuk-do",
            "data_year": 2023,
            "theme": "River + Transport",
            "focus_feature": "Gungpyeong 2 Underpass",
            "analysis_flow": "Miho River levee breach -> overflow -> underpass inundation -> vehicles and road users",
            "source": "Processed local Osong datasets; official flood extent pending",
            "started_at": "2023-07-15T00:00:00+09:00",
            "ended_at": "2023-07-16T00:00:00+09:00",
            "origin": "DERIVED",
            "data_status": "Offline MVP using local processed Osong data. Flood Extent is TEMPORARY until official MOIS DSSP-IF-00117 data is approved.",
            "event_year": 2023,
            "boundary_snapshot": "geoBoundaries ADM2 snapshot: 2020",
            "flood_extent": layers["flood_extent"]["data"],
        },
        "layers": layers,
        "population": population,
        "rainfall": rainfall,
        "dem": dem,
        "data_status": {
            "flood_extent": layers["flood_extent"],
            "population": population,
            "rainfall": rainfall,
            "dem": dem,
            "layers": {key: {k: value for k, value in layer.items() if k != "data"} for key, layer in layers.items()},
        },
    }


def get_osong_event() -> dict[str, Any]:
    return dict(get_osong_repository()["event"])


def get_osong_layers(layer_year: int = 2023) -> dict[str, Any]:
    return get_osong_repository(layer_year)["layers"]


def get_osong_data_status() -> dict[str, Any]:
    return get_osong_repository()["data_status"]


def get_osong_summary() -> dict[str, Any]:
    repo = get_osong_repository()
    layers = repo["layers"]
    return {
        "event_id": "osong-2023",
        "origin": "DERIVED",
        "official_population": repo["population"]["osong_population"],
        "official_population_unit": repo["population"]["unit"],
        "building_count": layers["buildings"]["feature_count"],
        "road_count": layers["roads"]["feature_count"],
        "waterway_count": layers["waterways"]["feature_count"],
        "terrain_low_elevation_cells": layers["terrain"]["feature_count"],
        "terrain_low_elevation_threshold_m": repo["dem"].get("low_elevation_threshold_m"),
        "rainfall_peak_mm_per_hour": repo["rainfall"].get("max_mm_per_hour"),
        "rainfall_records": repo["rainfall"].get("records"),
        "facility_count": layers["facilities"]["feature_count"],
        "underpass_available": layers["underpass"]["feature_count"] > 0,
        "flooded_area_km2": "PENDING_FLOOD_EXTENT",
        "exposed_population": "PENDING_FLOOD_EXTENT",
        "exposed_buildings": "PENDING_FLOOD_EXTENT",
        "affected_road_length_km": "PENDING_FLOOD_EXTENT",
        "critical_infrastructure": "PENDING_FLOOD_EXTENT",
        "affected_shelters": "PENDING_FLOOD_EXTENT",
        "data_status": "Flood Extent unavailable; exposure KPIs are intentionally not calculated.",
    }
