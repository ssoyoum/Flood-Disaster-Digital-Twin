"""Build data/facilities/candidates.json from the public underpass catalog and the gauge links.

Deterministic and offline: it only reads CSVs already in data/processed/facilities/ plus the hand-kept
registry.json, and writes candidates.json next to it. Nothing here becomes an operational facility;
every candidate keeps ``gauge``, ``control_rule`` and ``reference_event`` as null so no threshold can be
copied from Osong by accident. The backend loader rejects a CANDIDATE that carries any of them.

Selection:
  (a) every 충청북도 row of underpass_coordinates.csv that has coordinates and at least one
      water-level gauge in facility_gauge_links.csv flagged flood_forecast_station=Y within 5 km;
  (b) the three Cheongju follow-up candidates named in docs/UNDERPASS_EXPANSION.md
      (오송바이오폴리스·용암·학평, source rows 15124755:519/521/523) even without coordinates.
A named candidate that also appears in underpass_coordinates.csv (same 국토부 순번 and name) gets that
row's coordinates and gauge links; the two sources are the same national list. Coordinates come from
underpass_api_coordinates.csv (road-tunnel API first, OSM where the API has none), the same points
facility_gauge_links.csv was built from.

    python data/scripts/build_facility_candidates.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "data" / "processed" / "facilities"
COORDS_CSV = PROCESSED / "underpass_coordinates.csv"
# Same coordinates as facility_gauge_links.csv: road-tunnel API point first, OSM only where the API has none.
API_COORDS_CSV = PROCESSED / "underpass_api_coordinates.csv"
COORD_SOURCE_KO = {"api": "국토부 도로터널 API", "osm": "OSM 이름 매칭"}
LINKS_CSV = PROCESSED / "facility_gauge_links.csv"
CHUNGBUK_CSV = PROCESSED / "chungbuk_underpass_candidates.csv"
REGISTRY_JSON = REPO_ROOT / "data" / "facilities" / "registry.json"
OUTPUT_JSON = REPO_ROOT / "data" / "facilities" / "candidates.json"

SIDO = "충청북도"
SEOUL = "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc"
SEOUL_DEMO_ORDINAL = "43"  # Oebalsan comparison candidate; remains unverified
MAX_GAUGE_KM = 5.0
MAX_NEARBY = 3
NATIONAL_DATASET_ID = "15124755"
# docs/UNDERPASS_EXPANSION.md «1차 확인 후보»: 국토부 시설물 목록 순번.
NAMED_CANDIDATE_ORDINALS = ("519", "521", "523")
# Facilities whose coordinates sit this close to an operational facility are flagged for review:
# the OSM name match may have landed on the neighbouring underpass.
OVERLAP_KM = 0.1
# Rows whose OSM coordinates contradict the catalog location are left out until the coordinates are
# re-checked; they are listed under "excluded" with the reason so the omission stays visible.
EXCLUDED_ORDINALS = {
    "916": "목록상 위치는 영동군이지만 OSM 이름 매칭 좌표가 대전 유성구(만년교 0.39 km)에 있음 — 다른 시설을 가리킨 매칭으로 보고 좌표 확인 전까지 제외",
}
# ASCII slugs for the names that can appear here. Unknown names fall back to the 국토부 순번 only.
SLUGS = {
    "오송바이오폴리스지하차도": "osong-biopolis",
    "용암지하차도": "yongam",
    "학평지하차도": "hakpyeong",
    "계룡지하차도(복)": "gyeryong",
    "심곡지하차도(복)": "simgok",
    "궁평지하차도": "gungpyeong",
    "궁평2지하차도": "gungpyeong2",
    "고명지하차도": "gomyeong",
    "터미널 지하차도": "terminal",
    "단양지하차도": "danyang",
    "오창지하차도": "ochang",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_coords() -> list[dict[str, str]]:
    rows = read_csv(COORDS_CSV)
    best = {r["molit_no"]: r for r in read_csv(API_COORDS_CSV)}
    for row in rows:
        b = best.get(row["molit_no"], {})
        row["latitude"], row["longitude"] = b.get("best_latitude", ""), b.get("best_longitude", "")
        row["coordinate_source"] = COORD_SOURCE_KO.get(b.get("best_source", ""), "")
    return rows


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _num(value: str | None) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def slug_for(name: str, ordinal: str, sido: str) -> str:
    if sido == SEOUL and ordinal == SEOUL_DEMO_ORDINAL:
        return "seoul-43-oebalsan"
    base = SLUGS.get(name.strip())
    return f"cb-{ordinal}-{base}" if base else f"cb-{ordinal}"


def nearby_gauges(links: list[dict[str, str]], facility_key: str) -> list[dict[str, Any]]:
    rows = [r for r in links if r["facility_id"] == facility_key and r["kind"] == "waterlevel"]
    rows.sort(key=lambda r: float(r["distance_km"]))
    return [
        {
            "station_id": r["station_code"],
            "name": r["station_name"],
            "agency": r["agency"] or None,
            "distance_km": float(r["distance_km"]),
            "flood_forecast_station": r["flood_forecast_station"] == "Y",
            "planned_flood_m": _num(r["planned_flood_m"]),
            "warning_m": _num(r["warning_m"]),
            "advisory_m": _num(r["advisory_m"]),
        }
        for r in rows[:MAX_NEARBY]
    ]


def nearby_rain_gauges(links: list[dict[str, str]], facility_key: str) -> list[dict[str, Any]]:
    rows = [r for r in links if r["facility_id"] == facility_key and r["kind"] == "rainfall"]
    rows.sort(key=lambda r: float(r["distance_km"]))
    return [
        {"station_id": r["station_code"], "name": r["station_name"], "agency": r["agency"] or None,
         "distance_km": float(r["distance_km"])}
        for r in rows[:MAX_NEARBY]
    ]


def has_forecast_gauge_within(gauges: list[dict[str, Any]], km: float) -> dict[str, Any] | None:
    for g in gauges:  # nearest first
        if g["flood_forecast_station"] and g["distance_km"] <= km:
            return g
    return None


def build_gates(gauges: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    gates = {
        "inflow_path": {"status": "UNKNOWN", "note": "하천 월류형인지 내수 배수형인지 미확인"},
        "representative_gauge": {"status": "UNKNOWN", "note": f"{MAX_GAUGE_KM:g} km 안 홍수예보 관측소 없음" if gauges else "좌표가 없어 관측소를 연결하지 못함"},
        "site_instrumentation": {"status": "UNKNOWN", "note": "현장 계측(침수심·집수정·펌프) 설치 여부 미조사"},
        "validation_event": {"status": "UNKNOWN", "note": "시각 있는 침수·통제 기록 미확보"},
    }
    hit = has_forecast_gauge_within(gauges, MAX_GAUGE_KM)
    if hit:
        gates["representative_gauge"] = {
            "status": "PENDING",
            "note": f"{hit['name']} {hit['station_id']} · {hit['distance_km']:.2f} km · 홍수예보 지점 — 같은 유역인지, 유입을 설명하는지 확인 전",
        }
    return gates


def location_review(sgg: str, location: list[float] | None, gauges: list[dict[str, Any]], operational: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if not location:
        return notes
    for f in operational:
        loc = f.get("location")
        if loc and haversine_km(location[0], location[1], loc[0], loc[1]) <= OVERLAP_KM:
            notes.append(f"좌표가 운영 시설 {f['name']}({f['id']})과 {OVERLAP_KM:g} km 안에 겹침 — 이름 매칭이 이웃 시설을 가리켰을 수 있어 좌표 확인 필요")
    key = sgg.strip()[:2]
    if gauges and key and not any(key in g["name"] for g in gauges):
        places = sorted({g["name"].split("(")[0] for g in gauges})
        notes.append(f"가까운 수위 관측소가 모두 다른 시군({', '.join(places)})에 있음 — 목록상 위치 {sgg}와 좌표가 어긋날 수 있어 확인 필요")
    return notes


def main() -> None:
    coords = read_coords()
    links = read_csv(LINKS_CSV)
    chungbuk = read_csv(CHUNGBUK_CSV)
    registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    operational = [f for f in registry["facilities"] if f.get("status") == "OPERATIONAL"]
    by_molit = {r["molit_no"]: r for r in coords}

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(ordinal: str, name: str, sido: str, sgg: str, location: list[float] | None, source: dict[str, Any], management: str | None, agency: str | None, structure: str | None, selected_by: str, driver_hypothesis: str | None = None) -> None:
        facility_key = f"underpass_coordinates:{ordinal}"
        gauges = nearby_gauges(links, facility_key) if location else []
        rain_gauges = nearby_rain_gauges(links, facility_key) if location else []
        gates = build_gates(gauges)
        if driver_hypothesis == "pluvial" and rain_gauges and rain_gauges[0]["distance_km"] <= MAX_GAUGE_KM:
            nearest = rain_gauges[0]
            gates["representative_gauge"] = {
                "status": "PENDING",
                "note": f"{nearest['name']} {nearest['station_id']} · {nearest['distance_km']:.2f} km · representative rainfall gauge and catchment link need review",
            }
        entry = {
            "id": slug_for(name, ordinal, sido),
            "name": name,
            "kind": "underpass",
            "driver": "unverified",
            "status": "CANDIDATE",
            "region": f"{sido} {sgg}".strip(),
            "location": location,
            "road": None,
            "managing_agency": agency or None,
            "management_category": management or None,
            "structure_raw": structure or None,
            "source": source,
            "selected_by": selected_by,
            "nearby_gauges": gauges,
            "nearby_rain_gauges": rain_gauges,
            "gauge": None,
            "control_rule": None,
            "reference_event": None,
            "gates": gates,
            "review_notes": location_review(sgg, location, gauges, operational),
        }
        if driver_hypothesis:
            entry["driver_hypothesis"] = driver_hypothesis
            entry["driver_hypothesis_note"] = "Comparison hypothesis only; inflow path, site instrumentation and a validation event are unconfirmed."
        candidates.append(entry)
        seen.add(ordinal)

    # (b) named follow-up candidates first, so they keep their documented identity even when (a) also matches.
    for row in chungbuk:
        if row["dataset_id"] != NATIONAL_DATASET_ID or row["source_ordinal"] not in NAMED_CANDIDATE_ORDINALS:
            continue
        ordinal = row["source_ordinal"]
        coord_row = by_molit.get(ordinal)
        location = None
        if coord_row and coord_row["name"].strip() == row["name"].strip() and coord_row["latitude"] and coord_row["longitude"]:
            location = [float(coord_row["longitude"]), float(coord_row["latitude"])]
        sido, _, sgg = row["location_raw"].partition(" ")
        source = {
            "dataset_id": row["dataset_id"],
            "source_record_id": row["source_record_id"],
            "molit_no": ordinal,
            "source_url": row["source_url"],
            "source_date": row["source_date"],
            "source_updated_at": row["source_updated_at"],
            "coordinates": f"underpass_api_coordinates.csv ({coord_row['coordinate_source']})" if location else None,
        }
        add(ordinal, row["name"], sido, sgg, location, source, row["management_category"], row["agency_raw"], row["structure_raw"], "docs/UNDERPASS_EXPANSION.md 1차 확인 후보")

    # One Seoul counterpart shows a pluvial driver hypothesis using the same CANDIDATE schema.
    for row in coords:
        if row["sido"] != SEOUL or row["molit_no"] != SEOUL_DEMO_ORDINAL or not row["latitude"] or not row["longitude"]:
            continue
        location = [float(row["longitude"]), float(row["latitude"])]
        source = {
            "dataset_id": NATIONAL_DATASET_ID,
            "source_record_id": f"{NATIONAL_DATASET_ID}:{row['molit_no']}",
            "molit_no": row["molit_no"],
            "source_url": f"https://data.go.kr/data/{NATIONAL_DATASET_ID}/fileData.do",
            "coordinates": f"underpass_api_coordinates.csv ({row['coordinate_source']})",
            "osm_way_ids": row["osm_way_ids"] or None,
        }
        add(row["molit_no"], row["name"], row["sido"], row["sgg"], location, source, row["management"], None, row["structure"],
            "TODO.md pluvial-rule comparison candidate", "pluvial")
        break

    # (a) Chungbuk rows with coordinates and a flood-forecast gauge within MAX_GAUGE_KM.
    excluded: list[dict[str, str]] = []
    for row in coords:
        if row["sido"] != SIDO or not row["latitude"] or not row["longitude"] or row["molit_no"] in seen:
            continue
        location = [float(row["longitude"]), float(row["latitude"])]
        gauges = nearby_gauges(links, f"underpass_coordinates:{row['molit_no']}")
        if not has_forecast_gauge_within(gauges, MAX_GAUGE_KM):
            continue
        if row["molit_no"] in EXCLUDED_ORDINALS:
            excluded.append({"molit_no": row["molit_no"], "name": row["name"], "region": f"{row['sido']} {row['sgg']}".strip(), "reason": EXCLUDED_ORDINALS[row["molit_no"]]})
            continue
        source = {
            "dataset_id": NATIONAL_DATASET_ID,
            "source_record_id": f"{NATIONAL_DATASET_ID}:{row['molit_no']}",
            "molit_no": row["molit_no"],
            "source_url": f"https://data.go.kr/data/{NATIONAL_DATASET_ID}/fileData.do",
            "source_date": None,
            "source_updated_at": None,
            "coordinates": f"underpass_api_coordinates.csv ({row['coordinate_source']})",
            "osm_way_ids": row["osm_way_ids"] or None,
        }
        add(row["molit_no"], row["name"], row["sido"], row["sgg"], location, source, row["management"], None, row["structure"], f"{SIDO} · 좌표 있음 · {MAX_GAUGE_KM:g} km 안 홍수예보 수위관측소")

    candidates.sort(key=lambda c: int(c["source"]["molit_no"]))

    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    # Input hashes instead of a timestamp: regenerating from unchanged inputs yields a byte-identical file.
    payload = {
        "schema_version": 1,
        "generator": "data/scripts/build_facility_candidates.py",
        "inputs": {
            "underpass_coordinates.csv": {"rows": len(coords), "chungbuk_rows": sum(1 for r in coords if r["sido"] == SIDO), "chungbuk_rows_with_coordinates": sum(1 for r in coords if r["sido"] == SIDO and r["latitude"] and r["longitude"]), "sha256": sha256(COORDS_CSV)},
            "underpass_api_coordinates.csv": {"sha256": sha256(API_COORDS_CSV)},
            "facility_gauge_links.csv": {"rows": len(links), "sha256": sha256(LINKS_CSV)},
            "chungbuk_underpass_candidates.csv": {"rows": len(chungbuk), "sha256": sha256(CHUNGBUK_CSV)},
            "registry.json": {"operational": len(operational), "sha256": sha256(REGISTRY_JSON)},
        },
        "excluded": excluded,
        "selection": {
            "sido": SIDO,
            "max_gauge_km": MAX_GAUGE_KM,
            "seoul_comparison_candidate": {"dataset_id": NATIONAL_DATASET_ID, "molit_no": SEOUL_DEMO_ORDINAL, "driver_hypothesis": "pluvial", "operational": False},
            "rule": f"(a) {SIDO} 시설 중 좌표가 있고 {MAX_GAUGE_KM:g} km 안에 홍수예보 수위관측소가 있는 행 + (b) docs/UNDERPASS_EXPANSION.md의 청주 후보 3곳(순번 {', '.join(NAMED_CANDIDATE_ORDINALS)})",
            "not_a_ranking": "후보 순서는 국토부 순번이며 위험 순위가 아니다. 가까운 관측소는 후보일 뿐 대표성이 확인된 것이 아니다.",
        },
        "counts": {"candidates": len(candidates), "with_coordinates": sum(1 for c in candidates if c["location"]), "with_pending_gauge": sum(1 for c in candidates if c["gates"]["representative_gauge"]["status"] == "PENDING"), "with_review_notes": sum(1 for c in candidates if c["review_notes"]), "excluded": len(excluded)},
        "candidates": candidates,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(OUTPUT_JSON.relative_to(REPO_ROOT)).replace("\\", "/"), **payload["counts"]}, ensure_ascii=False))
    for c in candidates:
        gauge = c["gates"]["representative_gauge"]
        print(f"  {c['id']}: {c['name']} · {c['region']} · loc={'Y' if c['location'] else '-'} · gauge={gauge['status']} · notes={len(c['review_notes'])}")


if __name__ == "__main__":
    main()
