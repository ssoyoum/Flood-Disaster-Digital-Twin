"""Collect two more river-contact facility types: riverside campsites and low (submersible) bridges.

Both are closed or evacuated when the river rises, and both are spread across the country rather than the
capital region, unlike underpasses. Candidates come from OpenStreetMap and are kept only when they lie close to a
WAMIS national or local river line, the same check as collect_riverside_access.py.

- riverside_camp: tourism=camp_site/caravan_site within 200 m of a river line (야영장·캠핑장)
- low_bridge: a bridge or road named 세월교/잠수교/세월 within 50 m of a river line (낮은 교량, 물이 넘으면 통제)

    python data/scripts/collect_river_contact_extra.py            # download from Overpass, then filter
    python data/scripts/collect_river_contact_extra.py --offline  # reuse data/raw/facilities/osm/river_contact_extra.json

Outputs:
- data/raw/facilities/osm/river_contact_extra.json      raw Overpass response (ODbL, © OpenStreetMap contributors)
- data/processed/facilities/river_contact_extra.csv     kept sites, same columns as riverside_access.csv

Being near a river says the site is exposed to it. It does not say who closes it or at which stage.
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
RAW = ROOT / "data" / "raw" / "facilities" / "osm" / "river_contact_extra.json"
OUT = ROOT / "data" / "processed" / "facilities" / "river_contact_extra.csv"
RIVERS = [ROOT / "data" / "raw" / "river" / "wamis_river_network" / name for name in ("ntn_rvr.zip", "lcl_rvr.zip")]
ADM1 = ROOT / "data" / "raw" / "boundaries" / "geoBoundaries-KOR-ADM1.geojson"
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter")

BRIDGE_NAME = "세월교|잠수교|세월"
MAX_DISTANCE_M = {"riverside_camp": 200, "low_bridge": 50}
KIND_KO = {"riverside_camp": "하천변 야영장", "low_bridge": "세월교·잠수교"}
SIDO = {"KR-11": "서울", "KR-26": "부산", "KR-27": "대구", "KR-28": "인천", "KR-29": "광주", "KR-30": "대전", "KR-31": "울산",
        "KR-50": "세종", "KR-41": "경기", "KR-42": "강원", "KR-43": "충북", "KR-44": "충남", "KR-45": "전북", "KR-46": "전남",
        "KR-47": "경북", "KR-48": "경남", "KR-49": "제주"}

QUERY = f"""
[out:json][timeout:300];
area["ISO3166-1"="KR"][admin_level=2]->.kr;
(
  nwr["tourism"~"^(camp_site|caravan_site)$"](area.kr);
  way["bridge"]["name"~"{BRIDGE_NAME}"](area.kr);
  nwr["man_made"="bridge"]["name"~"{BRIDGE_NAME}"](area.kr);
);
out center tags;
"""


def download() -> dict:
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    last_error: Exception | None = None
    for endpoint in OVERPASS:  # the public instances return 502/504 under load
        request = urllib.request.Request(endpoint, data=data, headers={"User-Agent": "FloodOps/1.0 (river-contact facility research)"})
        try:
            with urllib.request.urlopen(request, timeout=360) as response:
                body = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:  # noqa: BLE001 - try the next mirror
            print(f"{endpoint}: {exc}")
            last_error = exc
    else:
        raise RuntimeError("every Overpass endpoint failed") from last_error
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return body


def kind_of(tags: dict) -> str | None:
    if tags.get("tourism") in ("camp_site", "caravan_site"):
        return "riverside_camp"
    if (tags.get("bridge") or tags.get("man_made") == "bridge") and re.search(BRIDGE_NAME, tags.get("name", "")):
        return "low_bridge"
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
        name = tags.get("name", "")
        rows.append({"osm_id": f"{element['type']}/{element['id']}", "name": name, "kind": kind,
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
    joined = gpd.sjoin_nearest(sites.to_crs("EPSG:5179"), rivers, how="left", distance_col="distance_to_river_m")
    joined = joined.sort_values("distance_to_river_m").drop_duplicates("osm_id")
    joined["max_m"] = joined["kind"].map(MAX_DISTANCE_M)
    kept = joined[joined["distance_to_river_m"] <= joined["max_m"]].to_crs("EPSG:4326")

    regions = gpd.read_file(ADM1)[["shapeISO", "geometry"]].to_crs("EPSG:5179")
    kept = gpd.sjoin_nearest(kept.drop(columns=["index_right"], errors="ignore").to_crs("EPSG:5179"), regions, how="left").to_crs("EPSG:4326")
    kept = kept.drop_duplicates("osm_id")
    kept["sido"] = kept["shapeISO"].map(SIDO).fillna("")
    # An unnamed campsite is told apart by the river it sits on.
    unnamed = kept["name"].eq("")
    kept.loc[unnamed, "name"] = kept.loc[unnamed, "river_name"].fillna("하천").astype(str) + " 야영장(이름 없음)"

    # One bridge is often several OSM ways; one campsite a node and an area. Keep one per name within ~500 m.
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["facility_id", "name", "kind", "kind_ko", "sido", "lon", "lat", "river_name", "river_class",
                         "distance_to_river_m", "access", "source", "osm_id"])
        for row in kept.itertuples():
            writer.writerow([f"osm:{row.osm_id}", row.name, row.kind, KIND_KO[row.kind], row.sido, round(row.lon, 6), round(row.lat, 6),
                             row.river_name, row.river_class, round(row.distance_to_river_m), row.access, "OpenStreetMap (ODbL)", row.osm_id])
    print(f"kept {len(kept)} of {len(sites)}", kept["kind"].value_counts().to_dict())
    print(kept.groupby(["kind", "sido"]).size().to_dict())


if __name__ == "__main__":
    main()
