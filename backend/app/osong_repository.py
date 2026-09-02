import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OSONG_DIR = REPO_ROOT / "data" / "processed" / "osong"
SAFEMAP_WMS_SNAPSHOT = REPO_ROOT / "data" / "raw" / "flood_extent" / "osong" / "safemap_if_0092_wms" / "osong_bbox_4326_layers.png"
SAFEMAP_WMS_BBOX = [127.275, 36.58, 127.365, 36.67]

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}

OSONG_RECONSTRUCTION_EVENTS = [
    {
        "time": "2023-07-15T04:10:00+09:00",
        "label": "Flood warning",
        "state": "warning",
        "description": "Flood warning issued before the underpass inundation sequence.",
        "source": "Official incident timeline; source-page evidence pending",
        "role": "Incident Record",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T06:40:00+09:00",
        "label": "Miho River design flood level reached",
        "state": "hydraulic_warning",
        "description": "Miho River bridge water level reached the reported design flood level of 29.02 m.",
        "source": "Official incident timeline + HRFCO observation context; source-page evidence pending",
        "role": "Hydromet Threshold",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T07:50:00+09:00",
        "label": "Overtopping begins",
        "state": "overtopping",
        "description": "Reported overflow near the temporary levee before structural failure.",
        "source": "Official incident timeline; source-page evidence pending",
        "role": "Incident Record",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T08:09:00+09:00",
        "label": "Temporary levee failure",
        "state": "levee_failure",
        "description": "Temporary levee failure is treated as the baseline simulation event that changes the underpass risk state.",
        "source": "Official incident timeline; source-page evidence pending",
        "role": "Baseline Event",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T08:27:00+09:00",
        "label": "Underpass inflow starts",
        "state": "underpass_inflow",
        "description": "Water inflow into Gungpyeong 2 Underpass begins; rule-based auto-closure scenario activates here.",
        "source": "Official incident timeline / CCTV-derived timing; source-page evidence pending",
        "role": "Validation Target",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T08:35:00+09:00",
        "label": "Unsafe driving condition",
        "state": "unsafe_driving",
        "description": "The underpass is treated as unsafe for vehicle passage.",
        "source": "Official incident timeline / CCTV-derived timing; source-page evidence pending",
        "role": "Validation Target",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
    {
        "time": "2023-07-15T08:40:00+09:00",
        "label": "Full inundation",
        "state": "full_inundation",
        "description": "The underpass reaches full inundation in the baseline sequence.",
        "source": "Official incident timeline / CCTV-derived timing; source-page evidence pending",
        "role": "Validation Target",
        "confidence": "NEEDS_SOURCE_PAGE",
    },
]


def _minutes_between(start: str, end: str) -> int:
    from datetime import datetime

    return int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() // 60)


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
    peak_row = max(rows, key=lambda row: float(row["rainfall_mm"]) if row.get("rainfall_mm") else -1) if rows else None
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
        "peak_timestamp": peak_row["timestamp_kst"] if peak_row else None,
        "peak_station_id": peak_row["station_id"] if peak_row else None,
        "peak_station_name": peak_row["station_name"] if peak_row else None,
        "stations": list(stations.values()),
        "path": str(path.relative_to(REPO_ROOT)),
    }


