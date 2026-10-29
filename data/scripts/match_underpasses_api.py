"""Give the MOLIT underpass register coordinates from the national road-tunnel API.

Inputs:
- data/processed/facilities/underpass_coordinates.csv — 국토교통부 「시설물안전법 대상 지하차도 현황」 938 rows
  with the OSM match from match_underpasses_osm.py.
- data/processed/facilities/road_tunnels.csv — 국토교통부_도로 교량 및 터널 현황정보 (getTunlList), from
  ``python data/scripts/link_facilities_to_gauges.py tunnels --hyear 2024``. Carries start/end coordinates
  and the managing office for every road tunnel and underpass.

Matching uses the same name normalisation as the OSM match, within the same 시도 and the first word of
시군구. If the name is unique within the 시도 in both the catalog and the API it is accepted without the
시군구 check (세종 rows have no 시군구; border facilities are listed under a neighbouring 구) and
``api_sgg_differs`` marks it. Several API rows
for one facility (one per direction) are averaged. Coordinates of 0 or outside Korea are rejected.
The existing OSM file is not modified; this writes a separate table so the two sources can be compared.
``best_*`` prefers the API point because it is tied to the listed 시군구; OSM is used only when the API has none.
``osm_far_from_api`` marks OSM points more than 1 km from the API point (likely a same-name match elsewhere).
``api_shared_with`` lists other catalog rows that matched the same API record and so got the same point.
``osm_is_other_facility`` names the 시군구 of a same-name API facility within 1 km of an OSM-only point. The point
is dropped (``osm_dropped``, empty ``best_*``) only if it is also more than 10 km from every API underpass of the
listed 시군구; otherwise it is kept as a likely border structure. Any OSM-only point more than 25 km from every
HRFCO station of the listed 시군구 (``osm_city_station_km``) is dropped too. 시도 names are compared after the
2024 renaming.

Output: data/processed/facilities/underpass_api_coordinates.csv and data/manifests/underpass-api-coordinates.json.

    python data/scripts/match_underpasses_api.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from match_underpasses_osm import norm  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "data" / "processed" / "facilities" / "underpass_coordinates.csv"
TUNNELS = REPO_ROOT / "data" / "processed" / "facilities" / "road_tunnels.csv"
OUT = REPO_ROOT / "data" / "processed" / "facilities" / "underpass_api_coordinates.csv"
SUMMARY = REPO_ROOT / "data" / "manifests" / "underpass-api-coordinates.json"
ENDPOINT = "https://apis.data.go.kr/1613000/btiData/getTunlList"
# Spot checks of pairs beyond this gap found the OSM way in another city with the same name
# (e.g. 거제 옥산 -> 경산, 의정부 용현 -> 인천 용현동), while the API point sat in the listed 시군구.
OSM_FAR_M = 1000
# An OSM-only point that sits on a same-name facility of another 시군구 is dropped only when it is also this far
# from every API underpass of the listed 시군구 (평택 신대 → 수원, 서초 내곡 → 고양). Closer ones are border
# structures listed under the neighbour (위례 하남/송파, 매헌 과천/서초) and are kept with the flag.
CITY_FAR_KM = 10.0
# Independent check for OSM-only points with no API record to compare against: distance to the nearest HRFCO
# station whose address is in the listed 시군구. API points sit within 14.9 km of one at the 99th percentile
# (570 rows, 2026-10-26); 영동 계룡(복) → 대전 유성 35 km and 안산 중앙 → 서울 중구 26 km are beyond this.
STATION_FAR_KM = 25.0
STATIONS = REPO_ROOT / "data" / "manifests" / "hrfco-stations.json"
# The 2023 catalog predates the renaming; the 2024 API uses the new names.
SIDO_ALIASES = {"전라북도": "전북특별자치도", "강원도": "강원특별자치도"}


def sido_of(name: str | None) -> str:
    name = (name or "").strip()
    return SIDO_ALIASES.get(name, name)


def point(lat: str | None, lon: str | None) -> tuple[float, float] | None:
    try:
        la, lo = float(lat or ""), float(lon or "")
    except ValueError:
        return None
    return (la, lo) if 33 < la < 39 and 124 < lo < 132 else None


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(h))


def sgg_head(sgg: str) -> str:
    return (sgg or "").split()[0] if sgg else ""


def station_anchors() -> dict[tuple[str, str], list[tuple[float, float]]]:
    catalog = json.loads(STATIONS.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for kind in ("waterlevel", "rainfall"):
        for s in catalog["kinds"][kind]["stations"]:
            parts = (s.get("address") or "").split()
            if len(parts) >= 2 and (p := point(str(s.get("lat")), str(s.get("lon")))):
                out.setdefault((sido_of(parts[0]), parts[1]), []).append(p)
    return out


def main() -> None:
    catalog = list(csv.DictReader(CATALOG.open(encoding="utf-8-sig", newline="")))
    tunnels = list(csv.DictReader(TUNNELS.open(encoding="utf-8-sig", newline="")))
    underpasses = [t for t in tunnels if t.get("tunlType") == "지하차도" or "지하차도" in (t.get("facilName") or "")]

    by_sgg: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    by_sido: dict[tuple[str, str], list[dict[str, str]]] = {}
    by_name: dict[str, list[dict[str, str]]] = {}
    city_points: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for t in underpasses:
        key, t_sido, t_sgg = norm(t.get("facilName") or ""), sido_of(t.get("sidoNm")), sgg_head(t.get("sggNm") or "")
        by_sgg.setdefault((key, t_sido, t_sgg), []).append(t)
        by_sido.setdefault((key, t_sido), []).append(t)
        by_name.setdefault(key, []).append(t)
        if p := point(t.get("sLatitude"), t.get("sLongitude")):
            city_points.setdefault((t_sido, t_sgg), []).append(p)

    rows, used = [], set()
    claims: dict[int, list[str]] = {}
    hit_ids: dict[str, list[int]] = {}
    catalog_names = Counter((norm(c["name"]), sido_of(c["sido"])) for c in catalog)
    anchors = station_anchors()
    for c in catalog:
        key, sido = norm(c["name"]), sido_of(c["sido"])
        hits, method = by_sgg.get((key, sido, sgg_head(c["sgg"]))), "name_sido_sgg"
        if not hits:
            # Fallback for 세종 (no 시군구) and facilities on a district border. Only when the name is unique on
            # both sides: three catalog rows named 신대지하차도 (용인·수원·평택) must not all take the 수원 point.
            cand = by_sido.get((key, sido)) or []
            names = {t.get("sggNm") for t in cand}
            unique = cand and len(names) == 1 and catalog_names[(key, sido)] == 1
            hits, method = (cand, "name_sido_unique") if unique else (None, "")
        starts = [p for t in hits or [] if (p := point(t.get("sLatitude"), t.get("sLongitude")))]
        ends = [p for t in hits or [] if (p := point(t.get("eLatitude"), t.get("eLongitude")))]
        for t in hits or []:
            used.add(id(t))
            claims.setdefault(id(t), []).append(c["molit_no"])
        hit_ids[c["molit_no"]] = [id(t) for t in hits or []]
        pts = starts + ends
        mid = (statistics.fmean(p[0] for p in pts), statistics.fmean(p[1] for p in pts)) if pts else None
        osm = point(c.get("latitude"), c.get("longitude")) if c.get("match_status") == "matched" else None
        status = "API_VALID" if mid else ("API_INVALID_COORD" if hits else "NO_API_MATCH")
        first = (hits or [{}])[0]
        gap = round(metres(osm, mid)) if osm and mid else None
        # An OSM-only point sitting on the API record of a same-name facility in another 시군구 is that facility.
        osm_other, osm_dropped, osm_station_km = None, False, None
        if osm and not mid:
            for t in by_name.get(key, []):
                p = point(t.get("sLatitude"), t.get("sLongitude"))
                same_place = sido_of(t.get("sidoNm")) == sido and sgg_head(t.get("sggNm") or "") == sgg_head(c["sgg"])
                if p and not same_place and metres(osm, p) <= OSM_FAR_M:
                    osm_other = f"{t.get('sidoNm', '')} {t.get('sggNm', '')}".strip()
                    break
            home = city_points.get((sido, sgg_head(c["sgg"]))) if c["sgg"] else None
            osm_dropped = bool(osm_other and home and min(metres(osm, p) for p in home) > CITY_FAR_KM * 1000)
            stations_here = anchors.get((sido, sgg_head(c["sgg"]))) if c["sgg"] else None
            if stations_here:
                osm_station_km = min(metres(osm, p) for p in stations_here) / 1000
                osm_dropped = osm_dropped or osm_station_km > STATION_FAR_KM
        if mid:
            best, best_source = mid, "api"
        elif osm and not osm_dropped:
            best, best_source = osm, "osm"
        else:
            best, best_source = None, ""
        rows.append({
            "molit_no": c["molit_no"], "name": c["name"], "sido": c["sido"], "sgg": c["sgg"],
            "api_status": status, "match_method": method if hits else "",
            "api_rows": len(hits or []), "api_name": first.get("facilName", ""), "api_sgg": first.get("sggNm", ""),
            "api_sgg_differs": "true" if hits and c["sgg"] and sgg_head(first.get("sggNm") or "") != sgg_head(c["sgg"]) else "false",
            "managing_office": first.get("orgmNm", ""), "length_m": first.get("length", ""), "open_year": first.get("openYear", ""),
            "latitude": f"{mid[0]:.6f}" if mid else "", "longitude": f"{mid[1]:.6f}" if mid else "",
            "osm_latitude": f"{osm[0]:.6f}" if osm else "", "osm_longitude": f"{osm[1]:.6f}" if osm else "",
            "osm_api_distance_m": gap if gap is not None else "",
            "osm_far_from_api": "true" if gap is not None and gap > OSM_FAR_M else "false",
            "osm_is_other_facility": osm_other or "",
            "osm_city_station_km": round(osm_station_km, 1) if osm_station_km is not None else "",
            "osm_dropped": "true" if osm_dropped else "false",
            "best_latitude": f"{best[0]:.6f}" if best else "", "best_longitude": f"{best[1]:.6f}" if best else "",
            "best_source": best_source,
        })

    # Two catalog rows matched to the same API record get the same point; one of them may be another facility.
    for row in rows:
        others = sorted({no for t in hit_ids[row["molit_no"]] for no in claims[t]} - {row["molit_no"]}, key=int)
        row["api_shared_with"] = ";".join(others)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    status = Counter(r["api_status"] for r in rows)
    distances = sorted(r["osm_api_distance_m"] for r in rows if r["osm_api_distance_m"] != "")
    has_osm = sum(1 for r in rows if r["osm_latitude"])
    has_api = status["API_VALID"]
    either = sum(1 for r in rows if r["osm_latitude"] or r["latitude"])
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_endpoint": ENDPOINT,
        "inputs": {
            "catalog": {"path": CATALOG.relative_to(REPO_ROOT).as_posix(), "rows": len(catalog)},
            "road_tunnels": {"path": TUNNELS.relative_to(REPO_ROOT).as_posix(), "rows": len(tunnels), "underpass_rows": len(underpasses),
                             "underpass_rows_with_valid_start": sum(1 for t in underpasses if point(t.get("sLatitude"), t.get("sLongitude")))},
        },
        "catalog_rows": len(rows),
        "api_status": dict(status),
        "with_osm_coordinate": has_osm,
        "with_api_coordinate": has_api,
        "with_either_coordinate": either,
        "api_only_new_coordinates": sum(1 for r in rows if r["latitude"] and not r["osm_latitude"]),
        "api_underpasses_not_in_catalog": sum(1 for t in underpasses if id(t) not in used),
        "osm_vs_api_distance_m": {
            "pairs": len(distances),
            "median": distances[len(distances) // 2] if distances else None,
            "p90": distances[int(len(distances) * 0.9)] if distances else None,
            "over_1000m": sum(1 for d in distances if d > OSM_FAR_M),
        },
        "best_coordinate_source": dict(Counter(r["best_source"] or "none" for r in rows)),
        "api_point_shared_by_several_catalog_rows": sum(1 for r in rows if r["api_shared_with"]),
        "osm_point_is_other_facility": sum(1 for r in rows if r["osm_is_other_facility"]),
        "osm_point_dropped": sum(1 for r in rows if r["osm_dropped"] == "true"),
        "output": {"path": OUT.relative_to(REPO_ROOT).as_posix(), "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()},
        "note": "API coordinates are the mean of start/end points of the tunnel record, not the underpass low point. "
                "A catalog row matched by name is a candidate match; rows with large OSM/API distance need review.",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
