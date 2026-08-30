"""Create validated Osong processed layers from downloaded raw sources."""

import csv
import hashlib
import json
from pathlib import Path

from shapely.geometry import box, shape
import tifffile


ROOT = Path(__file__).resolve().parents[2]
RAW_OSM = ROOT / "data/raw/osong/osm_context_2026-08-30.json"
RAW_OSM_EVENT = ROOT / "data/raw/osong/osm_context_2023-07-15.json"
RAW_BOUNDARIES = ROOT / "data/raw/boundaries"
PROCESSED = ROOT / "data/processed/osong"
AOI = box(127.27, 36.58, 127.40, 36.68)


def feature(properties: dict, geometry: dict) -> dict:
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def write_geojson(name: str, features: list[dict]) -> None:
    output = PROCESSED / name
    output.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")


def validate_features(name: str, features: list[dict], geometry_type: str | tuple[str, ...]) -> None:
    if not features:
        raise ValueError(f"{name}: no features")
    accepted_types = {geometry_type} if isinstance(geometry_type, str) else set(geometry_type)
    if any(item["geometry"]["type"] not in accepted_types for item in features):
        raise ValueError(f"{name}: unexpected geometry type")
    if any(not shape(item["geometry"]).is_valid for item in features):
        raise ValueError(f"{name}: invalid geometry")


def element_coordinates(element: dict) -> list[list[float]]:
    return [[point["lon"], point["lat"]] for point in element.get("geometry", [])]


def process_osm(snapshot_date: str, raw_path: Path) -> dict[str, int]:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    buildings: list[dict] = []
    roads: list[dict] = []
    waterways: list[dict] = []
    facilities: list[dict] = []
    tunnels: list[dict] = []

    for element in raw["elements"]:
        tags = element.get("tags", {})
        coords = element_coordinates(element)
        name = tags.get("name") or tags.get("ref") or "OSM feature"
        if tags.get("building") and len(coords) >= 3:
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            buildings.append(feature({"name": name, "building": tags["building"], "osm_id": element["id"], "origin": "OBSERVED"}, {"type": "Polygon", "coordinates": [coords]}))
        if tags.get("highway") and len(coords) >= 2:
            road = feature({"name": name, "highway": tags["highway"], "osm_id": element["id"], "origin": "OBSERVED"}, {"type": "LineString", "coordinates": coords})
            roads.append(road)
            if tags.get("tunnel") == "yes":
                tunnels.append(road)
        if tags.get("waterway") and len(coords) >= 2:
            waterways.append(feature({"name": name, "waterway": tags["waterway"], "osm_id": element["id"], "origin": "OBSERVED"}, {"type": "LineString", "coordinates": coords}))
        if tags.get("amenity"):
            point = coords[0] if len(coords) == 1 else ([sum(item[0] for item in coords) / len(coords), sum(item[1] for item in coords) / len(coords)] if coords else [])
            if point:
                facilities.append(feature({"name": name, "amenity": tags["amenity"], "osm_id": element["id"], "origin": "OBSERVED"}, {"type": "Point", "coordinates": point}))

    suffix = "2026" if snapshot_date == "2026-08-30" else "2023"
    write_geojson(f"osong_osm_buildings_{suffix}.geojson", buildings)
    write_geojson(f"osong_osm_roads_{suffix}.geojson", roads)
    write_geojson(f"osong_osm_waterways_{suffix}.geojson", waterways)
    write_geojson(f"osong_osm_facilities_{suffix}.geojson", facilities)
    write_geojson(f"osong_osm_tunnels_{suffix}.geojson", tunnels)
    validate_features("buildings", buildings, "Polygon")
    validate_features("roads", roads, "LineString")
    validate_features("waterways", waterways, "LineString")
    validate_features("facilities", facilities, "Point")
    validate_features("tunnels", tunnels, "LineString")
    return {"snapshot_date": snapshot_date, "buildings": len(buildings), "roads": len(roads), "waterways": len(waterways), "facilities": len(facilities), "tunnels": len(tunnels)}


