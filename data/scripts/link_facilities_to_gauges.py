"""Attach coordinates to underpasses and link each one to its nearest HRFCO gauges.

Two steps, both from original public providers:

1. ``tunnels``: download the national road-tunnel register (국토교통부 도로 교량 및 터널 현황정보,
   https://apis.data.go.kr/1613000/btiData/getTunlList) which carries start/end coordinates for every
   road tunnel and underpass. Needs a data.go.kr service key in ``DATA_GO_KR_SERVICE_KEY`` with
   활용신청 for that service. Raw pages go to data/raw/facilities/tunnels/, the merged table to
   data/processed/facilities/road_tunnels.csv.
2. ``link``: for every facility with coordinates (the registered twin facilities, the tunnel register
   rows whose name contains 지하차도, or any CSV with name/latitude/longitude), find the nearest
   water-level and rainfall stations in data/manifests/hrfco-stations.json and write
   data/processed/facilities/facility_gauge_links.csv with distances, the gauge's official levels and
   whether it is a flood-forecast station.

    python data/scripts/link_facilities_to_gauges.py tunnels --hyear 2024
    python data/scripts/link_facilities_to_gauges.py link
    python data/scripts/link_facilities_to_gauges.py link --csv my_sites.csv --name-col name --lat-col lat --lon-col lon

Distances are great-circle kilometres. A nearby gauge is a candidate, not a validated driver: whether
its basin actually feeds the underpass still has to be checked per facility (TODO DIRECTION).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

CATALOG_FILE = REPO_ROOT / "data" / "manifests" / "hrfco-stations.json"
RAW_TUNNELS = REPO_ROOT / "data" / "raw" / "facilities" / "tunnels"
TUNNELS_CSV = REPO_ROOT / "data" / "processed" / "facilities" / "road_tunnels.csv"
LINKS_CSV = REPO_ROOT / "data" / "processed" / "facilities" / "facility_gauge_links.csv"
LINKS_MANIFEST = REPO_ROOT / "data" / "manifests" / "facility-gauge-links.json"
TUNNEL_ENDPOINT = "https://apis.data.go.kr/1613000/btiData/getTunlList"


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_catalog() -> dict[str, list[dict[str, Any]]]:
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return {kind: [s for s in catalog["kinds"][kind]["stations"] if s.get("lon") and s.get("lat")] for kind in ("waterlevel", "rainfall")}


# ---- tunnels ------------------------------------------------------------------------------------
def fetch_tunnels(hyear: int, page_size: int = 1000) -> dict[str, Any]:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env", override=False)
    except ImportError:
        pass
    key = os.environ.get("DATA_GO_KR_SERVICE_KEY", "").strip()
    if not key:
        sys.exit("DATA_GO_KR_SERVICE_KEY is not set. Issue a data.go.kr key and apply for 국토교통부_도로 교량 및 터널 현황정보 (1613000/btiData).")
    RAW_TUNNELS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    page = 1
    total = None
    while True:
        raw = RAW_TUNNELS / f"getTunlList_{hyear}_p{page}.json"
        if raw.exists():
            payload = json.loads(raw.read_text(encoding="utf-8"))
        else:
            response = httpx.get(TUNNEL_ENDPOINT, params={"serviceKey": key, "responseType": "json", "numOfRows": page_size, "pageNo": page, "hyear": hyear}, timeout=90)
            response.raise_for_status()
            payload = response.json()
            raw.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            time.sleep(0.3)
        body = payload.get("response", payload)
        header = body.get("header", {})
        if str(header.get("resultCode", "00")) not in ("00", "0"):
            sys.exit(f"API error on page {page}: {header}")
        items = (body.get("body") or {}).get("items") or {}
        batch = items.get("item") if isinstance(items, dict) else items
        if isinstance(batch, dict):
            batch = [batch]
        batch = batch or []
        total = int((body.get("body") or {}).get("totalCount") or total or 0)
        rows.extend(batch)
        if not batch or len(rows) >= total:
            break
        page += 1
    if not rows:
        sys.exit("No tunnel rows returned; check hyear and the service application status.")
    TUNNELS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r})
    with TUNNELS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    underpasses = [r for r in rows if "지하차도" in str(r.get("facilNm") or r.get("tunlNm") or r.get("facilName") or "")]
    return {"hyear": hyear, "rows": len(rows), "underpass_rows": len(underpasses), "fields": fields, "csv": str(TUNNELS_CSV.relative_to(REPO_ROOT)).replace("\\", "/")}


# ---- linking -------------------------------------------------------------------------------------
def _pick(row: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in row and str(row[name]).strip():
            return str(row[name]).strip()
    return None


def facilities_from_sources(csv_path: Path | None, name_col: str | None, lat_col: str | None, lon_col: str | None) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    try:
        from app.twin import FACILITIES  # registered twin facilities

        for f in FACILITIES.values():
            sites.append({"source": "twin_registry", "id": f["id"], "name": f["name"], "lon": f["location"][0], "lat": f["location"][1]})
    except Exception:
        pass
    if csv_path:
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            for i, row in enumerate(csv.DictReader(handle)):
                name = row.get(name_col or "name")
                lat, lon = row.get(lat_col or "latitude"), row.get(lon_col or "longitude")
                if name and lat and lon:
                    sites.append({"source": csv_path.name, "id": f"{csv_path.stem}:{i + 1}", "name": name, "lon": float(lon), "lat": float(lat)})
    elif TUNNELS_CSV.exists():
        with TUNNELS_CSV.open(encoding="utf-8-sig", newline="") as handle:
            for i, row in enumerate(csv.DictReader(handle)):
                name = _pick(row, ("facilNm", "tunlNm", "facilName", "터널명"))
                lat = _pick(row, ("sLatitude", "startLat", "시작점위도"))
                lon = _pick(row, ("sLongitude", "startLon", "시작점경도"))
                if name and "지하차도" in name and lat and lon:
                    sites.append({"source": "road_tunnels", "id": f"tunnel:{i + 1}", "name": name, "lon": float(lon), "lat": float(lat), "sido": _pick(row, ("sidoNm", "시도명")), "sgg": _pick(row, ("sggNm", "시군구명"))})
    return sites


def link(sites: list[dict[str, Any]], max_km: float, top: int) -> list[dict[str, Any]]:
    catalog = load_catalog()
    out = []
    for site in sites:
        for kind in ("waterlevel", "rainfall"):
            ranked = sorted(catalog[kind], key=lambda s: haversine_km(site["lon"], site["lat"], s["lon"], s["lat"]))[:top]
            for rank, station in enumerate(ranked, 1):
                d = haversine_km(site["lon"], site["lat"], station["lon"], station["lat"])
                out.append({
                    "facility_id": site["id"], "facility_name": site["name"], "facility_source": site["source"], "sido": site.get("sido", ""), "sgg": site.get("sgg", ""),
                    "facility_lon": site["lon"], "facility_lat": site["lat"], "kind": kind, "rank": rank, "station_code": station["code"], "station_name": station["name"],
                    "agency": station.get("agency", ""), "distance_km": round(d, 2), "within_max_km": d <= max_km,
                    "flood_forecast_station": station.get("flood_forecast_station", ""), "planned_flood_m": station.get("pfh", ""), "warning_m": station.get("almwl", ""), "advisory_m": station.get("wrnwl", ""),
                })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("tunnels", help="download the national road-tunnel register (needs DATA_GO_KR_SERVICE_KEY)")
    t.add_argument("--hyear", type=int, default=datetime.now().year - 1)
    l = sub.add_parser("link", help="link facilities with coordinates to the nearest HRFCO gauges")
    l.add_argument("--csv", type=Path, default=None, help="optional facility CSV with name/latitude/longitude")
    l.add_argument("--name-col", default=None)
    l.add_argument("--lat-col", default=None)
    l.add_argument("--lon-col", default=None)
    l.add_argument("--max-km", type=float, default=5.0)
    l.add_argument("--top", type=int, default=3)
    args = parser.parse_args()
    if args.command == "tunnels":
        print(json.dumps(fetch_tunnels(args.hyear), ensure_ascii=False, indent=1))
        return
    sites = facilities_from_sources(args.csv, args.name_col, args.lat_col, args.lon_col)
    rows = link(sites, args.max_km, args.top)
    LINKS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LINKS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["facility_id"])
        writer.writeheader()
        writer.writerows(rows)
    nearest_wl = [r for r in rows if r["kind"] == "waterlevel" and r["rank"] == 1]
    summary = {
        "linked_at": datetime.now().isoformat(timespec="seconds"), "facilities": len(sites), "sources": sorted({s["source"] for s in sites}),
        "max_km": args.max_km, "facilities_with_gauge_within_max_km": sum(1 for r in nearest_wl if r["within_max_km"]),
        "facilities_with_flood_forecast_gauge_within_max_km": sum(1 for r in nearest_wl if r["within_max_km"] and r["flood_forecast_station"] == "Y"),
        "csv": str(LINKS_CSV.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    LINKS_MANIFEST.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in nearest_wl[:10]:
        print(f"  {r['facility_name']}: {r['station_name']} ({r['station_code']}) {r['distance_km']} km, forecast={r['flood_forecast_station']}, pfh={r['planned_flood_m']}")


if __name__ == "__main__":
    main()
