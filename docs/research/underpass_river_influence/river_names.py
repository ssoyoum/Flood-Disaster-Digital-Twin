"""OSM (Overpass, ODbL) named waterways near each underpass and each gauge -> same-river check.

For each point: named waterway=river|stream|canal ways within 1500 m, with min point-to-line distance.
Usage: python -X utf8 river_names.py   (after elevation_hint.py)
Output: osm_waterways.json (cache), facility_shortlist_input.csv
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
CACHE = os.path.join(OUT, "osm_waterways.json")
F = pd.read_csv(os.path.join(OUT, "facility_gauge_exceedance_elev.csv"), dtype={"station_code": str, "nearest_code": str})
st = json.load(open(os.path.join(REPO, "data/manifests/hrfco-stations.json"), encoding="utf-8"))
meta = {s["code"]: s for s in st["kinds"]["waterlevel"]["stations"]}
cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def seg_dist_m(lat, lon, a, b):
    kx = 111320 * math.cos(math.radians(lat)); ky = 110540
    ax, ay = (a["lon"] - lon) * kx, (a["lat"] - lat) * ky
    bx, by = (b["lon"] - lon) * kx, (b["lat"] - lat) * ky
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / L2))
    return math.hypot(ax + t * dx, ay + t * dy)


def query(lat, lon, radius=1500):
    key = f"{lat:.5f},{lon:.5f},{radius}"
    if key in cache:
        return cache[key]
    q = f'[out:json][timeout:60];way(around:{radius},{lat},{lon})[waterway~"^(river|stream|canal)$"][name];out tags geom;'
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "floodops-research/0.1"})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            break
        except Exception as ex:  # noqa
            print("retry", key, ex); time.sleep(10)
    else:
        return None
    best = {}
    for e in d["elements"]:
        g = e.get("geometry") or []
        dm = min((seg_dist_m(lat, lon, g[i], g[i + 1]) for i in range(len(g) - 1)), default=None)
        if dm is None:
            continue
        n = e["tags"]["name"]
        if n not in best or dm < best[n]["m"]:
            best[n] = {"m": round(dm), "waterway": e["tags"].get("waterway")}
    res = sorted(({"name": k, **v} for k, v in best.items()), key=lambda x: x["m"])
    cache[key] = res
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(1.5)
    return res


def fmt(res, k=3):
    return "; ".join(f"{r['name']}({r['waterway'][0]}) {r['m']}m" for r in (res or [])[:k])


BULK = os.path.join(OUT, "osm_waterways_bulk.json")
pts = [(meta[c]["lat"], meta[c]["lon"]) for c in F.station_code.unique()] + list(zip(F.facility_lat, F.facility_lon))
pts = sorted(set((round(a, 5), round(b, 5)) for a, b in pts))
if not os.path.exists(BULK):
    body = "".join(f'way(around:1500,{a},{b})[waterway~"^(river|stream|canal)$"][name];' for a, b in pts)
    q = f"[out:json][timeout:300];({body});out tags geom;"
    for attempt in range(5):
        try:
            req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "floodops-research/0.1"})
            d = json.load(urllib.request.urlopen(req, timeout=400)); break
        except Exception as ex:
            print("retry", ex); time.sleep(20)
    json.dump(d, open(BULK, "w", encoding="utf-8"), ensure_ascii=False)
ways = json.load(open(BULK, encoding="utf-8"))["elements"]
print("ways", len(ways))


def near(lat, lon, radius):
    best = {}
    for e in ways:
        g = e.get("geometry") or []
        if not g or abs(g[0]["lat"] - lat) > 0.6 or abs(g[0]["lon"] - lon) > 0.6:
            pass
        dm = min((seg_dist_m(lat, lon, g[i], g[i + 1]) for i in range(len(g) - 1)), default=None)
        if dm is None or dm > radius:
            continue
        n = e["tags"]["name"]
        if n not in best or dm < best[n]["m"]:
            best[n] = {"m": round(dm), "waterway": e["tags"].get("waterway")}
    return sorted(({"name": k, **v} for k, v in best.items()), key=lambda x: x["m"])


gauge_river = {c: near(meta[c]["lat"], meta[c]["lon"], 600) for c in F.station_code.unique()}
fac_rivers = [near(r.facility_lat, r.facility_lon, 1500) for _, r in F.iterrows()]
F["gauge_osm_river"] = [(gauge_river[c][0]["name"] if gauge_river[c] else None) for c in F.station_code]
F["gauge_osm_rivers"] = [fmt(gauge_river[c]) for c in F.station_code]
F["fac_osm_rivers_1500m"] = [fmt(x, 4) for x in fac_rivers]
same = []
for gr, fr in zip(F.gauge_osm_river, fac_rivers):
    hit = next((x for x in (fr or []) if gr and x["name"] == gr), None)
    same.append(hit["m"] if hit else None)
F["same_river_dist_m"] = same
F.to_csv(os.path.join(OUT, "facility_shortlist_input.csv"), index=False, encoding="utf-8-sig")
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 70)
print(F[["facility_name", "sgg", "station_name", "gauge_osm_rivers", "fac_osm_rivers_1500m", "same_river_dist_m"]].to_string())
