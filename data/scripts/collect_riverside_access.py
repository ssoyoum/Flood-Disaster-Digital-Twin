"""Collect riverside access points (둔치·고수부지 주차장, 하천 공원, 하상도로) and keep the ones on a river.

These are the first expansion type of the river-contact facility twin: places the public enters from the
riverbank, which are closed when the river rises. There is no national register with coordinates, so the
candidates come from OpenStreetMap by name and are kept only when they lie within a set distance of a
WAMIS national or local river line (data/raw/river/wamis_river_network). The 시도 comes from the
geoBoundaries ADM1 polygons.

    python data/scripts/collect_riverside_access.py            # download from Overpass, then filter
    python data/scripts/collect_riverside_access.py --offline  # reuse data/raw/facilities/osm/riverside_access.json

Outputs:
- data/raw/facilities/osm/riverside_access.json   raw Overpass response (ODbL, © OpenStreetMap contributors)
- data/processed/facilities/riverside_access.csv  kept sites with river name and distance

A name match plus river proximity says the site is on a riverbank. It does not say who closes it or when;
that is per municipality and is not in this table.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "facilities" / "osm" / "riverside_access.json"
OUT = ROOT / "data" / "processed" / "facilities" / "riverside_access.csv"
RIVERS = [ROOT / "data" / "raw" / "river" / "wamis_river_network" / name for name in ("ntn_rvr.zip", "lcl_rvr.zip")]
ADM1 = ROOT / "data" / "raw" / "boundaries" / "geoBoundaries-KOR-ADM1.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"

# Riverbank words. 강변·수변 alone also name apartments and hotels, so they only count together with a
# park/parking word or the river check below; the river check is what finally decides.
PARKING_NAME = "둔치|고수부지|천변|강변|수변|하천|한강공원|하상"
PARK_NAME = "둔치|고수부지|한강공원|강변공원|천변공원|수변공원|하천공원|둔치공원|시민공원"
ROAD_NAME = "하상도로|둔치도로|천변도로"
MAX_DISTANCE_M = {"riverside_parking": 200, "riverside_park": 300, "riverbed_road": 100}
KIND_KO = {"riverside_parking": "둔치·하천변 주차장", "riverside_park": "하천 둔치 공원", "riverbed_road": "하상도로"}
SIDO = {"KR-11": "서울", "KR-26": "부산", "KR-27": "대구", "KR-28": "인천", "KR-29": "광주", "KR-30": "대전", "KR-31": "울산",
        "KR-50": "세종", "KR-41": "경기", "KR-42": "강원", "KR-43": "충북", "KR-44": "충남", "KR-45": "전북", "KR-46": "전남",
        "KR-47": "경북", "KR-48": "경남", "KR-49": "제주"}

QUERY = f"""
[out:json][timeout:300];
area["ISO3166-1"="KR"][admin_level=2]->.kr;
(
  nwr["amenity"="parking"]["name"~"{PARKING_NAME}"](area.kr);
  nwr["leisure"="park"]["name"~"{PARK_NAME}"](area.kr);
  way["highway"]["name"~"{ROAD_NAME}"](area.kr);
);
out center tags;
"""


def download() -> dict:
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    request = urllib.request.Request(OVERPASS, data=data, headers={"User-Agent": "FloodOps/1.0 (river-contact facility research)"})
    with urllib.request.urlopen(request, timeout=360) as response:
        body = json.loads(response.read().decode("utf-8"))
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return body


def kind_of(tags: dict) -> str | None:
    name = tags.get("name", "")
    if tags.get("amenity") == "parking":
        return "riverside_parking"
    if tags.get("leisure") == "park":
        return "riverside_park"
    if tags.get("highway") and re.search(ROAD_NAME, name):
        return "riverbed_road"
    return None


def candidates(body: dict) -> gpd.GeoDataFrame:
    rows = []
    for element in body.get("elements", []):
        tags = element.get("tags", {})
        kind = kind_of(tags)
        lon = element.get("lon", (element.get("center") or {}).get("lon"))
        lat = element.get("lat", (element.get("center") or {}).get("lat"))
        if kind is None or lon is None or lat is None:
            continue
        rows.append({"osm_id": f"{element['type']}/{element['id']}", "name": tags.get("name", ""), "kind": kind,
                     "access": tags.get("access", ""), "lon": float(lon), "lat": float(lat)})
    frame = pd.DataFrame(rows)
    return gpd.GeoDataFrame(frame, geometry=[Point(xy) for xy in zip(frame.lon, frame.lat)], crs="EPSG:4326")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="reuse the saved Overpass response")
    args = parser.parse_args()
    body = json.loads(RAW.read_text(encoding="utf-8")) if args.offline else download()
    sites = candidates(body)
    print(f"candidates {len(sites)}", sites["kind"].value_counts().to_dict())

    rivers = pd.concat([gpd.read_file(f"zip://{path}").assign(river_class="national" if "ntn" in path.name else "local") for path in RIVERS])
    rivers = rivers.to_crs("EPSG:5179")[["RIVNM_2", "river_class", "geometry"]].rename(columns={"RIVNM_2": "river_name"})
    projected = sites.to_crs("EPSG:5179")
    joined = gpd.sjoin_nearest(projected, rivers, how="left", distance_col="distance_to_river_m")
    joined = joined.sort_values("distance_to_river_m").drop_duplicates("osm_id")
    joined["max_m"] = joined["kind"].map(MAX_DISTANCE_M)
    kept = joined[joined["distance_to_river_m"] <= joined["max_m"]].to_crs("EPSG:4326")

    # Nearest polygon, not "within": the simplified ADM1 coastlines and rivers leave some riverbank points outside.
    regions = gpd.read_file(ADM1)[["shapeISO", "geometry"]].to_crs("EPSG:5179")
    kept = gpd.sjoin_nearest(kept.drop(columns=["index_right"], errors="ignore").to_crs("EPSG:5179"), regions, how="left").to_crs("EPSG:4326")
    kept = kept.drop_duplicates("osm_id")
    kept["sido"] = kept["shapeISO"].map(SIDO).fillna("")

    # The same place is often mapped twice (a node and an area, or two halves of one park); keep one per name within 500 m.
    kept = kept.sort_values(["distance_to_river_m"])
    chosen: list[int] = []
    seen: dict[str, list[tuple[float, float]]] = {}
    for index, row in kept.iterrows():
        near = [(lon, lat) for lon, lat in seen.get(row["name"], []) if abs(lon - row["lon"]) < 0.006 and abs(lat - row["lat"]) < 0.0045]
        if near:
            continue
        seen.setdefault(row["name"], []).append((row["lon"], row["lat"]))
        chosen.append(index)
    kept = kept.loc[chosen].sort_values(["sido", "kind", "name"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["facility_id", "name", "kind", "kind_ko", "sido", "lon", "lat", "river_name", "river_class",
                         "distance_to_river_m", "access", "source", "osm_id"])
        for row in kept.itertuples():
            writer.writerow([f"osm:{row.osm_id}", row.name, row.kind, KIND_KO[row.kind], row.sido, round(row.lon, 6), round(row.lat, 6),
                             row.river_name, row.river_class, round(row.distance_to_river_m), row.access, "OpenStreetMap (ODbL)", row.osm_id])
    print(f"kept {len(kept)} of {len(sites)}", kept["kind"].value_counts().to_dict())
    print(kept["sido"].value_counts().to_dict())


if __name__ == "__main__":
    main()