def process_gungpyeong2_underpass(raw_path: Path) -> dict[str, int | str]:
    """Combine the two event-date OSM carriageways into the MVP facility layer."""
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    source_features = []
    for element in raw["elements"]:
        tags = element.get("tags", {})
        if tags.get("name") != "궁평지하차도" or tags.get("tunnel") != "yes":
            continue
        coords = element_coordinates(element)
        if len(coords) >= 2:
            source_features.append((element["id"], coords))

    if len(source_features) != 2:
        raise ValueError(f"gungpyeong2_underpass: expected 2 OSM carriageways, got {len(source_features)}")

    facility = feature(
        {
            "facility_id": "osong-gungpyeong2-underpass",
            "facility_name": "궁평2지하차도",
            "facility_type": "underpass",
            "road_route": "지방도 508호선",
            "route_context": "청주-세종 연결 도로",
            "managing_agency": "충청북도도로관리사업소",
            "official_name_verified": True,
            "official_route_verified": True,
            "official_managing_agency_verified": True,
            "official_source": "https://www.chungbuk.go.kr/www/selectBbsNttView.do?bbsNo=65&key=429&nttNo=284501&pageIndex=42&searchCnd=CN&searchCtgry=&searchKrwd=%EB%8F%84%EB%A1%9C",
            "geometry_source": "OpenStreetMap Overpass attic snapshot",
            "geometry_snapshot": "2023-07-15T23:59:59Z",
            "osm_ids": [item[0] for item in source_features],
            "event_date": "2023-07-15",
            "origin": "DERIVED",
        },
        {"type": "MultiLineString", "coordinates": [item[1] for item in source_features]},
    )
    validate_features("gungpyeong2_underpass", [facility], "MultiLineString")
    write_geojson("gungpyeong2_underpass.geojson", [facility])
    return {"feature_count": 1, "source_feature_count": len(source_features), "geometry_type": "MultiLineString"}


def process_boundaries() -> dict[str, int]:
    counts = {}
    for level in ("ADM1", "ADM2"):
        source = json.loads((RAW_BOUNDARIES / f"geoBoundaries-KOR-{level}.geojson").read_text(encoding="utf-8"))
        selected = [item for item in source["features"] if shape(item["geometry"]).intersects(AOI)]
        validate_features(level, selected, ("Polygon", "MultiPolygon"))
        write_geojson(f"osong_geoboundaries_{level.lower()}_aoi.geojson", selected)
        counts[level.lower()] = len(selected)
    return counts


def process_nasa_power() -> dict[str, float | int]:
    source = json.loads((ROOT / "data/raw/osong/nasa_power_precip_2023-07-15_16.json").read_text(encoding="utf-8"))
    values = source["properties"]["parameter"]["PRECTOTCORR"]
    output = PROCESSED / "osong_nasa_power_precip_2023-07-15_16.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["timestamp", "latitude", "longitude", "parameter", "precipitation_mm_per_hour", "data_year", "origin", "source"])
        writer.writeheader()
        for timestamp, value in values.items():
            writer.writerow({"timestamp": timestamp, "latitude": 36.628, "longitude": 127.354, "parameter": "PRECTOTCORR", "precipitation_mm_per_hour": value, "data_year": 2023, "origin": "DERIVED", "source": "NASA POWER hourly reanalysis"})
    return {"records": len(values), "max_mm_per_hour": max(values.values())}


def validate_rasters() -> dict[str, dict]:
    rasters = {
        "dem": ROOT / "data/raw/copernicus_dem_glo30/Copernicus_DSM_COG_10_N36_00_E127_00_DEM.tif",
        "population": ROOT / "data/raw/worldpop/kor_pop_2023_CN_100m_R2025A_v1.tif",
    }
    result = {}
    for name, path in rasters.items():
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            geo_keys = page.tags["GeoKeyDirectoryTag"].value
            keys = {geo_keys[index]: geo_keys[index + 3] for index in range(4, len(geo_keys), 4) if geo_keys[index + 1] == 0}
            if keys.get(2048) != 4326:
                raise ValueError(f"{name}: expected EPSG:4326, got GeoKey {keys.get(2048)}")
            result[name] = {
                "local_file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "dimensions": list(page.shape[::-1]),
                "crs": "EPSG:4326",
                "pixel_scale": list(page.tags["ModelPixelScaleTag"].value),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            }
    return result


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    result = {"osm": {"current": process_osm("2026-08-30", RAW_OSM), "event": process_osm("2023-07-15", RAW_OSM_EVENT)}, "gungpyeong2_underpass": process_gungpyeong2_underpass(RAW_OSM_EVENT), "boundaries": process_boundaries(), "nasa_power": process_nasa_power(), "rasters": validate_rasters()}
    (PROCESSED / "validation_report.json").write_text(json.dumps({"aoi": [127.27, 36.58, 127.40, 36.68], "crs": "EPSG:4326", "validation": "geometry type and validity checks passed", "result": result}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(result)