def _read_water_level(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "UNAVAILABLE",
            "source": "Flood Control Office water-level observation",
            "source_type": "OBSERVATION",
            "records": 0,
            "path": str(path.relative_to(REPO_ROOT)),
        }

    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = [float(row["water_level_m"]) for row in rows if row.get("water_level_m")]
    peak_row = max(rows, key=lambda row: float(row["water_level_m"]) if row.get("water_level_m") else -1) if rows else None
    stations: dict[str, dict[str, Any]] = {}
    for row in rows:
        station_id = row.get("station_id")
        if not station_id:
            continue
        station = stations.setdefault(
            station_id,
            {
                "station_id": station_id,
                "station_name": row.get("station_name"),
                "records": 0,
                "max_water_level_m": None,
                "peak_timestamp": None,
            },
        )
        station["records"] += 1
        if row.get("water_level_m"):
            value = float(row["water_level_m"])
            if station["max_water_level_m"] is None or value > station["max_water_level_m"]:
                station["max_water_level_m"] = value
                station["peak_timestamp"] = row.get("timestamp_kst")
    return {
        "status": "VERIFIED",
        "source": "Flood Control Office water-level observation",
        "source_type": "OBSERVATION",
        "parameter": "water_level_m",
        "period": "2023-07-14 00:00 through 2023-07-17 00:00 KST",
        "unit": "m",
        "records": len(rows),
        "max_water_level_m": max(values) if values else None,
        "peak_timestamp": peak_row["timestamp_kst"] if peak_row else None,
        "peak_station_id": peak_row["station_id"] if peak_row else None,
        "peak_station_name": peak_row["station_name"] if peak_row else None,
        "stations": list(stations.values()),
        "path": str(path.relative_to(REPO_ROOT)),
    }


