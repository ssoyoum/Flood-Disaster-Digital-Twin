"""Build map layers for the timeline-only cases (Pohang 2022, Andong-Uiseong 2026).

These cases have no official flood extent or gauge series in the repository yet. The map carries an
event-date OpenStreetMap snapshot and a handful of named public places used as focus sites.
Raw Overpass responses are cached under data/raw/<case>/ (outside Git).

Usage: python data/scripts/process_timeline_cases.py [pohang-2022|andong-uiseong-2026]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERPASS = "https://overpass-api.de/api/interpreter"

CASES = {
    "pohang-2022": {
        "raw_dir": ROOT / "data/raw/pohang",
        "out_dir": ROOT / "data/processed/pohang_2022",
        "prefix": "pohang",
        # Naengcheon lower reach: Naengcheon bridge, Indeok-dong and the POSCO Pohang works edge.
        "bbox": (129.37, 35.965, 129.43, 36.01),
        "snapshot": "2022-09-06T00:00:00Z",
        "aoi_name": "냉천 하류·인덕동 분석 범위",
        "sites": [
            {"name": "냉천교", "kind": "bridge", "lon": 129.40142, "lat": 35.99343, "note": "범람 지점으로 보도된 교량(1970년대 교량, 교각 다수)"},
            {"name": "인덕교", "kind": "bridge", "lon": 129.40359, "lat": 35.98517, "note": "복구사업 재가설 대상 교량"},
            {"name": "인덕동 일대", "kind": "neighbourhood", "lon": 129.39973, "lat": 35.98701, "note": "지하주차장 침수 사고가 난 동. 개별 단지는 표시하지 않음"},
        ],
    },
    "andong-uiseong-2026": {
        "raw_dir": ROOT / "data/raw/andong",
        "out_dir": ROOT / "data/processed/andong_uiseong_2026",
        "prefix": "andong",
        # Iljik-myeon (Andong) and Danchon-myeon (Uiseong): Micheon and the two temporary housing villages.
        "bbox": (128.63, 36.44, 128.80, 36.535),
        "snapshot": "2026-07-17T00:00:00Z",
        "aoi_name": "미천·일직면·단촌면 분석 범위",
        "sites": [
            {"name": "귀미1리 (안동 일직면)", "kind": "temporary_housing_village", "lon": 128.68783, "lat": 36.46538, "note": "산불 이재민 임시주택 침수·토사 피해 보도. 마을 중심점이며 단지 위치가 아님"},
            {"name": "구계리 (의성 단촌면)", "kind": "temporary_housing_village", "lon": 128.74354, "lat": 36.46841, "note": "임시주택 침수, 주민·캠핑객 155명 대피 보도. 마을 중심점"},
            {"name": "운산리 (미천 홍수경보 지점)", "kind": "warning_point", "lon": 128.65074, "lat": 36.47405, "note": "낙동강홍수통제소 홍수경보 발령 지점(보도). 관측소 좌표가 아니라 마을 중심점"},
            {"name": "광음리", "kind": "village", "lon": 128.66721, "lat": 36.50849, "note": "유원지 캠핑카 고립 보도"},
            {"name": "신석리", "kind": "village", "lon": 128.78442, "lat": 36.52302, "note": "교회 일대 침수·3명 고립 보도"},
        ],
    },
}


def fetch_osm(case: dict) -> dict:
    raw_path = case["raw_dir"] / f"osm_{case['prefix']}_{case['snapshot'][:10]}.json"
    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8"))
    west, south, east, north = case["bbox"]
    box = f"({south},{west},{north},{east})"
    query = (
        f'[out:json][timeout:240][date:"{case["snapshot"]}"];'
        f'(way["building"]{box};way["highway"]{box};way["waterway"]{box};node["amenity"]{box};way["amenity"]{box};);'
        "out geom tags;"
    )
    request = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "FloodOps-research/1.0", "Accept": "application/json"},
    )
    for attempt in range(3):
        try:
            payload = urllib.request.urlopen(request, timeout=300).read()
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
    case["raw_dir"].mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    return json.loads(payload)


def feature(properties: dict, geometry: dict) -> dict:
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def write(out_dir: Path, name: str, features: list[dict]) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    return len(features)


def build(case_id: str) -> dict:
    case = CASES[case_id]
    raw = fetch_osm(case)
    buildings, roads, waterways, facilities = [], [], [], []
    for element in raw["elements"]:
        tags = element.get("tags", {})
        coords = [[round(point["lon"], 6), round(point["lat"], 6)] for point in element.get("geometry", [])]
        name = tags.get("name") or tags.get("ref") or ""
        base = {"name": name, "osm_id": element["id"], "origin": "OBSERVED"}
        if tags.get("building") and len(coords) >= 3:
            if coords[0] != coords[-1]:
                coords = coords + [coords[0]]
            buildings.append(feature(base | {"building": tags["building"]}, {"type": "Polygon", "coordinates": [coords]}))
        if tags.get("highway") and len(coords) >= 2:
            roads.append(feature(base | {"highway": tags["highway"]}, {"type": "LineString", "coordinates": coords}))
        if tags.get("waterway") and len(coords) >= 2:
            waterways.append(feature(base | {"waterway": tags["waterway"]}, {"type": "LineString", "coordinates": coords}))
        if tags.get("amenity"):
            if element.get("type") == "node":
                point = [element["lon"], element["lat"]]
            elif coords:
                point = [sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords)]
            else:
                continue
            facilities.append(feature(base | {"amenity": tags["amenity"]}, {"type": "Point", "coordinates": point}))

    west, south, east, north = case["bbox"]
    aoi = [feature({"name": case["aoi_name"]}, {"type": "Polygon", "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]]})]
    sites = [feature({k: v for k, v in site.items() if k not in {"lon", "lat"}} | {"origin": "DERIVED"}, {"type": "Point", "coordinates": [site["lon"], site["lat"]]}) for site in case["sites"]]
    out, prefix = case["out_dir"], case["prefix"]
    counts = {
        "aoi": write(out, f"{prefix}_aoi.geojson", aoi),
        "buildings": write(out, f"{prefix}_osm_buildings.geojson", buildings),
        "roads": write(out, f"{prefix}_osm_roads.geojson", roads),
        "waterways": write(out, f"{prefix}_osm_waterways.geojson", waterways),
        "facilities": write(out, f"{prefix}_osm_facilities.geojson", facilities),
        "sites": write(out, f"{prefix}_focus_sites.geojson", sites),
    }
    summary = {"case_id": case_id, "bbox": list(case["bbox"]), "osm_snapshot": case["snapshot"], "counts": counts}
    (out / f"{prefix}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    targets = sys.argv[1:] or list(CASES)
    for case_id in targets:
        print(json.dumps(build(case_id), ensure_ascii=False))
