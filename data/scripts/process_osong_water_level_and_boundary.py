import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[2]
RAW_WATER = ROOT / "data" / "raw" / "water_level" / "osong"
RAW_BOUNDARY = ROOT / "data" / "raw" / "admin_boundary" / "sgis_2023"
PROCESSED = ROOT / "data" / "processed" / "osong"
VALIDATION_REPORT = PROCESSED / "validation_report.json"
SGIS_TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)

WATER_START = "202307140000"
WATER_END = "202307170000"
WATER_STATIONS = {
    "3011635": "청주시(팔결교)",
    "3011665": "청주시(미호강교)",
    "3011685": "세종시(미호교)",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def text_of(node: ET.Element, name: str) -> str:
    found = node.find(name)
    return found.text.strip() if found is not None and found.text else ""


def dms_to_decimal(value: str) -> float | None:
    if not value:
        return None
    parts = value.split("-")
    if len(parts) != 3:
        return None
    deg, minute, second = (float(part) for part in parts)
    return round(deg + minute / 60 + second / 3600, 7)


def load_station_metadata() -> dict[str, dict[str, Any]]:
    path = RAW_WATER / "hrfco_waterlevel_info.xml"
    root = ET.parse(path).getroot()
    metadata: dict[str, dict[str, Any]] = {}
    for node in root.iter():
        station_id = text_of(node, "wlobscd")
        if station_id not in WATER_STATIONS:
            continue
        lon_dms = text_of(node, "lon")
        lat_dms = text_of(node, "lat")
        metadata[station_id] = {
            "station_id": station_id,
            "station_name": text_of(node, "obsnm") or WATER_STATIONS[station_id],
            "address": text_of(node, "addr"),
            "detail_address": text_of(node, "etcaddr"),
            "agency": text_of(node, "agcnm"),
            "longitude": dms_to_decimal(lon_dms),
            "latitude": dms_to_decimal(lat_dms),
            "longitude_dms": lon_dms,
            "latitude_dms": lat_dms,
        }
    return metadata


def process_water_level() -> dict[str, Any]:
    metadata = load_station_metadata()
    rows: list[dict[str, Any]] = []
    raw_files: dict[str, Any] = {
        "station_info": {
            "local_file": "data/raw/water_level/osong/hrfco_waterlevel_info.xml",
            "raw_size_bytes": (RAW_WATER / "hrfco_waterlevel_info.xml").stat().st_size,
            "raw_sha256": sha256(RAW_WATER / "hrfco_waterlevel_info.xml"),
        }
    }

    for station_id, station_name in WATER_STATIONS.items():
        path = RAW_WATER / f"hrfco_waterlevel_10m_{station_id}_{WATER_START}_{WATER_END}.xml"
        root = ET.parse(path).getroot()
        station_rows = []
        for node in root.iter():
            if text_of(node, "wlobscd") != station_id or not text_of(node, "ymdhm"):
                continue
            ymdhm = text_of(node, "ymdhm")
            row = {
                "timestamp_kst": f"{ymdhm[:4]}-{ymdhm[4:6]}-{ymdhm[6:8]} {ymdhm[8:10]}:{ymdhm[10:12]}",
                "station_id": station_id,
                "station_name": metadata.get(station_id, {}).get("station_name", station_name),
                "water_level_m": text_of(node, "wl"),
                "fw_raw": text_of(node, "fw"),
                "longitude": metadata.get(station_id, {}).get("longitude"),
                "latitude": metadata.get(station_id, {}).get("latitude"),
                "agency": metadata.get(station_id, {}).get("agency"),
            }
            station_rows.append(row)
        rows.extend(station_rows)
        raw_files[station_id] = {
            "local_file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "raw_size_bytes": path.stat().st_size,
            "raw_sha256": sha256(path),
            "record_count": len(station_rows),
            "station_metadata": metadata.get(station_id, {}),
        }

    rows.sort(key=lambda row: (row["timestamp_kst"], row["station_id"]))
    output = PROCESSED / "osong_hrfco_water_level_10m_2023-07-14_17.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "timestamp_kst",
            "station_id",
            "station_name",
            "water_level_m",
            "fw_raw",
            "longitude",
            "latitude",
            "agency",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    levels = [float(row["water_level_m"]) for row in rows if row["water_level_m"]]
    return {
        "source": "Ministry of Climate and Environment / Flood Control Office OpenAPI",
        "source_url": "https://api.hrfco.go.kr/{ServiceKey}/waterlevel/list/10M/{wlobscd}/{start}/{end}.xml",
        "source_type": "OBSERVATION",
        "status": "VERIFIED",
        "period_start": "2023-07-14 00:00 KST",
        "period_end": "2023-07-17 00:00 KST",
        "temporal_resolution": "10 minutes",
        "unit": "m",
        "record_count": len(rows),
        "stations": {station_id: raw_files[station_id] for station_id in WATER_STATIONS},
        "raw_files": raw_files,
        "processed_file": str(output.relative_to(ROOT)).replace("\\", "/"),
        "processed_sha256": sha256(output),
        "max_water_level_m": max(levels) if levels else None,
        "validation": "HRFCO waterlevel info and 10-minute XML series parsed; station IDs, period, unit, record count, coordinates, and SHA-256 recorded.",
    }


def transform_coordinates(value: Any) -> Any:
    if not isinstance(value, list):
        return value
    if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
        lon, lat = SGIS_TO_WGS84.transform(float(value[0]), float(value[1]))
        return [round(lon, 7), round(lat, 7)]
    return [transform_coordinates(item) for item in value]


def process_sgis_boundary() -> dict[str, Any]:
    source = RAW_BOUNDARY / "sgis_boundary_2023_33043_emd.geojson"
    data = json.loads(source.read_text(encoding="utf-8"))
    features = data.get("features", [])
    osong_features = []
    for feature in features:
        if "오송읍" not in feature.get("properties", {}).get("adm_nm", ""):
            continue
        transformed = json.loads(json.dumps(feature, ensure_ascii=False))
        transformed["geometry"]["coordinates"] = transform_coordinates(transformed["geometry"]["coordinates"])
        osong_features.append(transformed)
    output_data = {
        "type": "FeatureCollection",
        "features": osong_features,
    }
    output = PROCESSED / "osong_sgis_admin_boundary_2023.geojson"
    output.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    geometry_types = sorted({feature.get("geometry", {}).get("type", "Unknown") for feature in osong_features})
    return {
        "source": "SGIS OpenAPI administrative boundary",
        "source_url": "https://sgisapi.mods.go.kr/OpenAPI3/boundary/hadmarea.geojson",
        "source_type": "OFFICIAL_ADMIN_BOUNDARY",
        "status": "VERIFIED",
        "event_year": 2023,
        "boundary_snapshot": 2023,
        "raw_files": {
            "chungbuk_sgg": {
                "local_file": "data/raw/admin_boundary/sgis_2023/sgis_boundary_2023_chungbuk_sgg.geojson",
                "raw_size_bytes": (RAW_BOUNDARY / "sgis_boundary_2023_chungbuk_sgg.geojson").stat().st_size,
                "raw_sha256": sha256(RAW_BOUNDARY / "sgis_boundary_2023_chungbuk_sgg.geojson"),
            },
            "cheongju_heungdeok_emd": {
                "local_file": str(source.relative_to(ROOT)).replace("\\", "/"),
                "raw_size_bytes": source.stat().st_size,
                "raw_sha256": sha256(source),
                "feature_count": len(features),
            },
        },
        "processed_file": str(output.relative_to(ROOT)).replace("\\", "/"),
        "processed_sha256": sha256(output),
        "feature_count": len(osong_features),
        "geometry_types": geometry_types,
        "raw_crs": "EPSG:5179",
        "processed_crs": "EPSG:4326",
        "administrative_unit": "충청북도 청주시 흥덕구 오송읍",
        "adm_cd": osong_features[0].get("properties", {}).get("adm_cd") if osong_features else None,
        "validation": "SGIS 2023 Cheongju Heungdeok-gu eup/myeon/dong boundary downloaded, Osong-eup feature extracted, and coordinates transformed from EPSG:5179 to EPSG:4326.",
    }


def update_validation_report(water_level: dict[str, Any], boundary: dict[str, Any]) -> None:
    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    report["hrfco_water_level_2023"] = water_level
    report["sgis_admin_boundary_2023"] = boundary
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    water_level = process_water_level()
    boundary = process_sgis_boundary()
    update_validation_report(water_level, boundary)
    print(json.dumps({"water_level": water_level, "boundary": boundary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
