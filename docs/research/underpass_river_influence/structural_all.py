"""Structural plausibility for ALL facilities with a water-level gauge within 5 km (no time series needed):
nearest gauge (rank 1) -> OSM river at gauge, same-named river within 1.5 km of the underpass,
gauge datum + planned flood level vs SRTM ground at the underpass.

Usage: python -X utf8 structural_all.py
Output: structural_all_229.csv
"""
import json
import math
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

REPO = r"C:\Users\11243\Documents\GitHub\Flood-Disaster-Digital-Twin"
OUT = os.path.dirname(os.path.abspath(__file__))
L = pd.read_csv(os.path.join(REPO, "data/processed/facilities/facility_gauge_links.csv"), dtype={"station_code": str})
inv = pd.read_csv(os.path.join(REPO, "data/processed/facilities/underpass_coordinates.csv"))
inv["facility_id"] = "underpass_coordinates:" + inv.molit_no.astype(str)
st = json.load(open(os.path.join(REPO, "data/manifests/hrfco-stations.json"), encoding="utf-8"))
meta = {s["code"]: s for s in st["kinds"]["waterlevel"]["stations"]}

R = L[(L.kind == "waterlevel") & (L["rank"] == 1) & (L.within_max_km)].copy()
R = R.drop(columns=["sido", "sgg"]).merge(inv[["facility_id", "sido", "sgg"]], on="facility_id", how="left")


def seg_dist_m(lat, lon, a, b):
    kx = 111320 * math.cos(math.radians(lat)); ky = 110540
    ax, ay = (a["lon"] - lon) * kx, (a["lat"] - lat) * ky
    bx, by = (b["lon"] - lon) * kx, (b["lat"] - lat) * ky
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / L2))
    return math.hypot(ax + t * dx, ay + t * dy)


BULK = os.path.join(OUT, "osm_waterways_bulk_all.json")
pts = [(meta[c]["lat"], meta[c]["lon"]) for c in R.station_code.unique()] + list(zip(R.facility_lat, R.facility_lon))
pts = sorted(set((round(a, 5), round(b, 5)) for a, b in pts))
if not os.path.exists(BULK):
    ways = {}
    for i in range(0, len(pts), 120):
        body = "".join(f'way(around:1500,{a},{b})[waterway~"^(river|stream|canal)$"][name];' for a, b in pts[i:i + 120])
        q = f"[out:json][timeout:300];({body});out tags geom;"
        for attempt in range(6):
            try:
                req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(),
                                             headers={"User-Agent": "floodops-research/0.1"})
                d = json.load(urllib.request.urlopen(req, timeout=400)); break
            except Exception as ex:
                print("retry", ex); time.sleep(30)
        for e in d["elements"]:
            ways[e["id"]] = e
        time.sleep(5)
    json.dump({"elements": list(ways.values())}, open(BULK, "w", encoding="utf-8"), ensure_ascii=False)
ways = json.load(open(BULK, encoding="utf-8"))["elements"]
print("ways", len(ways))


def near(lat, lon, radius):
    best = {}
    for e in ways:
        g = e.get("geometry") or []
        dm = min((seg_dist_m(lat, lon, g[i], g[i + 1]) for i in range(len(g) - 1)), default=None)
        if dm is None or dm > radius:
            continue
        n = e["tags"]["name"]
        if n not in best or dm < best[n]:
            best[n] = round(dm)
    return sorted(best.items(), key=lambda x: x[1])


ELEV = os.path.join(OUT, "srtm_cache.json")
elev = json.load(open(ELEV)) if os.path.exists(ELEV) else {}
need = [p for p in set(zip(R.facility_lat.round(6), R.facility_lon.round(6))) if f"{p[0]},{p[1]}" not in elev]
for i in range(0, len(need), 90):
    chunk = need[i:i + 90]
    d = json.load(urllib.request.urlopen("https://api.opentopodata.org/v1/srtm30m?locations=" + "|".join(f"{a},{b}" for a, b in chunk), timeout=120))
    for p, r in zip(chunk, d["results"]):
        elev[f"{p[0]},{p[1]}"] = r["elevation"]
    time.sleep(1.5)
json.dump(elev, open(ELEV, "w"))

rows = []
for _, r in R.iterrows():
    m = meta[r.station_code]
    gr = near(m["lat"], m["lon"], 600)
    fr = near(r.facility_lat, r.facility_lon, 1500)
    g0 = gr[0][0] if gr else None
    same = dict(fr).get(g0) if g0 else None
    ground = elev[f"{round(r.facility_lat, 6)},{round(r.facility_lon, 6)}"]
    pfh_el = (m["gdt"] + m["pfh"]) if (m.get("gdt") is not None and m.get("pfh") is not None) else None
    rows.append({"facility_id": r.facility_id, "facility_name": r.facility_name, "sido": r.sido, "sgg": r.sgg,
                 "station_code": r.station_code, "station_name": r.station_name, "distance_km": r.distance_km,
                 "flood_forecast_station": m.get("flood_forecast_station"), "has_pfh": m.get("pfh") is not None, "has_gdt": m.get("gdt") is not None,
                 "gauge_river": g0, "fac_nearest_river": fr[0][0] if fr else None, "fac_nearest_river_m": fr[0][1] if fr else None,
                 "same_river_dist_m": same, "ground_srtm_m": ground,
                 "hint_pfh_minus_ground_m": round(pfh_el - ground, 1) if pfh_el is not None and ground is not None else None})
A = pd.DataFrame(rows)
A.to_csv(os.path.join(OUT, "structural_all_229.csv"), index=False, encoding="utf-8-sig")
n = len(A)
sr = A.same_river_dist_m.notna()
el = A.hint_pfh_minus_ground_m >= -3
print("facilities", n, "unique gauges", A.station_code.nunique())
print("has pfh", A.has_pfh.sum(), "has gdt+pfh", (A.has_pfh & A.has_gdt).sum())
print("same river <=1.5km", sr.sum(), "<=500m", (A.same_river_dist_m <= 500).sum())
print("elev hint >= -3", el.sum(), ">= 0", (A.hint_pfh_minus_ground_m >= 0).sum())
print("same river<=1.5km & elev>=-3", (sr & el).sum(), "gauges", A[sr & el].station_code.nunique())
print("same river<=500m & elev>=-3", ((A.same_river_dist_m <= 500) & el).sum())
print("no river within 1.5km at all", A.fac_nearest_river.isna().sum())
print("elev < -10", (A.hint_pfh_minus_ground_m < -10).sum())
print(A[sr & el].groupby("sido").size())