def _build_hydromet_analysis(rainfall: dict[str, Any], water_level: dict[str, Any], dem: dict[str, Any], safemap: dict[str, Any]) -> dict[str, Any]:
    rainfall_stations = rainfall.get("stations") or []
    primary_water_station = next(
        (station for station in water_level.get("stations") or [] if station.get("station_id") == "3011665"),
        None,
    )
    max_rainfall_total = max((station.get("rainfall_total_mm", 0) for station in rainfall_stations), default=None)
    return {
        "title": "Observed rainfall and Miho River water-level context",
        "status": "READY_WITH_RASTER_FLOODMARKS",
        "summary": [
            "KMA AWS rainfall and Flood Control Office water-level observations are connected for the 2023-07-14 to 2023-07-17 event window.",
            "Safemap flood marks are visible as an official WMS raster overlay, but vector Flood Extent remains pending.",
            "Exposure counts stay locked because the WMS snapshot is not final vector geometry.",
        ],
        "rainfall": {
            "source": rainfall.get("source"),
            "period": rainfall.get("period"),
            "station_count": len(rainfall_stations),
            "records": rainfall.get("records"),
            "peak_mm_per_hour": rainfall.get("max_mm_per_hour"),
            "peak_timestamp": rainfall.get("peak_timestamp"),
            "peak_station_name": rainfall.get("peak_station_name"),
            "max_station_total_mm": max_rainfall_total,
            "stations": rainfall_stations,
        },
        "water_level": {
            "source": water_level.get("source"),
            "period": water_level.get("period"),
            "station_count": len(water_level.get("stations") or []),
            "records": water_level.get("records"),
            "peak_m": water_level.get("max_water_level_m"),
            "peak_timestamp": water_level.get("peak_timestamp"),
            "peak_station_name": water_level.get("peak_station_name"),
            "primary_station_peak_m": primary_water_station.get("max_water_level_m") if primary_water_station else None,
            "primary_station_peak_timestamp": primary_water_station.get("peak_timestamp") if primary_water_station else None,
        },
        "terrain": {
            "low_elevation_threshold_m": dem.get("low_elevation_threshold_m"),
            "low_elevation_feature_count": dem.get("low_elevation_feature_count"),
        },
        "floodmarks": {
            "source": safemap.get("source"),
            "data_vintage": safemap.get("data_vintage"),
            "status": safemap.get("status"),
            "usage": "visual verification only",
        },
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


def _read_envelope_comparison(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "status": "UNAVAILABLE",
            "source_type": "DERIVED_COMPARISON",
            "role": "Compare approximate envelope methods.",
            "rows": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def get_safemap_floodmarks_overlay() -> dict[str, Any]:
    if not SAFEMAP_WMS_SNAPSHOT.exists():
        return {
            "key": "safemap_floodmarks",
            "label": "Safemap Flood Marks WMS Snapshot",
            "status": "UNAVAILABLE",
            "source_type": "OFFICIAL_WMS_SNAPSHOT",
            "source": "MOIS Safemap IF_0092_WMS",
            "snapshot": "NOT RECORDED",
            "data_vintage": "2024 collection",
            "role": "Hazard Layer / visual verification only",
            "path": str(SAFEMAP_WMS_SNAPSHOT.relative_to(REPO_ROOT)),
            "bbox": SAFEMAP_WMS_BBOX,
            "image_url": None,
            "notes": "Safemap WMS snapshot is not vector geometry; do not use it for final exposure counts without vectorization or official vector data.",
        }
    return {
        "key": "safemap_floodmarks",
        "label": "Safemap Flood Marks WMS Snapshot",
        "status": "VERIFIED",
        "source_type": "OFFICIAL_WMS_SNAPSHOT",
        "source": "MOIS Safemap IF_0092_WMS",
        "snapshot": "2026-08-31 request snapshot; source page collection year 2024",
        "data_vintage": "2024 collection",
        "role": "Hazard Layer / visual verification only",
        "path": str(SAFEMAP_WMS_SNAPSHOT.relative_to(REPO_ROOT)),
        "bbox": SAFEMAP_WMS_BBOX,
        "image_url": "/api/events/osong-2023/flood/safemap-wms-snapshot.png",
        "image_size_bytes": SAFEMAP_WMS_SNAPSHOT.stat().st_size,
        "notes": "Safemap WMS snapshot is not vector geometry; do not use it for final exposure counts without vectorization or official vector data.",
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
            "Osong-eup administrative boundary",
            OSONG_DIR / "osong_sgis_admin_boundary_2023.geojson",
            status="VERIFIED",
            source_type="OFFICIAL_ADMIN_BOUNDARY",
            source="SGIS OpenAPI administrative boundary",
            snapshot="2023",
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
        "approx_flood_envelope": _layer(
            "approx_flood_envelope",
            "Approximate Flood Envelope Timeline",
            OSONG_DIR / "osong_approx_flood_envelope_timeline.geojson",
            status="TEMPORARY",
            source_type="DERIVED_APPROXIMATION",
            source="KMA rainfall + Flood Control Office water level + Copernicus DEM + WAMIS river geometry + incident timeline",
            snapshot="2023-07-15 incident timeline with 2023-07-14 through 2023-07-17 observations",
        ),
        "hand_reconstruction": _layer(
            "hand_reconstruction",
            "HAND Reconstruction Timeline",
            OSONG_DIR / "osong_hand_flood_envelope_timeline.geojson",
            status="TEMPORARY",
            source_type="DERIVED_APPROXIMATION",
            source="HAND-like relative elevation + WAMIS drainage connectivity + observed water-level rise + incident timeline",
            snapshot="2023-07-15 incident timeline with 2023-07-14 through 2023-07-17 observations",
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
    water_level = _read_water_level(OSONG_DIR / "osong_hrfco_water_level_10m_2023-07-14_17.csv")
    dem = _read_dem_summary(OSONG_DIR / "osong_dem_summary.json")
    safemap_floodmarks = get_safemap_floodmarks_overlay()
    analysis = _build_hydromet_analysis(rainfall, water_level, dem, safemap_floodmarks)

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
            "boundary_snapshot": "SGIS administrative boundary snapshot: 2023",
            "flood_extent": layers["flood_extent"]["data"],
        },
        "layers": layers,
        "population": population,
        "rainfall": rainfall,
        "water_level": water_level,
        "dem": dem,
        "safemap_floodmarks": safemap_floodmarks,
        "analysis": analysis,
        "data_status": {
            "flood_extent": layers["flood_extent"],
            "safemap_floodmarks": safemap_floodmarks,
            "population": population,
            "rainfall": rainfall,
            "water_level": water_level,
            "dem": dem,
            "analysis": analysis,
            "layers": {key: {k: value for k, value in layer.items() if k != "data"} for key, layer in layers.items()},
        },
    }


def get_osong_event() -> dict[str, Any]:
    return dict(get_osong_repository()["event"])


def get_osong_layers(layer_year: int = 2023) -> dict[str, Any]:
    return get_osong_repository(layer_year)["layers"]


def get_osong_data_status() -> dict[str, Any]:
    return get_osong_repository()["data_status"]


def get_osong_reconstruction() -> dict[str, Any]:
    repo = get_osong_repository()
    events = OSONG_RECONSTRUCTION_EVENTS
    by_state = {event["state"]: event for event in events}
    inflow_time = by_state["underpass_inflow"]["time"]
    unsafe_time = by_state["unsafe_driving"]["time"]
    full_time = by_state["full_inundation"]["time"]
    levee_failure_time = by_state["levee_failure"]["time"]
    response_window_min = _minutes_between(inflow_time, unsafe_time)
    full_inundation_window_min = _minutes_between(inflow_time, full_time)
    failure_to_inflow_min = _minutes_between(levee_failure_time, inflow_time)
    envelope_comparison = _read_envelope_comparison(OSONG_DIR / "osong_reconstruction_envelope_comparison.json")

    return {
        "event_id": "osong-2023",
        "title": "2023 Osong observed event reconstruction",
        "model_type": "Historical Disaster Reconstruction Digital Twin MVP",
        "event_year": 2023,
        "status": "READY_FOR_RULE_BASED_REPLAY",
        "replay": events,
        "baseline": {
            "name": "Baseline: 2023 observed incident sequence",
            "description": "Observed rainfall, water-level context, and official incident timing are replayed as a rule-based state sequence.",
            "states": [
                {"state": "warning", "time": by_state["warning"]["time"], "underpass_status": "open", "risk": "elevated"},
                {"state": "levee_failure", "time": levee_failure_time, "underpass_status": "open", "risk": "critical"},
                {"state": "underpass_inflow", "time": inflow_time, "underpass_status": "open", "risk": "life_safety_threat"},
                {"state": "unsafe_driving", "time": unsafe_time, "underpass_status": "unsafe", "risk": "vehicle_passage_not_viable"},
                {"state": "full_inundation", "time": full_time, "underpass_status": "inundated", "risk": "complete_loss_of_service"},
            ],
            "failure_to_inflow_min": failure_to_inflow_min,
            "inflow_to_unsafe_min": response_window_min,
            "inflow_to_full_inundation_min": full_inundation_window_min,
        },
        "intervention": {
            "name": "Scenario A: water-depth sensor + automatic entrance closure",
            "type": "ROAD_CLOSURE",
            "trigger": "underpass_water_depth >= 0.15 m",
            "trigger_time": inflow_time,
            "trigger_basis": "Scenario rule based on post-incident automatic closure concept; not hydraulically simulated.",
            "closure_action": "Close underpass entrances and block new vehicle entry.",
            "estimated_effect": "Prevents additional entry after detected inflow; does not estimate vehicles already inside.",
            "available_response_window_min": response_window_min,
            "time_until_full_inundation_min": full_inundation_window_min,
            "result_status": "RULE_BASED_INTERVENTION",
        },
        "provenance": [
            {
                "source": repo["rainfall"].get("source"),
                "data_vintage": repo["rainfall"].get("period"),
                "role": "Observed Input",
                "status": repo["rainfall"].get("status"),
            },
            {
                "source": repo["water_level"].get("source"),
                "data_vintage": repo["water_level"].get("period"),
                "role": "Observed Input",
                "status": repo["water_level"].get("status"),
            },
            {
                "source": "Official incident timeline / CCTV-derived timing",
                "data_vintage": "2023-07-15; source-page evidence pending",
                "role": "Incident State Validation",
                "status": "TEMPORARY",
            },
            {
                "source": repo["layers"]["approx_flood_envelope"].get("source"),
                "data_vintage": repo["layers"]["approx_flood_envelope"].get("snapshot"),
                "role": "Approximate visualization envelope",
                "status": repo["layers"]["approx_flood_envelope"].get("status"),
            },
            {
                "source": repo["layers"]["hand_reconstruction"].get("source"),
                "data_vintage": repo["layers"]["hand_reconstruction"].get("snapshot"),
                "role": "HAND-based reconstruction envelope",
                "status": repo["layers"]["hand_reconstruction"].get("status"),
            },
            {
                "source": repo["layers"]["underpass"].get("source"),
                "data_vintage": repo["layers"]["underpass"].get("snapshot"),
                "role": "Transport Facility Geometry",
                "status": repo["layers"]["underpass"].get("status"),
            },
            {
                "source": repo["safemap_floodmarks"].get("source"),
                "data_vintage": repo["safemap_floodmarks"].get("data_vintage"),
                "role": "Visual verification only",
                "status": repo["safemap_floodmarks"].get("status"),
            },
        ],
        "envelope_comparison": envelope_comparison,
        "limitations": [
            "This MVP reconstructs the observed event timeline and intervention window; it is not a calibrated 2D hydraulic model.",
            "Underpass water depth is not computed from hydraulics. The 15 cm threshold is represented as a rule-based intervention trigger.",
            "Approximate flood envelope is a temporary DEM-constrained visualization layer, not official Flood Extent or a hydraulic simulation.",
            "Flood Extent and exposure counts remain PENDING_FLOOD_EXTENT until verified vector flood geometry or calibrated simulation output is available.",
            "CCTV-derived inundation timestamps still need explicit source-page evidence in the manifest.",
        ],
    }


def get_osong_summary() -> dict[str, Any]:
    repo = get_osong_repository()
    layers = repo["layers"]
    reconstruction = get_osong_reconstruction()
    return {
        "event_id": "osong-2023",
        "origin": "DERIVED",
        "model_type": "Historical Disaster Reconstruction Digital Twin MVP",
        "baseline_state": "Observed incident replay connected",
        "intervention_state": "Scenario A rule-based auto-closure available",
        "response_window_min": reconstruction["intervention"]["available_response_window_min"],
        "time_until_full_inundation_min": reconstruction["intervention"]["time_until_full_inundation_min"],
        "official_population": repo["population"]["osong_population"],
        "official_population_unit": repo["population"]["unit"],
        "building_count": layers["buildings"]["feature_count"],
        "road_count": layers["roads"]["feature_count"],
        "waterway_count": layers["waterways"]["feature_count"],
        "terrain_low_elevation_cells": layers["terrain"]["feature_count"],
        "terrain_low_elevation_threshold_m": repo["dem"].get("low_elevation_threshold_m"),
        "hand_reconstruction_features": layers["hand_reconstruction"]["feature_count"],
        "rainfall_peak_mm_per_hour": repo["rainfall"].get("max_mm_per_hour"),
        "rainfall_peak_timestamp": repo["rainfall"].get("peak_timestamp"),
        "rainfall_peak_station_name": repo["rainfall"].get("peak_station_name"),
        "rainfall_records": repo["rainfall"].get("records"),
        "water_level_peak_m": repo["water_level"].get("max_water_level_m"),
        "water_level_peak_timestamp": repo["water_level"].get("peak_timestamp"),
        "water_level_peak_station_name": repo["water_level"].get("peak_station_name"),
        "primary_water_level_peak_m": repo["analysis"]["water_level"].get("primary_station_peak_m"),
        "primary_water_level_peak_timestamp": repo["analysis"]["water_level"].get("primary_station_peak_timestamp"),
        "facility_count": layers["facilities"]["feature_count"],
        "underpass_available": layers["underpass"]["feature_count"] > 0,
        "safemap_floodmarks_available": repo["safemap_floodmarks"]["status"] == "VERIFIED",
        "flooded_area_km2": "PENDING_FLOOD_EXTENT",
        "exposed_population": "PENDING_FLOOD_EXTENT",
        "exposed_buildings": "PENDING_FLOOD_EXTENT",
        "affected_road_length_km": "PENDING_FLOOD_EXTENT",
        "critical_infrastructure": "PENDING_FLOOD_EXTENT",
        "affected_shelters": "PENDING_FLOOD_EXTENT",
        "data_status": "Flood Extent unavailable; exposure KPIs are intentionally not calculated.",
    }
