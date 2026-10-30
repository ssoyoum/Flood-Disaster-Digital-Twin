"""Collect floodplain sites that are closed when the river rises: low crossings, riverbed sports grounds and parking.

The name search in collect_riverside_access.py only finds sites whose names say 둔치 or 하천. This script finds
them by position instead:

- low_bridge: OSM ford=yes (세월교·여울 횡단) within 50 m of a WAMIS river line
- riverside_sports: leisure=pitch/sports_centre/track within 80 m of an OSM river water area (둔치 운동장)
- riverside_parking: amenity=parking within 40 m of an OSM river water area (둔치 주차장)

The water areas are OSM natural=water + water=river/stream/canal (ways and multipolygon relations). The floodplain
itself is usually not mapped as water, so the distances above stand in for "on the floodplain"; a site just
outside a levee can still pass. Sites already in riverside_access.csv or river_contact_extra.csv are skipped.

    python data/scripts/collect_river_floodplain_sites.py            # download from Overpass, then filter
    python data/scripts/collect_river_floodplain_sites.py --offline  # reuse data/raw/facilities/osm/river_floodplain_*.json

Output: data/processed/facilities/river_floodplain_sites.csv (same columns as riverside_access.csv)
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "facilities" / "osm"
OUT = ROOT / "data" / "processed" / "facilities" / "river_floodplain_sites.csv"
EXISTING = [ROOT / "data" / "processed" / "facilities" / name for name in ("riverside_access.csv", "river_contact_extra.csv")]
RIVERS = [ROOT / "data" / "raw" / "river" / "wamis_river_network" / name for name in ("ntn_rvr.zip", "lcl_rvr.zip")]
ADM1 = ROOT / "data" / "raw" / "boundaries" / "geoBoundaries-KOR-ADM1.geojson"
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter")
AREA = 'area["ISO3166-1"="KR"][admin_level=2]->.kr;'
QUERIES = {
    "water": f'[out:json][timeout:600];{AREA}(way["natural"="water"]["water"~"^(river|stream|canal)$"](area.kr);relation["natural"="water"]["water"~"^(river|stream|canal)$"](area.kr););out geom;',
    "sites": f'[out:json][timeout:600];{AREA}(nwr["ford"="yes"](area.kr);nwr["leisure"~"^(pitch|sports_centre|track)$"](area.kr);nwr["amenity"="parking"](area.kr););out center tags;',
}
MAX_TO_WATER_M = {"riverside_sports": 80, "riverside_parking": 40}
MAX_TO_LINE_M = {"low_bridge": 50}
KIND_KO = {"low_bridge": "세월교·잠수교", "riverside_sports": "둔치 체육시설", "riverside_parking": "둔치·하천변 주차장"}
UNNAMED = {"low_bridge": "세월교", "riverside_sports": "둔치 운동장", "riverside_parking": "둔치 주차장"}
SPORT_KO = {"soccer": "축구장", "baseball": "야구장", "basketball": "농구장", "tennis": "테니스장", "multi": "다목적 운동장", "gateball": "게이트볼장",
            "golf": "골프 연습장", "futsal": "풋살장", "volleyball": "배구장", "badminton": "배드민턴장", "athletics": "육상 트랙"}
SIDO = {"KR-11": "서울", "KR-26": "부산", "KR-27": "대구", "KR-28": "인천", "KR-29": "광주", "KR-30": "대전", "KR-31": "울산",
        "KR-50": "세종", "KR-41": "경기", "KR-42": "강원", "KR-43": "충북", "KR-44": "충남", "KR-45": "전북", "KR-46": "전남",
        "KR-47": "경북", "KR-48": "경남", "KR-49": "제주"}


def fetch(key: str, offline: bool) -> dict:
    path = RAW_DIR / f"river_floodplain_{key}.json"
    if offline or path.exists():  # delete the file to download it again
        return json.loads(path.read_text(encoding="utf-8"))
    data = urllib.parse.urlencode({"data": QUERIES[key]}).encode()
    for endpoint in OVERPASS:  # the public instances return 502/504 under load
        try:
            request = urllib.request.Request(endpoint, data=data, headers={"User-Agent": "FloodOps/1.0 (river-contact facility research)"})
            with urllib.request.urlopen(request, timeout=660) as response:
                body = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"{endpoint}: {exc}")
    else:
        raise RuntimeError(f"every Overpass endpoint failed for {key}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return body


def water_areas(body: dict) -> gpd.GeoDataFrame:
    shapes = []
    for element in body.get("elements", []):
        if element["type"] == "way":
            coords = [(p["lon"], p["lat"]) for p in element.get("geometry", [])]
            if len(coords) >= 4 and coords[0] == coords[-1]:
                shapes.append(Polygon(coords))
        elif element["type"] == "relation":
            lines = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in element.get("members", [])
                     if m.get("role") == "outer" and len(m.get("geometry") or []) >= 2]
            if lines:
                shapes.extend(polygonize(unary_union(lines)))  # unary_union nodes the outer ring pieces
    frame = gpd.GeoDataFrame(geometry=[s for s in shapes if s.is_valid and not s.is_empty], crs="EPSG:4326")
    return frame.to_crs("EPSG:5179")


def kind_of(tags: dict) -> str | None:
    if tags.get("ford") == "yes":
        return "low_bridge"
    if tags.get("leisure") in ("pitch", "sports_centre", "track"):
        return "riverside_sports"
    if tags.get("amenity") == "parking":
        return "riverside_parking"
    return None


def sites(body: dict, skip: set[str]) -> gpd.GeoDataFrame:
    rows = []
    for element in body.get("elements", []):
        tags = element.get("tags", {})
        kind = kind_of(tags)
        osm_id = f"{element['type']}/{element['id']}"
        lon = element.get("lon", (element.get("center") or {}).get("lon"))
        lat = element.get("lat", (element.get("center") or {}).get("lat"))
        if kind is None or lon is None or lat is None or osm_id in skip:
            continue
        sport = SPORT_KO.get((tags.get("sport") or "").split(";")[0], "")
        rows.append({"osm_id": osm_id, "name": tags.get("name", ""), "sport": sport, "kind": kind, "access": tags.get("access", ""),
                     "lon": float(lon), "lat": float(lat)})
    frame = pd.DataFrame(rows)
    return gpd.GeoDataFrame(frame, geometry=[Point(xy) for xy in zip(frame.lon, frame.lat)], crs="EPSG:4326").to_crs("EPSG:5179")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="reuse the saved Overpass responses")
    args = parser.parse_args()
    skip = set()
    for path in EXISTING:
        if path.exists():
            with path.open(encoding="utf-8", newline="") as handle:
                skip |= {row["osm_id"] for row in csv.DictReader(handle)}
    water = water_areas(fetch("water", args.offline))
    candidates = sites(fetch("sites", args.offline), skip)
    print(f"water areas {len(water)} · candidates {len(candidates)}", candidates["kind"].value_counts().to_dict())

    rivers = pd.concat([gpd.read_file(f"zip://{path}").assign(river_class="national" if "ntn" in path.name else "local") for path in RIVERS])
    rivers = rivers.to_crs("EPSG:5179")[["RIVNM_2", "river_class", "geometry"]].rename(columns={"RIVNM_2": "river_name"})
    joined = gpd.sjoin_nearest(candidates, rivers, how="left", distance_col="distance_to_river_m").drop_duplicates("osm_id")
    joined = gpd.sjoin_nearest(joined.drop(columns=["index_right"]), water, how="left", distance_col="distance_to_water_m").drop_duplicates("osm_id")
    by_line = joined["kind"].map(MAX_TO_LINE_M)
    by_water = joined["kind"].map(MAX_TO_WATER_M)
    keep = (by_line.notna() & (joined["distance_to_river_m"] <= by_line)) | (by_water.notna() & (joined["distance_to_water_m"] <= by_water))
    kept = joined[keep].drop(columns=["index_right"])

    regions = gpd.read_file(ADM1)[["shapeISO", "geometry"]].to_crs("EPSG:5179")
    kept = gpd.sjoin_nearest(kept, regions, how="left").to_crs("EPSG:4326").drop_duplicates("osm_id")
    kept["sido"] = kept["shapeISO"].map(SIDO).fillna("")
    river = kept["river_name"].fillna("하천").astype(str)
    unnamed = kept["name"].eq("")
    label = kept["sport"].where(kept["sport"].ne("") & kept["kind"].eq("riverside_sports"), kept["kind"].map(UNNAMED))
    kept.loc[unnamed, "name"] = river[unnamed] + " " + label[unnamed] + "(이름 없음)"

    # Several pitches or parking bays side by side are one place for the board: one per name within ~500 m.
    kept = kept.sort_values(["distance_to_river_m"])
    chosen: list[int] = []
    seen: dict[str, list[tuple[float, float]]] = {}
    for index, row in kept.iterrows():
        key = f"{row['kind']}:{row['name']}"
        if any(abs(lon - row["lon"]) < 0.006 and abs(lat - row["lat"]) < 0.0045 for lon, lat in seen.get(key, [])):
            continue
        seen.setdefault(key, []).append((row["lon"], row["lat"]))
        chosen.append(index)
    kept = kept.loc[chosen].sort_values(["sido", "kind", "name"])

    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["facility_id", "name", "kind", "kind_ko", "sido", "lon", "lat", "river_name", "river_class",
                         "distance_to_river_m", "access", "source", "osm_id"])
        for row in kept.itertuples():
            writer.writerow([f"osm:{row.osm_id}", row.name, row.kind, KIND_KO[row.kind], row.sido, round(row.lon, 6), round(row.lat, 6),
                             row.river_name, row.river_class, round(row.distance_to_river_m), row.access, "OpenStreetMap (ODbL)", row.osm_id])
    print(f"kept {len(kept)}", kept["kind"].value_counts().to_dict())
    print(kept.groupby("sido").size().sort_values(ascending=False).to_dict())


if __name__ == "__main__":
    main()
