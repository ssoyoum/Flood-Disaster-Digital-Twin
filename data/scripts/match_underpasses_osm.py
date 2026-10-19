"""Give the MOLIT underpass register coordinates by matching names against OpenStreetMap.

Inputs (both public, no key):
- data/raw/facilities/molit/molit_underpass_20230930.csv — 국토교통부 「시설물안전법 대상 지하차도 현황」
  (938 rows; 시설물명 and 위치 = 시도 + 시군구 only, no coordinates).
- data/raw/facilities/osm/osm_underpass_ways.json — Overpass result for highway ways whose name
  contains 지하차도 in Korea, with way centres (ODbL).
- data/raw/facilities/osm/osm_tunnel_ways_named.json — optional wider tunnel snapshot. When the
  first source has no in-province match, Korean name aliases on tunnel ways are used as a fallback.

Matching is by normalised facility name (spaces, parentheses and 제/호 removed). OSM may hold several
ways per underpass (one per carriageway); their centres are averaged. If the same name exists in
different cities, the row is marked ambiguous and left for manual review instead of guessing.

Output: data/processed/facilities/underpass_coordinates.csv and a summary in
data/manifests/underpass-coordinates.json.

    python data/scripts/match_underpasses_osm.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MOLIT = REPO_ROOT / "data" / "raw" / "facilities" / "molit" / "molit_underpass_20230930.csv"
OSM = REPO_ROOT / "data" / "raw" / "facilities" / "osm" / "osm_underpass_ways.json"
OSM_TUNNELS = REPO_ROOT / "data" / "raw" / "facilities" / "osm" / "osm_tunnel_ways_named.json"
OUT = REPO_ROOT / "data" / "processed" / "facilities" / "underpass_coordinates.csv"
SUMMARY = REPO_ROOT / "data" / "manifests" / "underpass-coordinates.json"

# Rough province bounding boxes (lon_min, lat_min, lon_max, lat_max) to reject same-name matches in another region.
PROVINCE_BBOX = {
    "서울특별시": (126.76, 37.42, 127.19, 37.70), "인천광역시": (124.6, 37.0, 126.9, 37.98), "경기도": (126.3, 36.85, 127.9, 38.3),
    "강원특별자치도": (127.0, 37.0, 129.4, 38.65), "충청북도": (127.2, 36.0, 128.7, 37.3), "충청남도": (125.9, 35.95, 127.6, 37.1),
    "세종특별자치시": (127.1, 36.4, 127.45, 36.75), "대전광역시": (127.25, 36.17, 127.55, 36.5), "전라북도": (125.9, 35.3, 127.9, 36.2),
    "전북특별자치도": (125.9, 35.3, 127.9, 36.2), "전라남도": (125.0, 33.9, 127.9, 35.5), "광주광역시": (126.6, 35.05, 127.05, 35.3),
    "경상북도": (128.0, 35.55, 131.9, 37.6), "대구광역시": (128.35, 35.6, 128.9, 36.05), "경상남도": (127.5, 34.5, 129.3, 35.95),
    "부산광역시": (128.75, 34.95, 129.35, 35.4), "울산광역시": (128.95, 35.3, 129.5, 35.75), "제주특별자치도": (126.1, 33.1, 127.0, 33.6),
}


def norm(name: str) -> str:
    n = re.sub(r"\(.*?\)", "", name)
    n = re.sub(r"[\s·\-_]", "", n)
    n = n.replace("지하차도", "")
    n = re.sub(r"^제", "", n)
    return n


def load_molit() -> list[dict[str, str]]:
    raw = MOLIT.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.DictReader(io.StringIO(text)))
    for r in rows:
        parts = (r.get("위치") or "").split()
        r["sido"] = parts[0] if parts else ""
        r["sgg"] = " ".join(parts[1:]) if len(parts) > 1 else ""
    return rows


def load_osm() -> dict[str, list[dict]]:
    data = json.loads(OSM.read_text(encoding="utf-8"))
    by_name: dict[str, list[dict]] = defaultdict(list)
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        centre = el.get("center")
        if name and centre:
            by_name[norm(name)].append({"id": el["id"], "name": name, "lon": centre["lon"], "lat": centre["lat"], "tunnel": tags.get("tunnel", "")})
    return by_name


def load_osm_tunnel_names() -> tuple[dict[str, list[dict]], dict]:
    """Index Korean aliases from the wider OSM tunnel snapshot for fallback matching only."""
    if not OSM_TUNNELS.exists():
        return {}, {}
    data = json.loads(OSM_TUNNELS.read_text(encoding="utf-8"))
    by_name: dict[str, dict[int, dict]] = defaultdict(dict)
    name_fields = ("name", "name:ko", "tunnel:name", "tunnel:name:ko", "alt_name", "alt_name:ko")
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        centre = el.get("center")
        if el.get("type") != "way" or not centre or tags.get("tunnel") != "yes":
            continue
        for field in name_fields:
            name = (tags.get(field) or "").strip()
            key = norm(name)
            if key:
                by_name[key][int(el["id"])] = {
                    "id": el["id"], "name": name, "lon": centre["lon"], "lat": centre["lat"], "tunnel": "yes",
                }
    return {key: list(values.values()) for key, values in by_name.items()}, data


def cluster(points: list[dict], radius_km: float = 2.0) -> list[list[dict]]:
    """Group OSM ways of the same name that lie within radius_km of each other (one underpass = one cluster)."""
    groups: list[list[dict]] = []
    for p in points:
        for g in groups:
            if abs(g[0]["lat"] - p["lat"]) * 110.6 <= radius_km and abs(g[0]["lon"] - p["lon"]) * 88.8 <= radius_km:
                g.append(p)
                break
        else:
            groups.append([p])
    return groups


def in_province(sido: str, lon: float, lat: float) -> bool | None:
    box = PROVINCE_BBOX.get(sido)
    if not box:
        return None
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


def main() -> None:
    molit = load_molit()
    osm = load_osm()
    osm_tunnel_names, osm_tunnel_snapshot = load_osm_tunnel_names()
    out_rows = []
    counts = {"matched": 0, "ambiguous": 0, "unmatched": 0, "rejected_other_province": 0}
    source_counts = {"osm_underpass_ways": 0, "osm_tunnel_ways_named": 0, "none": 0}
    for r in molit:
        key = norm(r["시설물명"])
        candidates = osm.get(key, [])
        groups = cluster(candidates)
        groups = [g for g in groups if in_province(r["sido"], g[0]["lon"], g[0]["lat"]) is not False]
        rejected = len(cluster(candidates)) - len(groups)
        counts["rejected_other_province"] += rejected
        match_source = "osm_underpass_ways" if candidates else "none"
        if not groups and osm_tunnel_names:
            candidates = osm_tunnel_names.get(key, [])
            groups = cluster(candidates)
            groups = [g for g in groups if in_province(r["sido"], g[0]["lon"], g[0]["lat"]) is not False]
            counts["rejected_other_province"] += len(cluster(candidates)) - len(groups)
            match_source = "osm_tunnel_ways_named" if candidates else "none"
        status, lon, lat, ids = "unmatched", "", "", ""
        if len(groups) == 1:
            g = groups[0]
            lon = round(sum(p["lon"] for p in g) / len(g), 6)
            lat = round(sum(p["lat"] for p in g) / len(g), 6)
            ids = ";".join(str(p["id"]) for p in g)
            status = "matched"
        elif len(groups) > 1:
            status = "ambiguous"
            ids = ";".join(str(p["id"]) for g in groups for p in g)
        counts[status] += 1
        source_counts[match_source if status != "unmatched" else "none"] += 1
        out_rows.append({
            "molit_no": r["순번(No)"], "name": r["시설물명"], "sido": r["sido"], "sgg": r["sgg"], "grade": r.get("종별", ""), "management": r.get("관리주체구분", ""),
            "structure": r.get("항목명", ""), "latitude": lat, "longitude": lon, "match_status": status, "osm_source": match_source if status != "unmatched" else "", "osm_way_ids": ids, "osm_candidates": len(candidates),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)
    by_sido = defaultdict(lambda: {"total": 0, "matched": 0})
    for r in out_rows:
        by_sido[r["sido"]]["total"] += 1
        by_sido[r["sido"]]["matched"] += r["match_status"] == "matched"
    summary = {
        "built_at": datetime.now().isoformat(timespec="seconds"), "molit_rows": len(molit), "osm_distinct_names": len(osm), "osm_tunnel_distinct_names": len(osm_tunnel_names),
        "counts": counts, "match_sources": source_counts, "by_sido": dict(sorted(by_sido.items())), "csv": str(OUT.relative_to(REPO_ROOT)).replace("\\", "/"),
        "method": "normalised MOLIT name match against OSM highway ways named *지하차도*; only when no in-province primary match exists, fall back to exact Korean name aliases on OSM tunnel=yes ways; same-name ways within 2 km averaged and candidates outside a coarse province bbox rejected",
        "osm_attribution": "© OpenStreetMap contributors",
        "osm_license": "Open Database License (ODbL) 1.0",
        "osm_copyright_url": "https://www.openstreetmap.org/copyright",
        "supplemental_osm_snapshot": {
            "path": str(OSM_TUNNELS.relative_to(REPO_ROOT)).replace("\\", "/") if osm_tunnel_snapshot else None,
            "timestamp_osm_base": osm_tunnel_snapshot.get("osm3s", {}).get("timestamp_osm_base") if osm_tunnel_snapshot else None,
            "sha256": hashlib.sha256(OSM_TUNNELS.read_bytes()).hexdigest() if osm_tunnel_snapshot else None,
        },
        "limits": ["OSM coverage is partial and names may differ from the register (e.g. 교차로 vs 지하차도).", "fallback matching checks a province bounding box, not the listed city/district; all coordinates remain monitoring candidates, not verified facility entrances or operational locations.", "ambiguous rows (same name in several places) need manual review.", "coordinates are way centres, not portals; nearest gauges do not prove a shared basin or upstream influence."],
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("molit_rows", "osm_distinct_names", "counts")}, ensure_ascii=False))
    print({k: f"{v['matched']}/{v['total']}" for k, v in summary["by_sido"].items()})


if __name__ == "__main__":
    main()
